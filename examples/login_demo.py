"""
A local web page for testing GMGN email/password login end to end.

Why a web page rather than a terminal script: GMGN's first login step is gated
by reCAPTCHA v3, which scores the browser it runs in and issues a token bound to
gmgn.ai. A real browser is the only place that token can come from, so this demo
puts one in the loop:

    browser (reCAPTCHA token)  ->  this server  ->  gmgnapi (SRP)  ->  GMGN

Two ways to get the token, chosen in the form:

* **Automatic** — the server drives a Playwright browser to gmgn.ai and runs
  ``grecaptcha.enterprise.execute`` there. Needs ``pip install playwright`` and
  ``playwright install chromium``.
* **Manual** — you paste a token yourself. The page shows the exact snippet to
  run in a devtools console on an open gmgn.ai tab. No extra dependencies.

The page then shows every step of the exchange, prompts for an email or
authenticator code if GMGN asks for one, and prints the tokens at the end.

Run, from the repository root:

    python3 -m venv .venv                    # once; system Python is often
    .venv/bin/pip install -e ".[demo]"       # "externally managed" (PEP 668)
    .venv/bin/python examples/login_demo.py  # then open http://127.0.0.1:8765

For the automatic captcha option, also:

    .venv/bin/pip install playwright && .venv/bin/playwright install chromium

Your password is used to compute an SRP proof and is never sent to GMGN, never
written to disk, and never logged. The server binds to localhost only. It is a
debugging tool: do not expose it to a network.

Built with Chipa Editor - https://chipaeditor.com
"""

import argparse
import asyncio
import secrets
import uuid
import webbrowser
from typing import Any, Dict, List, Optional

from aiohttp import web

from gmgnapi import GmGnAuth
from gmgnapi.auth import CaptchaChallenge, VerificationChallenge

HOST = "127.0.0.1"
PORT = 8765

# The reCAPTCHA action GMGN's own login uses.
LOGIN_ACTION = "login"

# GMGN loads reCAPTCHA Enterprise from recaptcha.net (not the standard
# api.js), so tokens come from grecaptcha.enterprise, not grecaptcha.
ENTERPRISE_JS = "https://www.recaptcha.net/recaptcha/enterprise.js"


