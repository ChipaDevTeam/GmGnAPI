"""
Email and password authentication against GMGN.ai.

GMGN's web app signs in with SRP-6a over a multi-step endpoint: each POST to
``/account/login_v3`` either finishes the exchange or answers with a ``require``
list naming the next things to prove. A password login typically runs:

1. ``POST {"account": email, "srp_A": ...}`` -> ``require: ["verify_recaptcha"]``
   plus a reCAPTCHA site key.
2. ``POST {"session_id": ..., "captcha_token": ...}`` -> ``require:
   ["verify_password"]`` plus the SRP ``salt``, ``srp_B`` and ``user_id``.
3. ``POST {"session_id": ..., "client_M": ...}`` -> ``done: true`` with the
   access and refresh tokens. GMGN may insert an email code or authenticator
   step here for an unrecognised device.

The password is never transmitted. It is combined with the server's salt into an
SRP proof (see :mod:`gmgnapi.srp`), which is what step 3 sends.

Step 1 is gated by reCAPTCHA, which this library cannot and does not try to
solve. Pass a ``captcha_solver`` that returns a token from a real browser or a
solving service; without one, :meth:`GmGnAuth.login` raises
:class:`~gmgnapi.exceptions.CaptchaRequiredError` before contacting the server.
"""

import asyncio
import inspect
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

from curl_cffi.requests import AsyncSession

from . import srp
from .exceptions import (
    AuthenticationError,
    CaptchaRequiredError,
    VerificationRequiredError,
)
from .models import AuthTokens

logger = logging.getLogger(__name__)

__all__ = [
    "CaptchaChallenge",
    "VerificationChallenge",
    "GmGnAuth",
    "login",
]

# Request types GMGN can ask for mid-login. Mirrors the web client's RequireType.
REQUIRE_RECAPTCHA = "verify_recaptcha"
REQUIRE_CAPTCHA = "verify_captcha"
REQUIRE_PASSWORD = "verify_password"
REQUIRE_PASSWORD_SECRET = "password_secret"
REQUIRE_EMAIL_CODE = "email_code"
REQUIRE_VERIFY_EMAIL = "verify_email"
REQUIRE_OTP = "verify_otp"
REQUIRE_OTP_CODE = "otp_code"
REQUIRE_SMS_CODE = "sms_code"

# Requirements this library knows how to answer, used to choose between the
# alternatives in an "a|b" requirement.
_SUPPORTED_REQUIREMENTS = frozenset(
    {
        REQUIRE_RECAPTCHA,
        REQUIRE_CAPTCHA,
        REQUIRE_PASSWORD,
        REQUIRE_EMAIL_CODE,
        REQUIRE_VERIFY_EMAIL,
        REQUIRE_OTP,
        REQUIRE_OTP_CODE,
        REQUIRE_SMS_CODE,
    }
)

# Codes that mean "that verification attempt was wrong, ask again" rather than
# "this login is over". The web client re-prompts on these instead of failing.
RETRYABLE_CODES = frozenset({-102000, -109903, -101021, -20202, -109917})


@dataclass
class CaptchaChallenge:
    """A captcha GMGN wants solved before it will continue the login."""

    site_key: str
    #: ``"score"`` for reCAPTCHA v3 (invisible), ``"widget"`` for v2.
    key_type: str = "score"
    #: The reCAPTCHA action name to execute with; ``"login"`` for sign-in.
    action: str = "login"
    lang: str = "en"
    #: Raw ``captcha_data`` for GeeTest challenges; empty for reCAPTCHA.
    captcha_data: str = ""
    #: ``"recaptcha"`` or ``"geetest"``.
    provider: str = "recaptcha"


@dataclass
class VerificationChallenge:
    """A second factor GMGN wants before it will finish the login."""

    #: e.g. ``"email_code"``, ``"verify_otp"``.
    verify_type: str
    #: Opaque id the server uses to tie a code to the message it sent.
    code_id: Optional[str] = None
    #: The rest of the server's ``data`` block, for context.
    data: Dict[str, Any] = field(default_factory=dict)
    #: Set when a previous attempt was rejected, so a prompt can say so.
    previous_error: Optional[str] = None


