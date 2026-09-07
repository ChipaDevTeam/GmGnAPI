"""
Log in to GMGN.ai with an email address and password.

GMGN authenticates with SRP-6a: your password is never sent, only a proof
derived from it and the server's salt. GmGnAPI handles that handshake.

What GmGnAPI cannot do for you is the reCAPTCHA that guards the first step.
reCAPTCHA v3 scores the browser itself, so a token has to come from a real
browser or a solving service. Supply one via ``captcha_solver``; the two
approaches below are the usual ones.

Run:

    export GMGN_EMAIL="you@example.com"
    export GMGN_PASSWORD="..."
    python examples/login.py

Built with Chipa Editor - https://chipaeditor.com
"""

import asyncio
import logging
import os

from gmgnapi import GmGnAuth, GmGnClient
from gmgnapi.auth import CaptchaChallenge, VerificationChallenge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def solve_with_browser(challenge: CaptchaChallenge) -> str:
    """Get a reCAPTCHA token by running Google's script in a real browser.

    Needs `pip install playwright && playwright install chromium`. This is the
    approach that keeps the token's score high, because the score reflects the
    browser it came from.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        try:
            await page.goto("https://gmgn.ai/", wait_until="domcontentloaded")
            # GMGN uses reCAPTCHA Enterprise, loaded on demand — a freshly
            # loaded page has no window.grecaptcha at all, and the standard
            # api.js would give you a grecaptcha without .enterprise.
            await page.add_script_tag(
                url="https://www.recaptcha.net/recaptcha/enterprise.js"
                    f"?render={challenge.site_key}"
            )
            token = await page.evaluate(
                """([siteKey, action]) => new Promise((resolve, reject) => {
                    grecaptcha.enterprise.ready(() => {
                        grecaptcha.enterprise.execute(siteKey, { action })
                            .then(resolve)
                            .catch(reject)
                    })
                })""",
                [challenge.site_key, challenge.action],
            )
            return token
        finally:
            await browser.close()


async def solve_with_service(challenge: CaptchaChallenge) -> str:
    """Get a reCAPTCHA token from a solving service (2Captcha shown here).

    Needs `pip install 2captcha-python` and a ``TWOCAPTCHA_API_KEY``.
    """
    from twocaptcha import TwoCaptcha

    solver = TwoCaptcha(os.environ["TWOCAPTCHA_API_KEY"])
    result = await asyncio.to_thread(
        solver.recaptcha,
        sitekey=challenge.site_key,
        url="https://gmgn.ai/",
        version="v3",
        enterprise=1,  # GMGN uses reCAPTCHA Enterprise
        action=challenge.action,
        score=0.7,
    )
    return result["code"]


def ask_for_code(challenge: VerificationChallenge) -> str:
    """Prompt for a second factor, if GMGN asks for one.

    GMGN commonly emails a code when it sees a device it does not recognise.
    """
    if challenge.previous_error:
        print(f"That code was rejected: {challenge.previous_error}")

    prompts = {
        "email_code": "Enter the code GMGN emailed you: ",
        "verify_email": "Enter the code GMGN emailed you: ",
        "verify_otp": "Enter your authenticator code: ",
        "sms_code": "Enter the code GMGN texted you: ",
    }
    return input(prompts.get(challenge.verify_type, f"Enter your {challenge.verify_type}: "))


async def main() -> None:
    email = os.getenv("GMGN_EMAIL")
    password = os.getenv("GMGN_PASSWORD")

    if not email or not password:
        print("Set GMGN_EMAIL and GMGN_PASSWORD first.")
        return

    # Reusing a device_id across logins makes GMGN less likely to treat each
    # login as coming from a new device and email you a code every time.
    device_id = os.getenv("GMGN_DEVICE_ID")

    async with GmGnAuth(
        captcha_solver=solve_with_browser,
        code_provider=ask_for_code,
        device_id=device_id,
    ) as auth:
        tokens = await auth.login(email, password)
        logger.info("Logged in as %s", tokens.user_id)

        # Keep the refresh token to skip the captcha next time.
        if tokens.refresh_token:
            logger.info("Refresh token acquired; store it somewhere safe.")

        cookies = auth.cookies

    # The access token unlocks the authenticated WebSocket channels. The client
    # picks it up from self.access_token, so subscribing needs no extra argument.
    wallet = os.getenv("GMGN_WALLET_ADDRESS")
    if not wallet:
        logger.info("Set GMGN_WALLET_ADDRESS to stream wallet trades.")
        return

    client = GmGnClient(access_token=tokens.access_token, cookies=cookies)

    async def on_trade(data):
        logger.info("Trade: %s", data)

    client.on("wallet_trade_data", on_trade)

    async with client:
        await client.subscribe_wallet_trades(chain="sol", wallet_address=wallet)
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