class LoggingAuth(GmGnAuth):
    """A GmGnAuth that reports each protocol step to the page."""

    def __init__(self, session: "LoginSession", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._demo = session

    async def _post(self, path: str, payload: Dict[str, Any]) -> Any:
        # Show what is being sent, with anything secret reduced to a shape.
        self._demo.log("request", f"POST {path}", detail=_redact(payload))
        data = await super()._post(path, payload)
        if isinstance(data, dict):
            if data.get("done"):
                self._demo.log("response", "done — tokens issued")
            else:
                required = ", ".join(data.get("require") or []) or "nothing"
                self._demo.log("response", f"server requires: {required}")
        else:
            self._demo.log("response", "token received")
        return data


def _redact(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Describe a request body without echoing secrets back to the page."""
    out: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in ("srp_A", "client_M", "captcha_token", "password_secret"):
            out[key] = f"<{len(str(value))} chars>"
        elif key in ("email_code", "otp_code", "sms_code"):
            out[key] = "<code>"
        else:
            out[key] = value
    return out


class LoginSession:
    """One login attempt, driven by the page."""

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.events: List[Dict[str, Any]] = []
        self.state = "running"
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.prompt: Optional[Dict[str, Any]] = None
        self._answer: Optional[asyncio.Future] = None
        self.task: Optional[asyncio.Task] = None

    def log(self, kind: str, message: str, detail: Any = None) -> None:
        self.events.append({"kind": kind, "message": message, "detail": detail})

    async def ask(self, kind: str, message: str, **extra: Any) -> str:
        """Put a prompt on the page and wait for the answer."""
        loop = asyncio.get_running_loop()
        self._answer = loop.create_future()
        self.prompt = {"kind": kind, "message": message, **extra}
        self.log("prompt", message)
        try:
            return await self._answer
        finally:
            self.prompt = None
            self._answer = None

    def answer(self, value: str) -> bool:
        if self._answer is None or self._answer.done():
            return False
        self._answer.set_result(value)
        return True

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "events": self.events,
            "prompt": self.prompt,
            "result": self.result,
            "error": self.error,
        }


SESSIONS: Dict[str, LoginSession] = {}


async def solve_with_playwright(session: LoginSession, challenge: CaptchaChallenge) -> str:
    """Run grecaptcha on gmgn.ai in a real browser and return the token."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run `pip install playwright && "
            "playwright install chromium`, or choose the manual token option."
        )

    session.log("step", "Launching a browser to solve reCAPTCHA on gmgn.ai")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("https://gmgn.ai/", wait_until="domcontentloaded")
            # GMGN uses reCAPTCHA Enterprise and loads it lazily, so the plain
            # page has no grecaptcha at all until we add the script ourselves.
            await page.add_script_tag(
                url=f"{ENTERPRISE_JS}?render={challenge.site_key}"
            )
            token = await page.evaluate(
                """([siteKey, action]) => new Promise((resolve, reject) => {
                    grecaptcha.enterprise.ready(() => {
                        grecaptcha.enterprise.execute(siteKey, { action })
                            .then(resolve).catch(reject)
                    })
                })""",
                [challenge.site_key, challenge.action],
            )
        finally:
            await browser.close()

    session.log("step", f"reCAPTCHA token acquired ({len(token)} chars)")
    return token


async def run_login(session: LoginSession, form: Dict[str, Any]) -> None:
    """Drive one login attempt, reporting progress to the page."""

    async def captcha_solver(challenge: CaptchaChallenge) -> str:
        session.log(
            "step",
            f"GMGN wants a {challenge.provider} token "
            f"(type {challenge.key_type}, action {challenge.action})",
            detail={"site_key": challenge.site_key},
        )
        if form["captcha_mode"] == "playwright":
            return await solve_with_playwright(session, challenge)
        return await session.ask(
            "captcha",
            "Paste a reCAPTCHA token for gmgn.ai",
            site_key=challenge.site_key,
            action=challenge.action,
        )

    async def code_provider(challenge: VerificationChallenge) -> str:
        label = {
            "email_code": "the code GMGN emailed you",
            "verify_email": "the code GMGN emailed you",
            "verify_otp": "your authenticator code",
            "sms_code": "the code GMGN texted you",
        }.get(challenge.verify_type, challenge.verify_type)
        message = f"Enter {label}"
        if challenge.previous_error:
            message += f" (previous attempt: {challenge.previous_error})"
        return await session.ask("code", message)

    auth = LoggingAuth(
        session,
        captcha_solver=captcha_solver,
        code_provider=code_provider,
        device_id=form.get("device_id") or None,
    )

    try:
        session.log("step", f"Impersonating {auth.impersonate} for the TLS fingerprint")
        tokens = await auth.login(form["email"], form["password"])
        session.state = "done"
        session.result = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "user_id": tokens.user_id,
            "expires_at": tokens.expires_at,
            "device_id": auth.device_id,
        }
        session.log("success", "Logged in")
    except asyncio.CancelledError:
        session.state = "error"
        session.error = "Cancelled"
        raise
    except Exception as e:
        session.state = "error"
        session.error = f"{type(e).__name__}: {e}"
        session.log("error", session.error)
    finally:
        await auth.close()


async def handle_index(request: web.Request) -> web.Response:
    return web.Response(text=PAGE, content_type="text/html")


async def handle_login(request: web.Request) -> web.Response:
    body = await request.json()
    if not body.get("email") or not body.get("password"):
        return web.json_response({"error": "Email and password are required"}, status=400)

    session = LoginSession()
    SESSIONS[session.id] = session
    session.log("step", f"Starting login for {body['email']}")
    session.task = asyncio.create_task(
        run_login(
            session,
            {
                "email": body["email"],
                "password": body["password"],
                "captcha_mode": body.get("captcha_mode", "manual"),
                "device_id": body.get("device_id", ""),
            },
        )
    )
    return web.json_response({"id": session.id})