CaptchaSolver = Callable[[CaptchaChallenge], Union[str, Awaitable[str]]]
CodeProvider = Callable[[VerificationChallenge], Union[str, Awaitable[str]]]


async def _call(func: Callable, *args: Any) -> Any:
    """Call a callback that may be either sync or async."""
    result = func(*args)
    if inspect.isawaitable(result):
        return await result
    return result


class GmGnAuth:
    """Signs in to GMGN.ai with an email address and password.

    Example:
        ```python
        async with GmGnAuth(captcha_solver=my_solver) as auth:
            tokens = await auth.login("me@example.com", "hunter2")

        client = GmGnClient(access_token=tokens.access_token)
        ```
    """

    DEFAULT_BASE_URL = "https://gmgn.ai"
    LOGIN_PATH = "/account/login_v3"
    REFRESH_PATH = "/account/account/refresh_access_token"
    DEFAULT_APP_VERSION = "20260202-10623-98faccb"

    # curl_cffi's TLS fingerprint has to be recent enough that Cloudflare lets
    # the request through; chrome124 gets a managed challenge on this endpoint.
    DEFAULT_IMPERSONATE = "chrome136"

    #: How many times a single verification step may be re-prompted after the
    #: server rejects it (wrong email code, expired captcha, ...).
    MAX_RETRIES_PER_STEP = 3

    def __init__(
        self,
        captcha_solver: Optional[CaptchaSolver] = None,
        code_provider: Optional[CodeProvider] = None,
        base_url: Optional[str] = None,
        device_id: Optional[str] = None,
        fp_did: Optional[str] = None,
        app_version: Optional[str] = None,
        impersonate: Optional[str] = None,
        lang: str = "en",
        timeout: float = 30.0,
    ):
        """
        Initialize the authentication client.

        Args:
            captcha_solver: Callable returning a reCAPTCHA token for a
                :class:`CaptchaChallenge`. May be sync or async. Required,
                because GMGN gates the first login step on reCAPTCHA.
            code_provider: Callable returning a verification code for a
                :class:`VerificationChallenge` (email code, authenticator code).
                May be sync or async. Only needed when GMGN challenges the login.
            base_url: GMGN base URL (defaults to the official host)
            device_id: Stable device identifier; a random one is generated if
                omitted. Reusing the value across logins makes GMGN less likely
                to treat the login as coming from a new device.
            fp_did: Browser fingerprint device id, as above
            app_version: GMGN web app version string
            impersonate: curl_cffi browser fingerprint to impersonate
            lang: Language sent with the login request
            timeout: Per-request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("GMGN_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.captcha_solver = captcha_solver
        self.code_provider = code_provider
        self.device_id = device_id or os.getenv("GMGN_DEVICE_ID") or str(uuid.uuid4())
        self.fp_did = fp_did or os.getenv("GMGN_FP_DID") or uuid.uuid4().hex
        self.app_version = app_version or self.DEFAULT_APP_VERSION
        self.impersonate = impersonate or os.getenv("GMGN_IMPERSONATE", self.DEFAULT_IMPERSONATE)
        self.lang = lang
        self.timeout = timeout

        self._session: Optional[AsyncSession] = None
        self._session_lock = asyncio.Lock()

    async def __aenter__(self) -> "GmGnAuth":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def cookies(self) -> Dict[str, str]:
        """Cookies collected during login, for handing to :class:`GmGnClient`."""
        if self._session is None:
            return {}
        return {name: value for name, value in self._session.cookies.items()}

    async def _get_session(self) -> AsyncSession:
        """Return the HTTP session, priming it with the site's cookies once."""
        async with self._session_lock:
            if self._session is None:
                session = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)
                try:
                    # Pick up the cookies a browser would have before posting.
                    await session.get(f"{self.base_url}/")
                except Exception as e:  # pragma: no cover - best effort warm-up
                    logger.debug(f"Could not prime session cookies: {e}")
                self._session = session
            return self._session

    def _query_params(self) -> Dict[str, str]:
        """Query parameters GMGN's web client attaches to every API call."""
        return {
            "device_id": self.device_id,
            "fp_did": self.fp_did,
            "client_id": f"gmgn_web_{self.app_version}",
            "from_app": "gmgn",
            "app_ver": self.app_version,
            "tz_name": "Europe/Paris",
            "tz_offset": "3600",
            "app_lang": self.lang,
            "os": "web",
        }

    async def _post(self, path: str, payload: Dict[str, Any]) -> Any:
        """POST a JSON body and unwrap GMGN's ``{code, message, data}`` envelope.

        Returns the ``data`` member, which is a dict for login steps but a bare
        token string for the refresh endpoint.
        """
        session = await self._get_session()
        url = f"{self.base_url}{path}"

        try:
            response = await session.post(
                url,
                params=self._query_params(),
                json=payload,
                headers={
                    "Origin": self.base_url,
                    "Referer": f"{self.base_url}/",
                    "Content-Type": "application/json",
                },
            )
        except Exception as e:
            raise AuthenticationError(f"Login request failed: {e}")

        if response.status_code == 403:
            raise AuthenticationError(
                "GMGN returned 403 (Cloudflare challenge). Try a newer "
                f"impersonate target than {self.impersonate!r}.",
                details={"status_code": 403},
            )

        try:
            body = response.json()
        except Exception:
            raise AuthenticationError(
                f"Unexpected non-JSON response (HTTP {response.status_code})",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )

        code = body.get("code")
        if code not in (0, None):
            raise AuthenticationError(
                body.get("message") or f"Login failed with code {code}",
                details=body,
            )

        if "data" not in body:
            raise AuthenticationError("Response contained no data", details=body)
        return body["data"]

    async def login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        keep_login_state: bool = True,
    ) -> AuthTokens:
        """
        Log in with an email address and password.

        Args:
            email: Account email; falls back to the ``GMGN_EMAIL`` environment
                variable
            password: Account password; falls back to ``GMGN_PASSWORD``
            keep_login_state: Ask GMGN for a long-lived session

        Returns:
            The access and refresh tokens for the account.

        Raises:
            AuthenticationError: If the credentials are rejected, or the server
                asks for something that has not been configured
            CaptchaRequiredError: If no ``captcha_solver`` was provided
            VerificationRequiredError: If a second factor is required and no
                ``code_provider`` was provided
        """
        email = email or os.getenv("GMGN_EMAIL")
        password = password or os.getenv("GMGN_PASSWORD")

        if not email:
            raise AuthenticationError("An email address is required to log in")
        if not password:
            raise AuthenticationError("A password is required to log in")
        if self.captcha_solver is None:
            raise CaptchaRequiredError(
                "GMGN requires a reCAPTCHA token for the first login step. "
                "Pass a captcha_solver to GmGnAuth."
            )

        ephemeral = srp.generate_ephemeral()

        payload: Dict[str, Any] = {
            "account": email,
            "enable_passkey": False,
            "passkey_support": False,
            "srp_A": ephemeral.public,
            "keep_login_state": keep_login_state,
            "lang": self.lang,
            "version": "2.0",
        }

        # Carried across steps: the server sends the SRP material once, but
        # later steps still need it.
        key_data: Dict[str, Any] = {}
        # The last step the server described, replayed when it rejects an answer.
        last_step: Optional[Dict[str, Any]] = None
        previous_error: Optional[str] = None
        attempts = 0
        max_attempts = self.MAX_RETRIES_PER_STEP * 6

        while True:
            attempts += 1
            if attempts > max_attempts:
                raise AuthenticationError("Login did not complete; too many steps")

            try:
                step = await self._post(self.LOGIN_PATH, payload)
                if not isinstance(step, dict):
                    raise AuthenticationError(
                        "Unexpected login response", details={"data": step}
                    )
                previous_error = None
            except AuthenticationError as e:
                details = e.details if isinstance(e.details, dict) else {}
                if details.get("code") in RETRYABLE_CODES and last_step is not None:
                    # The server rejected a code or captcha. Re-prompt for the
                    # same step rather than dropping the whole login.
                    step = last_step
                    previous_error = e.message
                else:
                    raise

            if step.get("traditional_login"):
                raise AuthenticationError(
                    "This account uses GMGN's legacy login, which is not supported"
                )

            if step.get("done"):
                return self._build_tokens(step.get("data") or {})

            last_step = step
            data = step.get("data") or {}
            for name in ("key", "key_ver", "salt", "user_id", "srp_B"):
                if data.get(name) is not None:
                    key_data[name] = data[name]

            requirements: List[str] = list(step.get("require") or [])
            if not requirements:
                raise AuthenticationError(
                    "Login stalled: server asked for nothing and did not finish",
                    details=step,
                )

            answer = await self._answer_requirements(
                requirements, data, key_data, ephemeral, email, password, previous_error
            )

            payload = {"session_id": step.get("session_id"), **answer}

    async def _answer_requirements(
        self,
        requirements: List[str],
        data: Dict[str, Any],
        key_data: Dict[str, Any],
        ephemeral: srp.Ephemeral,
        email: str,
        password: str,
        previous_error: Optional[str],
    ) -> Dict[str, Any]:
        """Produce the fields that satisfy one round of ``require`` entries."""
        answer: Dict[str, Any] = {}

        # A "a|b" entry means either one will do; take the first we support.
        flattened: List[str] = []
        for requirement in requirements:
            if "|" in requirement:
                alternatives = requirement.split("|")
                supported = [a for a in alternatives if a in _SUPPORTED_REQUIREMENTS]
                flattened.append(supported[0] if supported else alternatives[0])
            else:
                flattened.append(requirement)

        for requirement in flattened:
            if requirement == REQUIRE_RECAPTCHA:
                answer["captcha_token"] = await self._solve_captcha(
                    CaptchaChallenge(
                        site_key=data.get("site_key", ""),
                        key_type=data.get("key_type") or "score",
                        action="login",
                        lang=self.lang,
                        provider="recaptcha",
                    )
                )

            elif requirement == REQUIRE_CAPTCHA:
                answer["captcha_response"] = await self._solve_captcha(
                    CaptchaChallenge(
                        site_key=data.get("site_key", ""),
                        key_type=data.get("key_type") or "widget",
                        action="login",
                        lang=self.lang,
                        captcha_data=data.get("captcha_data", ""),
                        provider="geetest",
                    )
                )

            elif requirement == REQUIRE_PASSWORD:
                answer["client_M"] = self._derive_proof(key_data, ephemeral, password)

            elif requirement == REQUIRE_PASSWORD_SECRET:
                # Only reached when registering or resetting a password, where
                # the client uploads a new verifier. Logging in never sets one.
                raise AuthenticationError(
                    "GMGN asked this login to set a new password verifier, "
                    "which is not supported. Sign in on the website first."
                )

            elif requirement in (REQUIRE_EMAIL_CODE, REQUIRE_VERIFY_EMAIL):
                code_id = data.get("email_code_id") or data.get("code_id")
                answer["email_code"] = await self._request_code(
                    VerificationChallenge(
                        verify_type=requirement,
                        code_id=code_id,
                        data=data,
                        previous_error=previous_error,
                    )
                )
                if code_id:
                    answer["email_code_id"] = code_id

            elif requirement == REQUIRE_SMS_CODE:
                code_id = data.get("sms_code_id")
                answer["sms_code"] = await self._request_code(
                    VerificationChallenge(
                        verify_type=requirement,
                        code_id=code_id,
                        data=data,
                        previous_error=previous_error,
                    )
                )
                if code_id:
                    answer["sms_code_id"] = code_id

            elif requirement in (REQUIRE_OTP, REQUIRE_OTP_CODE):
                answer["otp_code"] = await self._request_code(
                    VerificationChallenge(
                        verify_type=REQUIRE_OTP,
                        data=data,
                        previous_error=previous_error,
                    )
                )

            else:
                raise AuthenticationError(
                    f"GMGN requires {requirement!r}, which this library does not "
                    "support. Complete this login in a browser."
                )

        return answer

    def _derive_proof(
        self, key_data: Dict[str, Any], ephemeral: srp.Ephemeral, password: str
    ) -> str:
        """Compute the SRP client proof for the password step."""
        salt = key_data.get("salt")
        server_public = key_data.get("srp_B")
        user_id = key_data.get("user_id")

        if not salt or not server_public:
            raise AuthenticationError(
                "GMGN asked for a password proof without sending SRP parameters. "
                "The account may not exist or may not use password login.",
                details={"has_salt": bool(salt), "has_srp_B": bool(server_public)},
            )

        private_key = srp.derive_private_key(salt, str(user_id or ""), password)
        try:
            session = srp.derive_session(
                ephemeral.secret, server_public, salt, str(user_id or ""), private_key
            )
        except ValueError as e:
            raise AuthenticationError(f"SRP handshake failed: {e}")
        return session.proof

    async def _solve_captcha(self, challenge: CaptchaChallenge) -> str:
        if self.captcha_solver is None:
            raise CaptchaRequiredError(
                "GMGN requires a captcha token. Pass a captcha_solver to GmGnAuth.",
                details=challenge,
            )
        token = await _call(self.captcha_solver, challenge)
        if not token:
            raise CaptchaRequiredError("The captcha solver returned no token")
        return token

    async def _request_code(self, challenge: VerificationChallenge) -> str:
        if self.code_provider is None:
            raise VerificationRequiredError(
                f"GMGN requires a {challenge.verify_type!r} verification code. "
                "Pass a code_provider to GmGnAuth.",
                details=challenge,
            )
        code = await _call(self.code_provider, challenge)
        if not code:
            raise VerificationRequiredError("The code provider returned no code")
        return str(code).strip()

    @staticmethod
    def _build_tokens(data: Dict[str, Any]) -> AuthTokens:
        """Normalise the final payload into :class:`AuthTokens`."""
        access = data.get("access_token")
        refresh = data.get("refresh_token")

        # GMGN sends the refresh token either bare or wrapped with its expiry.
        refresh_token = None
        refresh_expires_at = None
        if isinstance(refresh, dict):
            refresh_token = refresh.get("token")
            refresh_expires_at = refresh.get("expire_at")
        elif refresh:
            refresh_token = refresh

        if isinstance(access, dict):
            access_token = access.get("token")
            expires_at = access.get("expire_at")
        else:
            access_token = access
            expires_at = data.get("expire_at")

        if not access_token:
            raise AuthenticationError(
                "Login finished without returning an access token", details=data
            )

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            user_id=data.get("user_id"),
        )

    async def refresh(self, refresh_token: str) -> AuthTokens:
        """
        Exchange a refresh token for a fresh access token.

        Args:
            refresh_token: The refresh token from a previous login

        Returns:
            The refreshed tokens.

        Raises:
            AuthenticationError: If the refresh token is rejected
        """
        if not refresh_token:
            raise AuthenticationError("A refresh token is required")

        data = await self._post(self.REFRESH_PATH, {"refresh_token": refresh_token})

        # This endpoint answers with the new access token alone, either as a
        # bare string or wrapped in the usual object.
        if isinstance(data, str):
            data = {"access_token": data}
        elif isinstance(data, dict) and "access_token" not in data:
            data = {"access_token": data}
        elif not isinstance(data, dict):
            raise AuthenticationError("Unexpected refresh response", details={"data": data})

        tokens = self._build_tokens(data)
        # Keep the caller's refresh token so the result is a complete credential.
        if tokens.refresh_token is None:
            tokens.refresh_token = refresh_token
        return tokens


async def login(
    email: Optional[str] = None,
    password: Optional[str] = None,
    captcha_solver: Optional[CaptchaSolver] = None,
    code_provider: Optional[CodeProvider] = None,
    **kwargs: Any,
) -> AuthTokens:
    """
    Log in with an email address and password and return the tokens.

    A convenience wrapper around :class:`GmGnAuth` for one-shot logins.

    Args:
        email: Account email; falls back to ``GMGN_EMAIL``
        password: Account password; falls back to ``GMGN_PASSWORD``
        captcha_solver: Returns a reCAPTCHA token for a :class:`CaptchaChallenge`
        code_provider: Returns a code for a :class:`VerificationChallenge`
        **kwargs: Passed through to :class:`GmGnAuth`

    Returns:
        The access and refresh tokens for the account.
    """
    async with GmGnAuth(
        captcha_solver=captcha_solver, code_provider=code_provider, **kwargs
    ) as auth:
        return await auth.login(email, password)
