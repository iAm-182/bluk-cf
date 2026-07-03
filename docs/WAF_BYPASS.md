# Cloudflare WAF Bypass Techniques

## Overview

This document details every WAF bypass technique discovered during the development of this tool, including what worked, what failed, and why.

---

## 1. Turnstile CAPTCHA Bypass

### The Problem
Cloudflare Turnstile runs inside a **cross-origin sandboxed iframe**. Standard browser automation (Selenium, Playwright) cannot interact with it because:
- The iframe is sandboxed (`allow-scripts allow-same-origin` restricted)
- CDP `dispatchMouseEvent` events are blocked by the sandbox
- JavaScript cannot reach into the iframe due to cross-origin policy

### What Failed ❌

| Approach | Issue |
|----------|-------|
| Selenium `click()` on checkbox element | Element not interactable (cross-origin) |
| Playwright `frame.click()` | Frame locator fails (different origin) |
| JavaScript `iframe.contentDocument` | Cross-origin block |
| CDP `Input.dispatchMouseEvent` | Blocked by iframe sandbox |
| SeleniumBase UC Mode | Couldn't handle Turnstile |
| Patchright | Same as Playwright — cross-origin issue |
| SolveCaptcha | Balance $0, API-first approach |
| curl_cffi with cf_clearance | TLS fingerprint mismatch |

### What Worked ✅

**Approach: nodriver + OpenCV + OS-level mouse click**

```python
import nodriver as uc

# 1. Start browser with xvfb-run (virtual display)
browser = await uc.start(headless=False)

# 2. Take screenshot
await page.save_screenshot("/tmp/shot.png")

# 3. Find checkbox via OpenCV template matching
import cv2
img = cv2.imread("/tmp/shot.png")
template = cv2.imread("turnstile_checkbox.png")
result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)

# 4. OS-level mouse click (bypasses iframe sandbox!)
x = max_loc[0] + template.shape[1] // 2
y = max_loc[1] + template.shape[0] // 2
await page.mouse_click(x, y)  # This sends OS-level X11 click

# 5. Poll for token
token = await page.evaluate(
    'document.querySelector("input[name=cf-turnstile-response]")?.value'
)
```

### Why It Works

`nodriver.mouse_click(x, y)` sends a **mousePressed/mouseReleased event** via CDP that reaches the OS level (X11). Unlike JavaScript clicks, OS-level events bypass the iframe sandbox because they're processed by the display server, not the browser's JavaScript engine.

**Key requirement**: Must run under `xvfb-run` (virtual framebuffer) for headless environments.

---

## 2. Cloudflare WAF (cf_clearance)

### The Problem
After signing up, API calls to `/api/v4/user/tokens` are blocked by Cloudflare WAF with "Attention Required!" page. Even authenticated browser sessions get blocked.

### What Failed ❌

| Approach | Issue |
|----------|-------|
| XHR from browser (`page.evaluate(fetch())`) | WAF blocks API calls |
| Synchronous XMLHttpRequest | Same — WAF blocks |
| httpx with session cookies | WAF blocks (different fingerprint) |
| curl_cffi with cf_clearance cookie | TLS fingerprint mismatch |

### What Worked ✅

**Approach: Navigate to API Tokens page via Account URL**

Instead of calling the API directly, navigate the browser to:
```
https://dash.cloudflare.com/{account_id}/api-tokens/create
```

This works because:
1. The browser session is already authenticated (from signup)
2. The WAF allows **page navigation** (not XHR) from authenticated sessions
3. The token creation form loads client-side (React SPA)
4. Token creation happens via the UI, not direct API calls

### Boterdrop-Solver (cf_clearance)

For standalone WAF bypass, use [Boterdrop-Solver](https://github.com/najibyahya/Boterdrop-Solver):
- Uses **Camoufox** (fingerprint-proof Firefox)
- Gets `cf_clearance` cookie in ~7 seconds
- Works with VPS and residential proxies
- The cookie is **browser-fingerprint-bound** — only works within Camoufox

---

## 3. React Button Click Issues

### The Problem
Cloudflare dashboard is a React SPA. Some buttons don't respond to standard automation clicks.

### What Failed ❌

| Approach | Issue |
|----------|-------|
| `page.find("button").click()` | Clicks `<span>` inside button, not the button |
| `button.click()` via evaluate | React synthetic events not triggered |
| `dispatchEvent(new MouseEvent('click'))` | Same — React doesn't see it |
| `Object.getOwnPropertyDescriptor(HTMLButtonElement.prototype, 'click').call(btn)` | Works for native events but React delegation still ignores it |

### What Worked ✅

**Strategy: Use `page.evaluate` to click the actual `<button>` element**

```python
await page.evaluate('''
    (() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === 'Create Token') {
                b.scrollIntoView({block: 'center'});
                b.click();
                return 'clicked';
            }
        }
    })()
''')
```

**Why**: `b.click()` on the `<button>` element triggers the native click event, which React's root-level event delegation picks up. The key is clicking the `<button>` element directly, not a child `<span>`.

**Fallback**: CDP `Input.dispatchMouseEvent` with exact coordinates from `getBoundingClientRect()`.

---

## 4. Login/Re-authentication

### The Problem
After signup, the session is valid. But if the browser closes, re-login redirects to **Google OAuth** — email/password login is gone.

### Observation
- Fresh signup: Session established, can navigate to any dashboard page
- Browser close + reopen: Must login again → Google OAuth redirect
- No way to bypass Google OAuth with email/password alone

### Solution
**Grab all tokens immediately during the signup session.** Never close the browser until all tokens are created.

---

## 5. IP Rate Limiting

### Observed Limits

```
Server IP (70.x.x.x):  ~10-15 signups → blocked for 2-6 hours
Proxy IP (186.x.x.x):  ~3-4 signups → blocked for 1-3 hours
```

### Solution
- Rotate IPs (residential proxies preferred)
- Add 5-10 minute delays between signups
- Use `Boterdrop-Solver` with proxy for cf_clearance

---

## 6. Account API Tokens vs User API Tokens

### Key Discovery

There are **two types** of API tokens in Cloudflare:

| Type | URL | Notes |
|------|-----|-------|
| User API Tokens | `/profile/api-tokens` | Tied to user session, loses access if user deleted |
| **Account API Tokens** | `/{account_id}/api-tokens` | Tied to account, survives user changes, **recommended** |

**We use Account API Tokens** because:
1. Direct URL: `/{account_id}/api-tokens/create`
2. Permission template: "AI & Machine Learning" → "Workers AI"
3. Token persists even if user is removed

---

## Environment Requirements

```
OS:           Linux (Ubuntu 22.04+)
Display:      Xvfb (xvfb-run)
Browser:      Google Chrome (stable)
Python:       3.10+
Key packages: nodriver, opencv-python-headless, httpx
```

### Installation
```bash
apt install -y xvfb google-chrome-stable
pip install nodriver opencv-python-headless httpx
```

### Running
```bash
# MUST use xvfb-run for headless environments
xvfb-run --auto-servernum python main.py
```