async def handle_status(request: web.Request) -> web.Response:
    session = SESSIONS.get(request.query.get("id", ""))
    if session is None:
        return web.json_response({"error": "Unknown session"}, status=404)
    return web.json_response(session.snapshot())


async def handle_answer(request: web.Request) -> web.Response:
    body = await request.json()
    session = SESSIONS.get(body.get("id", ""))
    if session is None:
        return web.json_response({"error": "Unknown session"}, status=404)
    if not session.answer(body.get("value", "")):
        return web.json_response({"error": "Nothing is waiting for an answer"}, status=409)
    return web.json_response({"ok": True})


async def handle_cancel(request: web.Request) -> web.Response:
    body = await request.json()
    session = SESSIONS.get(body.get("id", ""))
    if session is not None and session.task and not session.task.done():
        session.task.cancel()
    return web.json_response({"ok": True})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/login", handle_login)
    app.router.add_get("/api/status", handle_status)
    app.router.add_post("/api/answer", handle_answer)
    app.router.add_post("/api/cancel", handle_cancel)
    return app


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GmGnAPI — Login Demo</title>
<style>
  :root{--bg:#0f172a;--card:#1e293b;--line:#334155;--text:#f8fafc;--muted:#94a3b8;
        --accent:#6366f1;--ok:#10b981;--warn:#f59e0b;--err:#ef4444;--radius:.75rem}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
       font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .wrap{max-width:820px;margin:0 auto;padding:2rem 1.25rem 4rem}
  h1{font-size:1.6rem;margin:0 0 .35rem}
  .sub{color:var(--muted);margin:0 0 1.75rem}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
        padding:1.5rem;margin-bottom:1.25rem}
  label{display:block;font-weight:600;margin:0 0 .35rem;font-size:.9rem}
  input,select{width:100%;padding:.65rem .75rem;background:var(--bg);color:var(--text);
       border:1px solid var(--line);border-radius:.5rem;font:inherit}
  input:focus,select:focus{outline:2px solid var(--accent);outline-offset:1px}
  .row{margin-bottom:1rem}
  .hint{color:var(--muted);font-size:.82rem;margin-top:.35rem}
  button{padding:.7rem 1.15rem;border:0;border-radius:.5rem;background:var(--accent);
         color:#fff;font:inherit;font-weight:600;cursor:pointer}
  button:disabled{opacity:.5;cursor:not-allowed}
  button.ghost{background:transparent;border:1px solid var(--line);color:var(--text)}
  .log{list-style:none;margin:0;padding:0}
  .log li{display:flex;gap:.65rem;padding:.5rem 0;border-bottom:1px solid var(--line);
          font-size:.9rem;align-items:flex-start}
  .log li:last-child{border-bottom:0}
  .tag{flex:none;width:5.5rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
       color:var(--muted);padding-top:.15rem}
  .kind-request .tag{color:var(--accent)}
  .kind-response .tag{color:var(--ok)}
  .kind-prompt .tag{color:var(--warn)}
  .kind-error .tag{color:var(--err)}
  .kind-success .tag{color:var(--ok)}
  pre{background:var(--bg);border:1px solid var(--line);border-radius:.5rem;padding:.6rem .75rem;
      margin:.4rem 0 0;overflow-x:auto;font-size:.8rem;color:var(--muted);
      white-space:pre-wrap;word-break:break-word}
  .token{word-break:break-all;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
         font-size:.8rem;background:var(--bg);border:1px solid var(--line);
         border-radius:.5rem;padding:.6rem .75rem;margin-top:.3rem}
  .banner{border-left:3px solid var(--warn);background:rgba(245,158,11,.08);
          padding:.85rem 1rem;border-radius:.4rem;font-size:.88rem;margin-bottom:1.5rem}
  .ok-banner{border-left-color:var(--ok);background:rgba(16,185,129,.08)}
  .err-banner{border-left-color:var(--err);background:rgba(239,68,68,.08)}
  .hidden{display:none}
  code{background:var(--bg);padding:.1rem .3rem;border-radius:.25rem;font-size:.85em}
</style>
</head>
<body>
<div class="wrap">
  <h1>GmGnAPI — Login Demo</h1>
  <p class="sub">Sign in to GMGN.ai with an email address and password, one protocol step at a time.</p>

  <div class="banner">
    Your password never leaves this machine — it is turned into an SRP proof locally.
    This server listens on localhost only and stores nothing.
  </div>

  <form id="form" class="card">
    <div class="row">
      <label for="email">GMGN email</label>
      <input id="email" type="email" autocomplete="username" required>
    </div>
    <div class="row">
      <label for="password">Password</label>
      <input id="password" type="password" autocomplete="current-password" required>
    </div>
    <div class="row">
      <label for="mode">reCAPTCHA token</label>
      <select id="mode">
        <option value="manual">Manual — I will paste a token</option>
        <option value="playwright">Automatic — use Playwright (must be installed)</option>
      </select>
      <p class="hint">GMGN gates the first step on reCAPTCHA v3, and its tokens are bound to
      gmgn.ai, so one has to come from a browser on that site.</p>
    </div>
    <div class="row">
      <label for="device">Device ID <span style="font-weight:400;color:var(--muted)">(optional)</span></label>
      <input id="device" type="text" placeholder="reuse to look like the same device each time">
    </div>
    <button id="submit" type="submit">Log in</button>
  </form>

  <div id="promptCard" class="card hidden">
    <div id="promptMsg" style="font-weight:600;margin-bottom:.75rem"></div>
    <div id="promptHelp" class="hint hidden" style="margin:0 0 .75rem">
      <span id="promptHelpText"></span>
      <pre id="promptSnippet"></pre>
      <button id="copySnippet" type="button" class="ghost"
              style="margin-top:.5rem;padding:.35rem .7rem;font-size:.8rem">Copy snippet</button>
    </div>
    <div class="row"><input id="promptInput" type="text" autocomplete="off"></div>
    <button id="promptSend" type="button">Submit</button>
  </div>

  <div id="resultCard" class="card hidden"></div>

  <div id="logCard" class="card hidden">
    <div style="font-weight:600;margin-bottom:.5rem">Protocol steps</div>
    <ul id="log" class="log"></ul>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let sessionId = null, polling = null, shown = 0;

// Reloading the page mid-login resumes the run instead of losing it.
const resume = new URLSearchParams(location.search).get('session');
if (resume) { sessionId = resume; attach(); }

function attach() {
  $('submit').disabled = true;
  $('logCard').classList.remove('hidden');
  polling = setInterval(poll, 500);
  poll();
}

$('form').addEventListener('submit', async e => {
  e.preventDefault();
  $('submit').disabled = true;
  $('log').innerHTML = ''; shown = 0;
  $('logCard').classList.remove('hidden');
  $('resultCard').classList.add('hidden');

  const res = await fetch('/api/login', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      email: $('email').value, password: $('password').value,
      captcha_mode: $('mode').value, device_id: $('device').value
    })
  });
  const data = await res.json();
  if (data.error) { finish('error', data.error); return; }
  sessionId = data.id;
  history.replaceState(null, '', '?session=' + sessionId);
  attach();
});

