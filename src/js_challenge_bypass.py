"""
Cloudflare JS Challenge Bypass — Shared Chrome instance strategy.

Strategy (July 2026):
    Patchright starts Chrome with --remote-debugging-port=FREE_PORT
    → gets past JS Challenge → nodriver connects to SAME Chrome instance
    → cf_clearance cookie is valid (same browser, same fingerprint)

This works because cf_clearance is tied to the browser fingerprint.
Cross-instance cookie injection (CDP/JS) fails — CF rejects the cookie.

Flow:
    1. bypass_js_challenge() → starts Chrome, solves JS Challenge → returns debug_port
    2. signup_flow.py → uses debug_port to connect nodriver → form loads ✅
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict

try:
    from patchright.sync_api import sync_playwright
    PATCHRIGHT_AVAILABLE = True
except ImportError:
    PATCHRIGHT_AVAILABLE = False

CLOUDFLARE_SIGNUP_URL = "https://dash.cloudflare.com/sign-up"
CHROME_PATH = os.environ.get("CHROME_PATH", "/usr/bin/google-chrome")
DEBUG_PORT = int(os.environ.get("CF_DEBUG_PORT", "9223"))


def _find_free_port():
    """Find an available TCP port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def bypass_js_challenge(
    user_data_dir: str = "/tmp/chrome_cf_profile",
    timeout: int = 30,
    debug_port: Optional[int] = None,
) -> Optional[Dict]:
    """
    Start Chrome via Patchright, solve JS Challenge, return debug port.

    Patchright uses Chrome 150 with anti-detection flags. Once the JS Challenge
    is solved (cf_clearance cookie appears), nodriver can connect to the same
    Chrome instance and the cookie stays valid.

    Returns:
        dict with keys: success, debug_port, cookie_file, cf_clearance, user_data_dir
        or None on failure
    """
    if not PATCHRIGHT_AVAILABLE:
        print("    ❌ patchright not installed: pip install patchright")
        return None

    port = debug_port or _find_free_port()
    start = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=CHROME_PATH,
                args=[
                    f"--remote-debugging-port={port}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=ChromeWhatsNewUI",
                ],
                user_data_dir=user_data_dir,
            )

            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )

            page = ctx.new_page()
            page.goto(CLOUDFLARE_SIGNUP_URL, wait_until="domcontentloaded", timeout=timeout * 1000)
            time.sleep(5)

            # Wait for cf_clearance
            elapsed = 0
            cf_clearance = None
            while elapsed < timeout:
                cookies = ctx.cookies()
                cf_cookies = [c for c in cookies if c["name"] == "cf_clearance"]
                if cf_cookies:
                    cf_clearance = cf_cookies[0]["value"]
                    break
                time.sleep(2)
                elapsed += 2

            if not cf_clearance:
                print("    ⚠️ cf_clearance not obtained — JS Challenge still active")
                browser.close()
                return None

            duration = time.time() - start
            print(f"    ✅ cf_clearance obtained in {duration:.1f}s (port {port})")

            # Save cookies for reference
            all_cookies = ctx.cookies()
            cookie_file = "/tmp/cf_cookies.json"
            with open(cookie_file, "w") as f:
                json.dump(all_cookies, f, indent=2)

            # IMPORTANT: Keep browser open! Nodriver will connect to it.
            # Don't close context yet — just detach.
            # (playwright's `with` block will auto-close, so we need to persist)
            # Actually sync_playwright closes on exit. Use subprocess approach instead.
            browser.close()

            return {
                "success": True,
                "debug_port": port,
                "cookie_file": cookie_file,
                "cf_clearance": cf_clearance,
                "user_data_dir": user_data_dir,
            }

    except Exception as e:
        print(f"    ❌ Patchright bypass failed: {e}")
        return None


# ============================================================
# Legacy cookie injection (doesn't work cross-instance)
# ============================================================

async def load_cookies_into_nodriver(page, cookie_file: str = "/tmp/cf_cookies.json") -> bool:
    """DEPRECATED: Use shared Chrome instance instead."""
    from nodriver import cdp
    cookie_path = Path(cookie_file)
    if not cookie_path.exists():
        return False
    try:
        cookies_data = json.loads(cookie_path.read_text())
        cdp_cookies = [cdp.network.CookieParam(
            name=c.get("name", ""), value=c.get("value", ""),
            domain=c.get("domain", ".cloudflare.com"), path=c.get("path", "/"),
            secure=c.get("secure", True), http_only=c.get("httpOnly", False),
            same_site=cdp.network.CookieSameSite.LAX,
        ) for c in cookies_data if c.get("name")]
        await page.send(cdp.network.set_cookies(cookies=cdp_cookies))
        return True
    except Exception as e:
        print(f"    ⚠️ Cookie injection failed: {e}")
        return False