"""
Turnstile Bypass — Solves Cloudflare Turnstile using nodriver's built-in verify_cf().

The ONLY approach that works (July 2026). No OpenCV, no xdotool, no template matching.
Just call: await page.verify_cf()

CF Challenge Types:
- JS Challenge ("Just a moment...") → handled by js_challenge_bypass.py (Patchright)
- Turnstile widget (iframe-based) → handled by verify_cf()
- Managed Challenge ("Let us know you are human") → REQUIRES HUMAN CLICK (phone-in-the-loop)
"""

import asyncio
from typing import Optional


async def verify_cf(page, timeout: float = 30.0) -> str:
    """
    Solve Turnstile using nodriver's built-in method.

    Works for standard Turnstile (iframe-based). Does NOT work for:
    - JS Challenge interstitial (handled by js_challenge_bypass)
    - Managed Challenge "Let us know you are human" (requires human)
    """
    result = await page.verify_cf()
    return result or ""


async def is_turnstile_present(page) -> bool:
    """Check if any CF challenge is present on the page."""
    return bool(await page.evaluate('''(() => {
        if (document.querySelector('input[name="cf_challenge_response"]')) return true;
        if (document.querySelector('input[name="cf-turnstile-response"]')) return true;
        const iframes = document.querySelectorAll("iframe");
        for (const f of iframes) {
            if (f.src && f.src.includes("challenges.cloudflare.com")) return true;
        }
        const body = document.body.innerText;
        if (body.includes("Verify you are human") || body.includes("Let us know you are human")) return true;
        return false;
    })()'''))


async def is_managed_challenge(page) -> bool:
    """
    Check if the page has a managed challenge that requires human click.
    Returns True if phone-in-the-loop is needed.
    """
    return bool(await page.evaluate('''(() => {
        const body = document.body.innerText || "";
        return body.includes("Let us know you are human") || body.includes("Verify you are human");
    })()'''))


async def is_rate_limited(page) -> bool:
    """
    Check if the current IP is rate-limited by Cloudflare.
    """
    return bool(await page.evaluate('''(() => {
        const body = document.body.innerText || "";
        return body.includes("unable to sign up") ||
               body.includes("too many sign ups") ||
               body.includes("rate limited") ||
               body.includes("try again later");
    })()'''))