$('promptSend').addEventListener('click', async () => {
  const value = $('promptInput').value.trim();
  if (!value) return;
  $('promptInput').value = '';
  $('promptCard').classList.add('hidden');
  await fetch('/api/answer', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: sessionId, value})
  });
});

$('promptInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); $('promptSend').click(); }
});

async function poll() {
  const res = await fetch('/api/status?id=' + sessionId);
  if (!res.ok) return;
  const s = await res.json();

  for (const ev of s.events.slice(shown)) {
    const li = document.createElement('li');
    li.className = 'kind-' + ev.kind;
    const tag = document.createElement('span');
    tag.className = 'tag'; tag.textContent = ev.kind;
    const body = document.createElement('div');
    body.style.flex = '1';
    body.textContent = ev.message;
    if (ev.detail) {
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(ev.detail, null, 2);
      body.appendChild(pre);
    }
    li.append(tag, body);
    $('log').appendChild(li);
  }
  shown = s.events.length;

  if (s.prompt) showPrompt(s.prompt); else $('promptCard').classList.add('hidden');
  if (s.state === 'done') finish('done', s.result);
  else if (s.state === 'error') finish('error', s.error);
}

function showPrompt(p) {
  if (!$('promptCard').classList.contains('hidden')) return;
  $('promptCard').classList.remove('hidden');
  $('promptMsg').textContent = p.message;
  if (p.kind === 'captcha') {
    $('promptHelp').classList.remove('hidden');
    $('promptHelpText').innerHTML =
      'Open <a href="https://gmgn.ai/" target="_blank" style="color:var(--accent)">gmgn.ai</a>, ' +
      'then run this in the devtools console and paste the result. ' +
      'GMGN uses reCAPTCHA Enterprise and loads it on demand, so this snippet ' +
      'adds the script itself before asking for a token:';
    $('promptSnippet').textContent = snippetFor(p.site_key, p.action);
  } else {
    $('promptHelp').classList.add('hidden');
  }
  $('promptInput').focus();
}

