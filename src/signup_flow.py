"""
Cloudflare Signup Flow — Automated account creation via headless browser.

CF Protection Layers (July 2026):
  L1: JS Challenge  → handled by stealth browser args (nodriver)
  L2: Turnstile      → handled by verify_cf()
  L3: Managed Challenge → requires human click (detected, logged)
  L4: Rate Limit     → detected, requires IP rotation

IMPORTANT: L1 bypass requires these browser args:
  --disable-blink-features=AutomationControlled
  --disable-features=ChromeWhatsNewUI
  --user-agent=Chrome 150 UA
Without them, CF shows "Just a moment..." interstitial.
"""

import asyncio
import re
from typing import Optional

import nodriver as uc

from .turnstile_bypass import verify_cf, is_turnstile_present, is_managed_challenge, is_rate_limited


CLOUDFLARE_SIGNUP_URL = "https://dash.cloudflare.com/sign-up"

# Required browser flags for JS Challenge bypass (July 2026)
STEALTH_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=ChromeWhatsNewUI",
    "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
]


class SignupResult:
    """Result of a signup attempt."""

    def __init__(
        self,
        success: bool,
        email: str = "",
        password: str = "",
        account_id: str = "",
        error: str = "",
        page_url: str = "",
    ):
        self.success = success
        self.email = email
        self.password = password
        self.account_id = account_id
        self.error = error
        self.page_url = page_url

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "email": self.email,
            "password": self.password,
            "account_id": self.account_id,
            "error": self.error,
        }


async def start_stealth_browser(headless: bool = True) -> tuple:
    """Start nodriver with anti-detection flags that bypass CF JS Challenge."""
    browser = await uc.start(
        headless=headless,
        browser_args=STEALTH_BROWSER_ARGS,
    )
    return browser


async def signup(
    page: uc.Tab,
    email: str,
    password: str,
    max_wait: int = 30,
    retry_turnstile: bool = True,
) -> SignupResult:
    """
    Execute the Cloudflare signup flow.

    Args:
        page: nodriver Tab (already navigated or will navigate)
        email: Email address for the new account
        password: Password for the new account
        max_wait: Max seconds to wait for redirect after submit
        retry_turnstile: Whether to retry Turnstile if first attempt fails

    Returns:
        SignupResult with account_id on success
    """
    # Navigate to signup
    await page.get(CLOUDFLARE_SIGNUP_URL)
    await asyncio.sleep(8)

    # ---- Phase 0: Verify page loaded (JS Challenge bypassed by stealth flags) ----
    title = await page.evaluate("document.title")
    if "Just a moment" in title:
        print("    ⚠️ JS Challenge still active — stealth flags may need update")
        return SignupResult(False, email=email, error="JS Challenge not bypassed")

    # Check rate limit before proceeding
    if await is_rate_limited(page):
        return SignupResult(False, email=email,
                          error="Rate limited: IP flagged, try residential proxy")

    # Fill email
    email_input = await page.select('input[name="email"]', timeout=15)
    if not email_input:
        await asyncio.sleep(8)
        email_input = await page.select('input[name="email"]', timeout=10)
    if not email_input:
        return SignupResult(False, email=email, error="Email input not found")
    await email_input.click()
    await asyncio.sleep(0.5)
    await email_input.send_keys(email)
    await asyncio.sleep(1)

    # Fill password
    pw_input = await page.select('input[name="password"]', timeout=5)
    if not pw_input:
        return SignupResult(False, email=email, error="Password input not found")
    await pw_input.click()
    await asyncio.sleep(0.5)
    await pw_input.send_keys(password)
    await asyncio.sleep(2)

    # Scroll to make Turnstile visible
    await page.evaluate("window.scrollBy(0, 400)")
    await asyncio.sleep(3)

    # Solve Turnstile
    turnstile_present = await is_turnstile_present(page)
    if turnstile_present:
        try:
            token = await verify_cf(page, timeout=60)
            if token:
                print(f"    ✅ Turnstile solved: {token[:20]}...")
            else:
                print("    ⚠️ verify_cf returned empty")
        except (TimeoutError, RuntimeError) as e:
            if retry_turnstile:
                await asyncio.sleep(5)
                try:
                    token = await verify_cf(page, timeout=60)
                    print(f"    ✅ Turnstile solved (retry): {token[:20]}...")
                except Exception as e2:
                    # Check if it's actually a managed challenge
                    if await is_managed_challenge(page):
                        return SignupResult(False, email=email,
                            error="Managed challenge: requires human intervention")
                    return SignupResult(False, email=email, error=f"Turnstile failed: {e2}")
            else:
                return SignupResult(False, email=email, error=f"Turnstile failed: {e}")
    await asyncio.sleep(5)

    # Submit form
    submit_btn = await page.select('button[type="submit"]', timeout=5)
    if not submit_btn:
        return SignupResult(False, email=email, error="Submit button not found")
    await submit_btn.scroll_into_view()
    await asyncio.sleep(1)
    await submit_btn.click()

    # Wait for redirect
    for _ in range(max_wait):
        await asyncio.sleep(1)
        url = await page.evaluate("location.href")
        if "/sign-up" not in url:
            break
    await asyncio.sleep(10)

    # Extract Account ID from URL
    url = await page.evaluate("location.href")
    match = re.search(r"/([a-f0-9]{32})", url)
    if match:
        account_id = match.group(1)
        return SignupResult(
            True, email=email, password=password,
            account_id=account_id, page_url=url,
        )

    # Check for error messages
    error_msgs = await page.evaluate("""
        Array.from(document.querySelectorAll('p, [role="alert"]'))
            .map(e => e.textContent.trim())
            .filter(t => t.includes('unable') || t.includes('limit') || t.includes('Incorrect'))
    """)
    error = error_msgs if error_msgs else f"Redirect failed: {url[:80]}"

    return SignupResult(False, email=email, error=str(error))