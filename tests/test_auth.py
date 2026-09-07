"""
Tests for email and password login against GMGN.

The login is a multi-step exchange, so these drive a scripted fake of GMGN's
``/account/login_v3`` endpoint. The happy-path test plays a real SRP server:
it verifies the proof the client sends against a verifier derived from the
password, so a broken handshake fails here rather than silently authenticating.
"""

import secrets

import pytest

from gmgnapi import srp
from gmgnapi.auth import (
    CaptchaChallenge,
    GmGnAuth,
    VerificationChallenge,
)
from gmgnapi.exceptions import (
    AuthenticationError,
    CaptchaRequiredError,
    VerificationRequiredError,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    """Stands in for curl_cffi's AsyncSession, returning scripted responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.cookies = {"cf_clearance": "fake-clearance"}
        self.closed = False

    async def post(self, url, params=None, json=None, headers=None):
        self.requests.append({"url": url, "params": params, "json": json})
        if not self._responses:
            raise AssertionError(f"unexpected extra request to {url}: {json}")
        nxt = self._responses.pop(0)
        return nxt(json) if callable(nxt) else nxt

    async def get(self, url):
        return FakeResponse({})

    async def close(self):
        self.closed = True


def envelope(data, code=0, message="success"):
    return FakeResponse({"code": code, "message": message, "data": data})


def make_auth(responses, **kwargs):
    """Build a GmGnAuth wired to a scripted fake session."""
    kwargs.setdefault("captcha_solver", lambda challenge: "captcha-token")
    auth = GmGnAuth(**kwargs)
    session = FakeSession(responses)

    async def _get_session():
        return session

    auth._get_session = _get_session
    auth._session = session
    return auth, session


class SRPServer:
    """A minimal SRP-6a server, to check the client's proof for real."""

    def __init__(self, user_id, password, salt=None):
        self.user_id = user_id
        self.salt = salt or srp.generate_salt()
        private_key = srp.derive_private_key(self.salt, user_id, password)
        self.verifier = srp.SRPInteger.from_hex(srp.derive_verifier(private_key))
        self._b = srp.SRPInteger.from_hex(secrets.token_bytes(32).hex())
        # B = (k*v + g^b) mod N
        self.B = (
            srp.k.multiply(self.verifier).add(srp.g.mod_pow(self._b, srp.N)).mod(srp.N)
        )

    def expected_proof(self, client_public):
        A = srp.SRPInteger.from_hex(client_public)
        u = srp.H(A, self.B)
        S = A.multiply(self.verifier.mod_pow(u, srp.N)).mod(srp.N).mod_pow(self._b, srp.N)
        K = srp.H(S)
        M = srp.H(
            srp.H(srp.N).xor(srp.H(srp.g)),
            srp.H(self.user_id),
            srp.SRPInteger.from_hex(self.salt),
            A,
            self.B,
            K,
        )
        return M.to_hex()


class TestSuccessfulLogin:
    async def test_full_srp_exchange(self):
        """Captcha, then a password proof a real SRP server accepts."""
        user_id = "user-4242"
        password = "correct horse battery staple"
        server = SRPServer(user_id, password)
        captured = {}

        def step_two(body):
            captured["captcha"] = body
            return envelope(
                {
                    "done": False,
                    "session_id": "sess-1",
                    "require": ["verify_password"],
                    "data": {
                        "salt": server.salt,
                        "srp_B": server.B.to_hex(),
                        "user_id": user_id,
                    },
                }
            )

        def step_three(body):
            captured["proof"] = body
            return envelope(
                {
                    "done": True,
                    "data": {
                        "access_token": "access-abc",
                        "refresh_token": {"token": "refresh-xyz", "expire_at": 1800000000},
                        "user_id": user_id,
                    },
                }
            )

        auth, session = make_auth(
            [
                envelope(
                    {
                        "done": False,
                        "session_id": "sess-1",
                        "require": ["verify_recaptcha"],
                        "data": {"site_key": "6Lf3-key", "key_type": "score"},
                    }
                ),
                step_two,
                step_three,
            ]
        )

        tokens = await auth.login("me@example.com", password)

        assert tokens.access_token == "access-abc"
        assert tokens.refresh_token == "refresh-xyz"
        assert tokens.refresh_expires_at == 1800000000
        assert tokens.user_id == user_id

        # Step 1 sends the account and the client's public ephemeral.
        first = session.requests[0]["json"]
        assert first["account"] == "me@example.com"
        assert first["version"] == "2.0"
        assert len(first["srp_A"]) == 512
        assert "password" not in str(first)

        # Step 2 answers the captcha against the same session.
        assert captured["captcha"] == {"session_id": "sess-1", "captcha_token": "captcha-token"}

        # Step 3's proof must be the one the server independently computes.
        assert captured["proof"]["client_M"] == server.expected_proof(first["srp_A"])

    async def test_password_is_never_transmitted(self):
        server = SRPServer("u1", "s3cret-password")
        auth, session = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["verify_recaptcha"],
                          "data": {"site_key": "k"}}),
                envelope({"done": False, "session_id": "s", "require": ["verify_password"],
                          "data": {"salt": server.salt, "srp_B": server.B.to_hex(), "user_id": "u1"}}),
                envelope({"done": True, "data": {"access_token": "t"}}),
            ]
        )
        await auth.login("me@example.com", "s3cret-password")

        for request in session.requests:
            assert "s3cret-password" not in str(request["json"])

    async def test_bare_refresh_token_string(self):
        auth, _ = make_auth(
            [envelope({"done": True, "data": {"access_token": "a", "refresh_token": "r"}})]
        )
        tokens = await auth.login("me@example.com", "pw")
        assert tokens.refresh_token == "r"
        assert tokens.refresh_expires_at is None

    async def test_async_captcha_solver(self):
        async def solver(challenge):
            assert isinstance(challenge, CaptchaChallenge)
            return "async-token"

        captured = {}

        def check(body):
            captured.update(body)
            return envelope({"done": True, "data": {"access_token": "a"}})

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["verify_recaptcha"],
                          "data": {"site_key": "k"}}),
                check,
            ],
            captcha_solver=solver,
        )
        await auth.login("me@example.com", "pw")
        assert captured["captcha_token"] == "async-token"

    async def test_captcha_challenge_carries_server_details(self):
        seen = {}

        def solver(challenge):
            seen["challenge"] = challenge
            return "tok"

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["verify_recaptcha"],
                          "data": {"site_key": "site-123", "key_type": "score"}}),
                envelope({"done": True, "data": {"access_token": "a"}}),
            ],
            captcha_solver=solver,
        )
        await auth.login("me@example.com", "pw")

        challenge = seen["challenge"]
        assert challenge.site_key == "site-123"
        assert challenge.key_type == "score"
        assert challenge.action == "login"
        assert challenge.provider == "recaptcha"


