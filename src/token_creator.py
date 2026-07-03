"""
Account API Token Creator — Creates Cloudflare API tokens via dashboard UI.

Flow:
1. Navigate to /{account_id}/api-tokens/create
2. Fill token name
3. Select "AI & Machine Learning" permission category
4. Enable Workers AI (Read + Edit)
5. Click "Review token"
6. Click "Create Token"
7. Extract cfut_* token

Key Technical Notes:
- Uses Account API Tokens (NOT User API Tokens)
- URL: /{account_id}/api-tokens/create (auto-fills account filter)
- React buttons require proper click handling:
  - evaluate('button.click()') works for most buttons
  - Some buttons need CDP Input.dispatchMouseEvent with proper coordinates
- The "Create Token" button on the summary page sometimes needs JS click fallback
"""

import asyncio
import re
import time
from typing import Optional

import nodriver as uc


class TokenResult:
    """Result of a token creation attempt."""

    def __init__(
        self,
        success: bool,
        token: str = "",
        token_name: str = "",
        error: str = "",
    ):
        self.success = success
        self.token = token
        self.token_name = token_name
        self.error = error


async def create_token(
    page: uc.Tab,
    account_id: str,
    token_name: str = "workers-ai-auto",
    timeout: float = 120,
) -> TokenResult:
    """
    Create an Account API Token with Workers AI permissions.

    Args:
        page: nodriver Tab (already logged in)
        account_id: Cloudflare Account ID (32-char hex)
        token_name: Name for the token
        timeout: Max seconds for the whole flow

    Returns:
        TokenResult with cfut_* token on success
    """
    start = time.time()

    # Step 1: Navigate to token creation form
    create_url = f"https://dash.cloudflare.com/{account_id}/api-tokens/create"
    await page.get(create_url)
    await asyncio.sleep(15)

    # Verify we're on the creation page
    current_url = await page.evaluate("location.href")
    if "login" in current_url.lower():
        return TokenResult(False, error="Not logged in — session expired")

    # Step 2: Fill token name
    name_input = await page.select('input[aria-label*="Token name"]', timeout=10)
    if name_input:
        await name_input.click()
        await asyncio.sleep(0.5)
        await name_input.send_keys(token_name)
    else:
        # Fallback: use JS
        filled = await page.evaluate("""
            (() => {
                const inputs = document.querySelectorAll('input[type="text"]');
                for (const i of inputs) {
                    if (i.getAttribute('aria-label')?.includes('Token') || i.placeholder?.includes('name')) {
                        const nativeSet = Object.getOwnPropertyDescriptor(
                            HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeSet.call(i, '""" + token_name + """');
                        i.dispatchEvent(new Event('input', {bubbles: true}));
                        i.dispatchEvent(new Event('change', {bubbles: true}));
                        return true;
                    }
                }
                return false;
            })()
        """)
        if not filled:
            return TokenResult(False, token_name=token_name, error="Token name input not found")
    await asyncio.sleep(2)

    # Step 3: Click "AI & Machine Learning" category
    ai_clicked = await page.evaluate("""
        (() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim().includes('AI & Machine Learning')) {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return true;
                }
            }
            return false;
        })()
    """)
    if not ai_clicked:
        return TokenResult(False, token_name=token_name, error="AI & Machine Learning category not found")
    await asyncio.sleep(5)

    # Step 4: Select Workers AI permissions
    # Find and enable Workers AI Read + Edit checkboxes
    perms_selected = await page.evaluate("""
        (() => {
            const results = [];
            // Find the Workers AI section
            const allText = document.body.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (allText.nextNode()) {
                const text = allText.currentNode.textContent.trim();
                if (text === 'Workers AI' || text.startsWith('Workers AI ')) {
                    const parent = allText.currentNode.parentElement;
                    const container = parent?.closest('div, tr, li, section');
                    if (container) {
                        // Find checkboxes within this container
                        const checkboxes = container.querySelectorAll(
                            'input[type="checkbox"], [role="checkbox"]'
                        );
                        checkboxes.forEach(cb => {
                            if (cb.type === 'checkbox' && !cb.checked) {
                                cb.click();
                                results.push('checked: ' + (cb.name || cb.id || 'checkbox'));
                            } else if (cb.getAttribute('role') === 'checkbox') {
                                cb.click();
                                results.push('clicked role=checkbox');
                            }
                        });
                        if (results.length === 0) {
                            // Try clicking the container itself to expand/select
                            container.click();
                            results.push('clicked container');
                        }
                    }
                    break;
                }
            }
            return results.length > 0 ? results.join(', ') : 'not found';
        })()
    """)
    await asyncio.sleep(3)

    # Step 5: Click "Review token"
    review_clicked = await page.evaluate("""
        (() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                const text = b.textContent.trim();
                if (text === 'Review token' || text === 'Continue to summary') {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return text;
                }
            }
            return 'not found';
        })()
    """)
    if "not found" in str(review_clicked):
        return TokenResult(False, token_name=token_name, error="Review button not found")
    await asyncio.sleep(12)

    # Step 6: Click "Create Token" on summary page
    # Try multiple click strategies
    create_clicked = False

    # Strategy 1: JS click
    create_clicked = await page.evaluate("""
        (() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim() === 'Create Token' && !b.disabled) {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return true;
                }
            }
            return false;
        })()
    """)

    if not create_clicked:
        # Strategy 2: Find via nodriver
        try:
            btn = await page.find("Create Token", best_match=True, timeout=10)
            if btn:
                await btn.click()
                create_clicked = True
        except Exception:
            pass

    if not create_clicked:
        # Strategy 3: CDP mouse click at button coordinates
        coords = await page.evaluate("""
            (() => {
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    if (b.textContent.trim() === 'Create Token' && !b.disabled) {
                        const r = b.getBoundingClientRect();
                        return JSON.stringify({
                            x: Math.round(r.x + r.width/2),
                            y: Math.round(r.y + r.height/2)
                        });
                    }
                }
                return '{"x":0,"y":0}';
            })()
        """)
        import json
        try:
            c = json.loads(coords) if isinstance(coords, str) else {"x": 0, "y": 0}
            if c["x"] > 0:
                from nodriver.cdp.input_ import MouseButton
                await page.send(uc.cdp.input_.dispatch_mouse_event(
                    type_="mouseMoved", x=c["x"], y=c["y"]
                ))
                await asyncio.sleep(0.3)
                await page.send(uc.cdp.input_.dispatch_mouse_event(
                    type_="mousePressed", x=c["x"], y=c["y"],
                    button=MouseButton("left"), click_count=1
                ))
                await asyncio.sleep(0.1)
                await page.send(uc.cdp.input_.dispatch_mouse_event(
                    type_="mouseReleased", x=c["x"], y=c["y"],
                    button=MouseButton("left"), click_count=1
                ))
                create_clicked = True
        except Exception:
            pass

    if not create_clicked:
        return TokenResult(False, token_name=token_name, error="Create Token button not clickable")

    # Step 7: Wait for token to appear
    await asyncio.sleep(12)

    # Extract token
    token = await page.evaluate("""
        (() => {
            const body = document.body.innerText;
            const m = body.match(/cfut_[A-Za-z0-9_\\-]{20,}/);
            if (m) return m[0];

            // Check code/pre elements
            const codes = document.querySelectorAll('code, pre, input[readonly]');
            for (const c of codes) {
                const t = (c.value || c.textContent || '').trim();
                if (t.startsWith('cfut_') && t.length > 20) return t;
            }
            return '';
        })()
    """)

    if token and token.startswith("cfut_"):
        return TokenResult(True, token=token, token_name=token_name)

    # Check for errors
    elapsed = time.time() - start
    return TokenResult(
        False,
        token_name=token_name,
        error=f"Token not found after {elapsed:.0f}s",
    )
