# ☁️ Cloudflare Auto Signup

> Automated Cloudflare account creation with **Workers AI API token generation** — bypasses Turnstile CAPTCHA and Cloudflare WAF using headless browser automation.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" />
  <img src="https://img.shields.io/badge/platform-linux-lightgrey.svg" />
</p>

## 🎯 What This Tool Does

This tool automates the **entire lifecycle** of creating Cloudflare accounts with Workers AI access:

1. **📧 Generate temp email** — via disposable mail API (any mailserver with compatible endpoint)
2. **🔐 Sign up Cloudflare account** — fill form, solve Turnstile CAPTCHA, submit
3. **🔑 Create Account API Token** — with Workers AI (Read + Edit) permissions
4. **✅ Validate token** — verify against Workers AI REST API
5. **💾 Save to JSON/TXT** — email, password, account_id, api_token, validation status
6. **📊 Live dashboard** — optional Rich real-time worker progress/logs/statistics
7. **🧩 9Router export/add** — export valid keys to 9Router-friendly TXT and bulk-add them locally

**Output example:**
```json
{
  "email": "cf12345@yourdomain.com",
  "password": "Cf*Ab3xK9$mQ",
  "account_id": "a1b2c3d4e5f6789012345678abcdef01",
  "api_token": "cfut_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "token_valid": true,
  "workers_ai_models": 60,
  "token_name": "workers-ai-auto",
  "status": "full",
  "created_at": "2026-07-03T23:00:00+00:00",
  "proxy_used": "direct"
}
```

---

## 🛠️ Tools & Technologies