class TestSecondFactor:
    async def test_email_code_step(self):
        seen = {}

        def code_provider(challenge):
            seen["challenge"] = challenge
            return " 123456 "

        captured = {}

        def check(body):
            captured.update(body)
            return envelope({"done": True, "data": {"access_token": "a"}})

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["email_code"],
                          "data": {"email_code_id": "code-1"}}),
                check,
            ],
            code_provider=code_provider,
        )
        await auth.login("me@example.com", "pw")

        assert captured["email_code"] == "123456"
        assert captured["email_code_id"] == "code-1"
        assert seen["challenge"].verify_type == "email_code"
        assert seen["challenge"].code_id == "code-1"

    async def test_authenticator_code_step(self):
        captured = {}

        def check(body):
            captured.update(body)
            return envelope({"done": True, "data": {"access_token": "a"}})

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["verify_otp"], "data": {}}),
                check,
            ],
            code_provider=lambda challenge: "654321",
        )
        await auth.login("me@example.com", "pw")
        assert captured["otp_code"] == "654321"

    async def test_alternative_requirements_pick_a_supported_one(self):
        """A "a|b" requirement means either will do."""
        captured = {}

        def check(body):
            captured.update(body)
            return envelope({"done": True, "data": {"access_token": "a"}})

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s",
                          "require": ["verify_passkey|email_code"],
                          "data": {"email_code_id": "c1"}}),
                check,
            ],
            code_provider=lambda challenge: "111111",
        )
        await auth.login("me@example.com", "pw")
        assert captured["email_code"] == "111111"

    async def test_rejected_code_is_reprompted(self):
        """A wrong code re-prompts instead of ending the login."""
        attempts = []

        def code_provider(challenge):
            attempts.append(challenge.previous_error)
            return "000000" if len(attempts) == 1 else "123456"

        auth, _ = make_auth(
            [
                envelope({"done": False, "session_id": "s", "require": ["email_code"],
                          "data": {"email_code_id": "c1"}}),
                FakeResponse({"code": -102000, "message": "wrong code", "data": {}}),
                envelope({"done": True, "data": {"access_token": "a"}}),
            ],
            code_provider=code_provider,
        )
        tokens = await auth.login("me@example.com", "pw")

        assert tokens.access_token == "a"
        assert len(attempts) == 2
        assert attempts[0] is None
        assert attempts[1] == "wrong code"


