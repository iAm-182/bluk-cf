"""
Turnstile Bypass — Solves Cloudflare Turnstile CAPTCHA using OpenCV + OS-level mouse clicks.

Technical Background:
    Cloudflare Turnstile runs inside a cross-origin sandboxed iframe.
    Standard CDP click events (dispatchMouseEvent) are blocked by the sandbox.
    The ONLY way to interact with the checkbox is via OS-level mouse clicks
    that operate at the display server level (X11/Wayland).

    The approach:
    1. Take a screenshot of the browser viewport
    2. Use OpenCV template matching to find the Turnstile checkbox
    3. Calculate the absolute screen coordinates
    4. Execute an OS-level mouse click via nodriver's mouse_click()
    5. Poll for the cf-turnstile-response hidden input to appear

    This runs under xvfb-run to provide a virtual display server.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# Turnstile checkbox template — a small crop of the unchecked box
# Save this as a reference image, or generate from screenshot
TEMPLATE_PATH = Path(__file__).parent / "templates" / "turnstile_checkbox.png"


async def find_turnstile_iframe(page) -> Optional[object]:
    """Find the Turnstile iframe on the page."""
    iframes = await page.query_selector_all("iframe")
    for iframe in iframes:
        src = await iframe.get_attribute("src") or ""
        if "challenges.cloudflare.com" in src:
            return iframe
    return None


def find_checkbox_position(screenshot_path: str, template_path: Optional[str] = None) -> Optional[tuple]:
    """
    Find Turnstile checkbox position in screenshot using OpenCV template matching.

    Args:
        screenshot_path: Path to the screenshot image
        template_path: Path to the checkbox template image.
                      If None, uses color-based detection.

    Returns:
        (x, y) center coordinates of the checkbox, or None if not found.
    """
    img = cv2.imread(screenshot_path)
    if img is None:
        return None

    if template_path and Path(template_path).exists():
        # Template matching approach
        template = cv2.imread(template_path)
        if template is None:
            return None

        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.7:  # Confidence threshold
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
    else:
        # Color-based detection: look for the Turnstile checkbox pattern
        # The unchecked checkbox has a distinctive grey/white pattern
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Turnstile checkbox is typically in the center-bottom area
        h, w = img.shape[:2]
        roi = img[h // 2 :, w // 4 : 3 * w // 4]  # Center-bottom quarter

        # Look for the small square checkbox pattern (light grey)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find small rectangular contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if 200 < area < 3000:  # Checkbox is small
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = cw / ch if ch > 0 else 0
                if 0.7 < aspect_ratio < 1.3:  # Roughly square
                    # Convert back to full image coordinates
                    full_x = x + w // 4
                    full_y = y + h // 2
                    return (full_x + cw // 2, full_y + ch // 2)

    return None


async def verify_cf(page, timeout: float = 60.0) -> str:
    """
    Solve Cloudflare Turnstile CAPTCHA on the current page.

    This is the core function that bypasses Turnstile:
    1. Scrolls to make Turnstile visible
    2. Takes screenshot
    3. Finds checkbox via OpenCV
    4. Clicks via OS-level mouse event
    5. Polls for token

    Args:
        page: nodriver Tab object
        timeout: Maximum seconds to wait for token

    Returns:
        The cf-turnstile-response token string

    Raises:
        TimeoutError: If token not received within timeout
        RuntimeError: If checkbox cannot be found
    """
    # Scroll down to make Turnstile visible
    await page.evaluate("window.scrollBy(0, 400)")
    await asyncio.sleep(2)

    # Check if Turnstile iframe exists
    iframe = await find_turnstile_iframe(page)
    if iframe is None:
        # Try clicking the checkbox frame first (it might be pre-solved)
        response = await page.evaluate(
            'document.querySelector("input[name=cf-turnstile-response]")?.value || ""'
        )
        if response:
            return response
        raise RuntimeError("Turnstile iframe not found on page")

    # Wait for Turnstile to fully load
    await asyncio.sleep(3)

    # Take screenshot for analysis
    screenshot_path = "/tmp/turnstile_screenshot.png"
    await page.save_screenshot(screenshot_path)

    # Find checkbox position
    pos = find_checkbox_position(screenshot_path, str(TEMPLATE_PATH) if TEMPLATE_PATH.exists() else None)

    if pos is None:
        # Fallback: click center of viewport (Turnstile is usually centered)
        viewport = await page.evaluate("({w: window.innerWidth, h: window.innerHeight})")
        pos = (viewport["w"] // 2, viewport["h"] // 2 + 100)

    # Get iframe position to calculate absolute coordinates
    iframe_rect = await iframe.evaluate(
        "() => { const r = this.getBoundingClientRect(); return {x: r.x, y: r.y}; }"
    )

    # Calculate absolute click coordinates
    abs_x = iframe_rect["x"] + pos[0]
    abs_y = iframe_rect["y"] + pos[1]

    # Execute OS-level mouse click
    # This is the KEY technique — bypasses iframe sandbox
    await page.mouse_click(abs_x, abs_y)

    # Poll for token
    start = time.time()
    while time.time() - start < timeout:
        await asyncio.sleep(2)
        response = await page.evaluate(
            'document.querySelector("input[name=cf-turnstile-response]")?.value || ""'
        )
        if response:
            return response

        # Check if still loading
        checkbox_status = await page.evaluate("""
            (() => {
                const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
                if (!iframe) return 'no_iframe';
                return 'waiting';
            })()
        """)
        if checkbox_status == "no_iframe":
            # Iframe removed = challenge solved, check again
            response = await page.evaluate(
                'document.querySelector("input[name=cf-turnstile-response]")?.value || ""'
            )
            if response:
                return response

    raise TimeoutError(f"Turnstile not solved within {timeout}s")


async def is_turnstile_present(page) -> bool:
    """Check if Turnstile CAPTCHA is present on the page."""
    return await page.evaluate("""
        (() => {
            const iframes = document.querySelectorAll('iframe');
            for (const f of iframes) {
                if (f.src && f.src.includes('challenges.cloudflare.com')) return true;
            }
            const input = document.querySelector('input[name="cf-turnstile-response"]');
            return !!input;
        })()
    """)