| Tool | Version | Purpose |
|------|---------|---------|
| [**nodriver**](https://github.com/ultrafunkamsterdam/nodriver) | ≥0.38 | Undetected Chrome automation (Selenium alternative, no chromedriver needed) |
| [**OpenCV**](https://opencv.org/) | ≥4.8 | Template matching to find Turnstile checkbox in screenshots |
| [**httpx**](https://github.com/encode/httpx) | ≥0.25 | Async HTTP client for email API and token validation |
| [**Pillow**](https://python-pillow.org/) | ≥10.0 | Image processing support |
| [**Google Chrome**](https://www.google.com/chrome/) | Stable | Browser engine for automation |
| [**Xvfb**](https://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml) | — | Virtual framebuffer for headless display |

### How Turnstile Handling Works

This project uses nodriver's built-in Cloudflare helper:

```python
await page.verify_cf()
```

The helper drives the Cloudflare/Turnstile challenge from the browser session and avoids brittle image-template or OS-click logic. Keep the same authenticated `page` object after signup; opening a fresh tab/browser can lose dashboard session state.

**Requires:** `xvfb-run` to provide a virtual display server in VPS/headless environments. When running as root, browser startup uses `sandbox=False`.

---

## 📋 Requirements

- **OS:** Linux (Ubuntu 22.04+ recommended)
- **Display:** Xvfb (`xvfb-run` command)
- **Browser:** Google Chrome (stable channel)
- **Python:** 3.10+
- **RAM:** ≥512MB per browser instance
- **Disk:** ≥2GB (Chrome + dependencies)

---

## 🚀 Quick Start

### 1. Setup (VPS)

```bash
# Clone the repo
git clone https://github.com/iAm-182/bluk-cf.git
cd bluk-cf

# Run setup script
chmod +x scripts/setup.sh
sudo ./scripts/setup.sh

# Edit config
cp config.example.json config.json
nano config.json
```

### 2. Configuration

Edit `config.json`:

```json
{
    "mail_api": "https://your-mail-api.example.com/api/new_address",
    "mail_domains": ["yourdomain.com", "anotherdomain.com"],
    "proxy": null,
    "headless": false,
    "max_accounts": 10,
    "delay_between_accounts": 300,
    "retry_attempts": 3,
    "token_name": "workers-ai-auto",
    "token_permissions": ["Workers AI"],
    "token_expiry": "no-expiration",
    "output_file": "results.json"
}
```

| Field | Description |
|-------|-------------|
| `mail_api` | Temp email API endpoint (POST, returns `address` + `jwt`) |
| `mail_domains` | Available email domains (randomly selected) |
| `proxy` | HTTP proxy URL (`http://user:pass@host:port`) or `null` |
| `headless` | Run Chrome without GUI (requires `xvfb-run`) |
| `max_accounts` | Max accounts per run |
| `delay_between_accounts` | Seconds to wait between signups |
| `retry_attempts` | Retries per account on failure |
| `token_name` | Name for the API token |
| `output_file` | JSON output path |

### 3. Run

```bash
# Create 1 account
xvfb-run --auto-servernum python main.py

# Create 5 accounts with proxy
xvfb-run --auto-servernum python main.py -n 5 -p "http://user:pass@host:port"

# Create 10 accounts, custom output + 9Router TXT export
xvfb-run --auto-servernum python main.py -n 10 -o my_accounts.json --export-txt keys.txt

# Run with 2 concurrent workers and Rich live dashboard
xvfb-run --auto-servernum python main.py -n 10 --workers 2 -p "http://user:pass@host:port"

# Export existing valid results for 9Router
python scripts/export_9router_txt.py -i results.json -o keys.txt

# Bulk-add exported keys into local 9Router (localhost:20128)
python scripts/add_to_9router.py -i keys.txt

# Validate an existing token
python main.py --validate-only --token cfut_xxx --account-id abc123

# Batch run with proxy rotation
./scripts/batch_runner.sh 20 proxies.txt
```

---

## 📖 CLI Reference

```
python main.py [OPTIONS]

Options:
  -n, --accounts N          Number of accounts to create (default: 1)
  -c, --config FILE         Config file path (default: config.json)
  -p, --proxy URL           HTTP proxy URL
  -o, --output FILE         Output JSON file (default: results.json)
  -d, --delay SECS          Delay between accounts (default: 300)
  --headless                Run in headless mode
  --retry N                 Retry attempts per account (default: 3)
  -w, --workers N           Concurrent account workers (default: 1)
  --no-dashboard            Disable Rich live dashboard
  --export-txt FILE         Export valid keys to 9Router-friendly TXT
  --validate-only           Only validate an existing token
  --token TOKEN             Token to validate (with --validate-only)
  --account-id ID           Account ID for validation
```

---

## 📊 Scalability

### Can it create 1000+ accounts?

**Yes, but with caveats:**

| Bottleneck | Limit | Solution |
|------------|-------|----------|
| IP rate limit | ~10-15 signups per IP | Rotate residential proxies |
| Memory per browser | ~200-300MB | Run sequentially, not parallel |
| Time per account | ~2-3 minutes | Expected for 1000 accounts: ~33-50 hours |
| Proxy cost | Residential ~$5-15/GB | Budget: ~$50-100 for 1000 accounts |
| Token creation | No observed rate limit | Not a bottleneck |

### Recommended approach for 1000+ accounts

```bash
# 1. Prepare proxy list (residential, rotating)
# Format: one proxy per line
# http://user:pass@host:port

# 2. Use batch runner with proxy rotation
./scripts/batch_runner.sh 1000 proxies.txt

# 3. Or schedule via cron (recommended)
# Run 50 accounts every 6 hours
xvfb-run --auto-servernum python main.py -n 50 -p "http://user:pass@host:port" -d 600
```

### Architecture for high throughput

```
┌─────────────────────────────────────────────┐
│           Scheduler (cron/systemd)          │
│  Runs every 6h, creates 50 accounts/run     │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    Proxy 1    Proxy 2    Proxy 3
        │          │          │
        ▼          ▼          ▼
    Browser    Browser    Browser
        │          │          │
        └──────────┼──────────┘
                   ▼
            results.json (append)
```

**Key optimizations:**
1. **Sequential, not parallel** — one browser at a time (memory efficient)
2. **Proxy rotation** — different IP per account
3. **Scheduled runs** — spread over hours to avoid rate limits
4. **Append mode** — results.json accumulates across runs
5. **Retry logic** — auto-retry on transient failures

---

## 📁 Project Structure

```
cloudflare-auto-signup/
├── main.py                      # Entry point — orchestrator
├── config.example.json          # Config template (copy to config.json)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── LICENSE                      # MIT License
├── .gitignore                   # Git ignore rules
├── src/
│   ├── __init__.py              # Package init
│   ├── email_generator.py       # Temp email API client
│   ├── turnstile_bypass.py      # OpenCV-based Turnstile solver
│   ├── signup_flow.py           # Signup automation (form + Turnstile)
│   ├── token_creator.py         # Account API Token creation
│   ├── token_validator.py       # Token validation via REST API
│   └── utils.py                 # Shared utilities
├── scripts/
│   ├── setup.sh                 # VPS setup (Chrome, Xvfb, deps)
│   └── batch_runner.sh          # Batch run with proxy rotation
├── docs/
│   ├── RATE_LIMITS.md           # Rate limit analysis & recovery times
│   ├── WAF_BYPASS.md            # WAF bypass techniques (detailed)
│   └── ARCHITECTURE.md          # Technical architecture diagram
└── tests/
    └── test_token_validator.py  # Validation tests
```

## ⚠️ Legal Disclaimer

This tool is provided for **educational and security research purposes only**. Users are responsible for complying with Cloudflare's Terms of Service and all applicable laws. The authors are not responsible for any misuse.

---

## 🙏 Acknowledgments

- [Auto-FreeCF](https://github.com/mocasus/Auto-FreeCF) — Original baseline concept and automation approach
- [nodriver](https://github.com/ultrafunkamsterdam/nodriver) — Undetected Chrome automation
- [Boterdrop-Solver](https://github.com/najibyahya/Boterdrop-Solver) — Camoufox CAPTCHA solver (cf_clearance)
- [chatgpt-auto-signup](https://github.com/SGAHSCAJASCJ/chatgpt-auto-signup) — verify_cf() implementation reference
- [OpenCV](https://opencv.org/) — Computer vision for template matching

---

## 🐛 Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Config not found: config.json` | Config file missing | `cp config.example.json config.json` then edit it |
| `ConnectionRefusedError` for mail API | Mail server is down or wrong URL | Check `mail_api` in config, verify server is running |
| `Email failed: 422` / `400` | Domain not supported by mail API | Make sure your mail API has the domains in `mail_domains` |
| `You are unable to sign up at this time` | **Rate limited** — too many signups from same IP | Wait 2-6 hours, or use a proxy (`-p http://user:pass@host:port`) |
| `Turnstile failed` / challenge timeout | Proxy/IP blocked or nodriver helper could not complete | Rotate to a fresh residential proxy, then retry |
| `email_not_verified` | Cloudflare blocks token creation until email verification | Ensure your temp-mail API exposes `/parsed_mails` and returns the Cloudflare verification email |
| `Token creation failed` | Email verification/API call failed or dashboard session expired | Check logs for `email_verify_error`, confirm `mail_api` and proxy health |
| `cf_clearance cookie is TLS-fingerprint-bound` | Using `curl_cffi` outside Camoufox | This tool uses nodriver (full browser), not `curl_cffi` — this shouldn't occur |
| `Xvfb not found` | Missing virtual display | `apt install -y xvfb` then run with `xvfb-run` |
| `nodriver not found` | Python dependency missing | `pip install -r requirements.txt` |
| `Chrome not found` | Google Chrome not installed | `apt install -y google-chrome-stable` or install from [Google](https://www.google.com/chrome/) |
| `PermissionError: DISPLAY` | Running headless env without xvfb | Use `xvfb-run --auto-servernum python main.py` |

### Token Validation Fails (`token_valid: false`)

This usually means:
1. Token was created but permissions weren't applied — re-run and check dashboard manually
2. Rate limit hit during token creation — account exists but token is incomplete
3. Token expired immediately — Cloudflare sometimes invalidates auto-created tokens

**Workaround:** Even if validation fails, the `account_id` + `api_token` are still saved in `results.json`. You can manually verify at `https://dash.cloudflare.com/{account_id}/api-tokens`.

### Browser Won't Start

```bash
# Check if Chrome is installed
google-chrome --version

# Check if Xvfb is installed
which xvfb-run

# Manual test — should open a browser window (or blank screen if no display)
xvfb-run --auto-servernum python -c "import nodriver as uc; import asyncio; asyncio.run(uc.start())"
```

---

## 🔄 End-to-End Guide: From Zero to Running

### Step 1: Prepare VPS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y xvfb google-chrome-stable python3.10 python3-pip git

# Clone
git clone https://github.com/iAm-182/bluk-cf.git
cd bluk-cf

# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Set Up Mail API

You need a **temporary email API** that:
- Accepts `POST /api/new_address` with `{"domain": "yourdomain.com"}`
- Returns `{"address": "user@yourdomain.com", "jwt": "..."}`

Options:
- [**Self-hosted temp mail**](https://github.com/nickspaargaren/no-google) — Self-hosted disposable mail server (recommended)
- [**Mailinator API**](https://www.mailinator.com/) — Commercial, limited free tier
- **Any disposable mail server** — As long as it matches the API format

Configure in `config.json`:
```json
{
    "mail_api": "https://your-mail-api.example.com/api/new_address",
    "mail_domains": ["yourdomain.com"]
}
```

### Step 3: Configure

```bash
cp config.example.json config.json
nano config.json  # Edit mail_api, mail_domains, proxy (if needed)
```

### Step 4: Run

```bash
# Single account (recommended first run)
xvfb-run --auto-servernum python main.py

# Multiple accounts
xvfb-run --auto-servernum python main.py -n 5

# With proxy
xvfb-run --auto-servernum python main.py -n 5 -p "http://user:pass@host:port"

# Custom output file
xvfb-run --auto-servernum python main.py -n 10 -o my_accounts.json

# Export valid keys for 9Router while running
xvfb-run --auto-servernum python main.py -n 10 --export-txt keys.txt

# Add exported keys to local 9Router
python scripts/add_to_9router.py -i keys.txt
```

### Step 5: Check Results

```bash
# View results
cat results.json | python -m json.tool

# Or use jq for filtering
cat results.json | jq '.[] | {email, account_id, api_token, status}'
```

### Step 6: Use the API Token

Each account produces a token like:
```json
{
  "account_id": "a1b2c3d4...",
  "api_token": "cfut_xxxxxxxxxxxxx"
}
```

Use it with Cloudflare Workers AI:
```bash
curl "https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/models/search" \
  -H "Authorization: Bearer cfut_XXXXXXXX"
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