class TestMissingConfiguration:
    async def test_login_without_captcha_solver(self):
        auth = GmGnAuth()
        with pytest.raises(CaptchaRequiredError, match="captcha_solver"):
            await auth.login("me@example.com", "pw")

    async def test_no_request_is_made_without_a_solver(self):
        """Fail before sending the email address anywhere."""
        auth, session = make_auth([], captcha_solver=None)
        with pytest.raises(CaptchaRequiredError):
            await auth.login("me@example.com", "pw")
        assert session.requests == []

    async def test_login_without_code_provider(self):
        auth, _ = make_auth(
            [envelope({"done": False, "session_id": "s", "require": ["email_code"], "data": {}})]
        )
        with pytest.raises(VerificationRequiredError, match="code_provider"):
            await auth.login("me@example.com", "pw")

    async def test_missing_email(self, monkeypatch):
        monkeypatch.delenv("GMGN_EMAIL", raising=False)
        auth, _ = make_auth([])
        with pytest.raises(AuthenticationError, match="email address is required"):
            await auth.login(password="pw")

    async def test_missing_password(self, monkeypatch):
        monkeypatch.delenv("GMGN_PASSWORD", raising=False)
        auth, _ = make_auth([])
        with pytest.raises(AuthenticationError, match="password is required"):
            await auth.login("me@example.com")

    async def test_credentials_from_environment(self, monkeypatch):
        monkeypatch.setenv("GMGN_EMAIL", "env@example.com")
        monkeypatch.setenv("GMGN_PASSWORD", "env-password")
        auth, session = make_auth([envelope({"done": True, "data": {"access_token": "a"}})])
        await auth.login()
        assert session.requests[0]["json"]["account"] == "env@example.com"

    async def test_empty_captcha_token_is_rejected(self):
        auth, _ = make_auth(
            [envelope({"done": False, "session_id": "s", "require": ["verify_recaptcha"],
                       "data": {"site_key": "k"}})],
            captcha_solver=lambda challenge: "",
        )
        with pytest.raises(CaptchaRequiredError, match="no token"):
            await auth.login("me@example.com", "pw")


class TestServerErrors:
    async def test_rejected_credentials(self):
        auth, _ = make_auth(
            [FakeResponse({"code": -10001, "message": "Incorrect password", "data": {}})]
        )
        with pytest.raises(AuthenticationError, match="Incorrect password"):
            await auth.login("me@example.com", "pw")

    async def test_cloudflare_challenge_is_explained(self):
        auth, _ = make_auth(
            [FakeResponse(None, status_code=403, text="<html>Just a moment...</html>")]
        )
        with pytest.raises(AuthenticationError, match="Cloudflare"):
            await auth.login("me@example.com", "pw")

    async def test_non_json_response(self):
        auth, _ = make_auth([FakeResponse(None, status_code=502, text="bad gateway")])
        with pytest.raises(AuthenticationError, match="non-JSON"):
            await auth.login("me@example.com", "pw")

    async def test_legacy_login_is_reported(self):
        auth, _ = make_auth([envelope({"traditional_login": True, "done": False})])
        with pytest.raises(AuthenticationError, match="legacy login"):
            await auth.login("me@example.com", "pw")

    async def test_unsupported_requirement(self):
        auth, _ = make_auth(
            [envelope({"done": False, "session_id": "s", "require": ["verify_passkey"], "data": {}})]
        )
        with pytest.raises(AuthenticationError, match="verify_passkey"):
            await auth.login("me@example.com", "pw")

    async def test_password_proof_without_srp_parameters(self):
        auth, _ = make_auth(
            [envelope({"done": False, "session_id": "s", "require": ["verify_password"], "data": {}})]
        )
        with pytest.raises(AuthenticationError, match="without sending SRP parameters"):
            await auth.login("me@example.com", "pw")

    async def test_empty_requirements_does_not_loop(self):
        auth, _ = make_auth([envelope({"done": False, "session_id": "s", "require": [], "data": {}})])
        with pytest.raises(AuthenticationError, match="stalled"):
            await auth.login("me@example.com", "pw")

    async def test_done_without_an_access_token(self):
        auth, _ = make_auth([envelope({"done": True, "data": {"user_id": "u"}})])
        with pytest.raises(AuthenticationError, match="without returning an access token"):
            await auth.login("me@example.com", "pw")

    async def test_password_secret_is_refused(self):
        """Setting a new verifier is a registration flow, not a login."""
        auth, _ = make_auth(
            [envelope({"done": False, "session_id": "s", "require": ["password_secret"],
                       "data": {"salt": "ab", "user_id": "u"}})]
        )
        with pytest.raises(AuthenticationError, match="new password verifier"):
            await auth.login("me@example.com", "pw")