function snippetFor(key, action) {
  return [
    '(async () => {',
    '  const k = "' + key + '";',
    '  const src = "https://www.recaptcha.net/recaptcha/enterprise.js?render=" + k;',
    '  try {',
    '    if (!window.grecaptcha || !window.grecaptcha.enterprise) {',
    '      await new Promise((ok, no) => {',
    '        const s = document.createElement("script");',
    '        s.src = src; s.onload = ok;',
    '        s.onerror = () => no(new Error("could not load " + src));',
    '        document.head.appendChild(s);',
    '      });',
    '    }',
    '    await new Promise(r => grecaptcha.enterprise.ready(r));',
    '    console.log(await grecaptcha.enterprise.execute(k, { action: "' + action + '" }));',
    '  } catch (e) {',
    '    console.error(e.message + " -- an ad/tracker blocker or your network is",',
    '      "most likely blocking recaptcha.net. Check the Network tab for the",',
    '      "enterprise.js request, retry with blockers off, or use the automatic",',
    '      "(Playwright) captcha option instead.");',
    '  }',
    '})()'
  ].join('\n');
}

$('copySnippet').addEventListener('click', () => {
  navigator.clipboard.writeText($('promptSnippet').textContent).then(() => {
    $('copySnippet').textContent = 'Copied';
    setTimeout(() => { $('copySnippet').textContent = 'Copy snippet'; }, 1500);
  });
});

function finish(state, payload) {
  clearInterval(polling);
  $('submit').disabled = false;
  $('promptCard').classList.add('hidden');
  const card = $('resultCard');
  card.classList.remove('hidden');
  if (state === 'error') {
    card.innerHTML = '<div class="banner err-banner" style="margin:0">' +
      '<strong>Login failed</strong><br>' + escapeHtml(String(payload)) + '</div>';
    return;
  }
  card.innerHTML =
    '<div class="banner ok-banner" style="margin:0 0 1rem"><strong>Logged in.</strong> ' +
    'Pass the access token to <code>GmGnClient(access_token=...)</code>.</div>' +
    field('User ID', payload.user_id) +
    field('Device ID', payload.device_id) +
    field('Access token', payload.access_token) +
    field('Refresh token', payload.refresh_token);
}

function field(label, value) {
  if (!value) return '';
  return '<div style="margin-bottom:.9rem"><label>' + label + '</label>' +
         '<div class="token">' + escapeHtml(String(value)) + '</div></div>';
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"GmGnAPI login demo running at {url}")
    print("Your password is turned into an SRP proof locally and never sent to GMGN.")
    if not args.no_browser:
        webbrowser.open(url)

    web.run_app(build_app(), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