class TestRefresh:
    async def test_refresh_returns_a_new_access_token(self):
        auth, session = make_auth([envelope({"access_token": "fresh-access"})])
        tokens = await auth.refresh("refresh-xyz")

        assert tokens.access_token == "fresh-access"
        # The caller's refresh token is preserved so the result stays usable.
        assert tokens.refresh_token == "refresh-xyz"
        assert session.requests[0]["json"] == {"refresh_token": "refresh-xyz"}
        assert session.requests[0]["url"].endswith("/account/account/refresh_access_token")

    async def test_refresh_accepts_a_bare_token_string(self):
        """GMGN answers this endpoint with the token itself, not an object."""
        auth, _ = make_auth([envelope("bare-access-token")])
        tokens = await auth.refresh("refresh-xyz")
        assert tokens.access_token == "bare-access-token"
        assert tokens.refresh_token == "refresh-xyz"

    async def test_refresh_accepts_a_wrapped_token(self):
        auth, _ = make_auth([envelope({"token": "wrapped", "expire_at": 123})])
        tokens = await auth.refresh("refresh-xyz")
        assert tokens.access_token == "wrapped"
        assert tokens.expires_at == 123

    async def test_refresh_requires_a_token(self):
        auth, _ = make_auth([])
        with pytest.raises(AuthenticationError, match="refresh token is required"):
            await auth.refresh("")

    async def test_rejected_refresh_token(self):
        auth, _ = make_auth([FakeResponse({"code": -1, "message": "expired", "data": {}})])
        with pytest.raises(AuthenticationError, match="expired"):
            await auth.refresh("stale")


class TestRequestShape:
    async def test_query_parameters_match_the_web_client(self):
        auth, session = make_auth(
            [envelope({"done": True, "data": {"access_token": "a"}})],
            device_id="device-1",
            fp_did="fp-1",
        )
        await auth.login("me@example.com", "pw")

        params = session.requests[0]["params"]
        assert params["device_id"] == "device-1"
        assert params["fp_did"] == "fp-1"
        assert params["from_app"] == "gmgn"
        assert params["os"] == "web"
        assert params["client_id"].startswith("gmgn_web_")

    async def test_login_url(self):
        auth, session = make_auth([envelope({"done": True, "data": {"access_token": "a"}})])
        await auth.login("me@example.com", "pw")
        assert session.requests[0]["url"] == "https://gmgn.ai/account/login_v3"

    async def test_impersonation_defaults_past_the_cloudflare_challenge(self):
        """chrome124 gets a managed challenge on this endpoint; stay newer."""
        assert GmGnAuth.DEFAULT_IMPERSONATE != "chrome124"
        assert GmGnAuth().impersonate == GmGnAuth.DEFAULT_IMPERSONATE

    async def test_close_releases_the_session(self):
        auth, session = make_auth([envelope({"done": True, "data": {"access_token": "a"}})])
        await auth.login("me@example.com", "pw")
        await auth.close()
        assert session.closed

    async def test_cookies_are_exposed_for_the_websocket_client(self):
        auth, _ = make_auth([envelope({"done": True, "data": {"access_token": "a"}})])
        await auth.login("me@example.com", "pw")
        assert auth.cookies["cf_clearance"] == "fake-clearance"


class TestAuthTokens:
    def test_str_does_not_leak_the_token(self):
        from gmgnapi import AuthTokens

        tokens = AuthTokens(access_token="super-secret", refresh_token="also-secret", user_id="u1")
        assert "super-secret" not in str(tokens)
        assert "also-secret" not in str(tokens)
        assert "u1" in str(tokens)


class TestClientIntegration:
    async def test_client_login_stores_token_and_cookies(self, monkeypatch):
        from gmgnapi import GmGnClient
        from gmgnapi.models import AuthTokens

        class StubAuth:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.cookies = {"cf_clearance": "abc"}
                StubAuth.last = self

            async def login(self, email, password):
                self.credentials = (email, password)
                return AuthTokens(access_token="tok", refresh_token="ref", user_id="u9")

            async def close(self):
                self.closed = True

        monkeypatch.setattr("gmgnapi.auth.GmGnAuth", StubAuth)

        client = GmGnClient(device_id="d1", fp_did="f1", cookies={"existing": "1"})
        tokens = await client.login("me@example.com", "pw", captcha_solver=lambda c: "t")

        assert tokens.access_token == "tok"
        assert client.access_token == "tok"
        assert client.cookies == {"existing": "1", "cf_clearance": "abc"}
        # The client's identity is passed through so the WebSocket handshake
        # matches the session that logged in.
        assert StubAuth.last.kwargs["device_id"] == "d1"
        assert StubAuth.last.kwargs["fp_did"] == "f1"
        assert StubAuth.last.closed is True
