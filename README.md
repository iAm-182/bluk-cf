<div align="center">

# 🚀 Auto-FreeCF

<img src="assets/logo.svg" alt="Auto-FreeCF Logo" width="200"/>

### Cloudflare Workers AI Account ID & Token Auto-Grabber

<img alt="Version" src="https://img.shields.io/badge/version-v4.0.1-5865F2?style=flat-square">
<img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square">
<img alt="Node" src="https://img.shields.io/badge/node-%3E=18.0.0-339933?style=flat-square">
<img alt="Python" src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square">
<img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square">

**Fully automated Cloudflare account grabber with advanced stealth scripts**

[Installation](#-installation) • [Usage](#-usage) • [Features](#-features) • [Documentation](#-documentation)

</div>

---

## ⚡ Quick Start

```bash
npm install -g auto-freecf
moycf
```

---

## ✨ Features

- 🤖 **Full Automation** — Login, grab Account ID, create API Token, all automatic
- 🛡️ **Stealth Mode** — Bypass Cloudflare bot detection with advanced stealth scripts
- 👻 **Headless by Default** — Runs completely in background, no browser window opens
- 🌐 **Residential Proxy** — Optional proxy configuration for better success rate
- 📝 **Single & Bulk** — Input single email:pass atau bulk dari file
- 📦 **Auto Setup** — Automatic dependency installation with live timer
- 💾 **Export Results** — Save to TXT format with account_id:worker_token
- 🔐 **Google OAuth** — Support login via Google Sign-In (fully automated)

---

## 📁 Project Structure

```
Auto-FreeCF/
├── src/                    # Core source code (login flow)
│   ├── __init__.py
│   ├── browser_bot.py      # Main browser automation logic
│   ├── turnstile_solver.py # Turnstile challenge solver
│   └── utils.py            # Utility functions
├── signup_from_scratch/    # 🔥 NEW: Auto signup from zero
│   ├── main.py             # Orchestrator
│   ├── src/
│   │   ├── signup_flow.py      # CF signup with Turnstile
│   │   ├── js_challenge_bypass.py  # JS Challenge bypass (stealth flags)
│   │   ├── email_verifier.py   # Email verification
│   │   ├── email_generator.py  # Temp-mail creation
│   │   ├── token_creator.py    # API token creation
│   │   ├── token_validator.py  # Token validation
│   │   ├── turnstile_bypass.py # Advanced Turnstile solver
│   │   └── utils.py
│   └── config.example.json
├── mail-adapter/           # Temp-mail bridge (Supabase API)
│   ├── adapter.py
│   └── config.example.json
├── deploy-browserfarm.sh   # VPS deployment script
├── cli.js                  # CLI entry point
├── terminal_ui.py          # Terminal UI
├── web_ui.py               # Web UI
├── browser_bot.py          # Backward compatibility wrapper
└── package.json            # NPM package config
```

## 🚀 Installation

```bash
npm install -g auto-freecf
```

## 💻 Usage

### CLI Mode

```bash
# Single account (email:password)
moycf email@example.com:password123

# Bulk accounts from file
moycf accounts.txt

# With proxy
moycf accounts.txt --proxy config/proxy.json

# Google OAuth login
moycf google_email:password --login-method google
```

### Interactive Mode

```bash
moycf
```

Then choose:
1. Single account (email:password)
2. Single account (Google OAuth)
3. Bulk accounts (from file)

### Web UI

```bash
python web_ui.py
```

Open http://localhost:8080 in your browser.

### 🔥 Signup From Scratch (NEW)

Create Cloudflare accounts from zero — no existing email needed:

```bash
# 1. Setup mail adapter (once)
cd mail-adapter
cp config.example.json config.json
python3 adapter.py &

# 2. Create accounts
cd signup_from_scratch
cp config.example.json config.json
# Edit config.json → set "mail_api" to "http://localhost:9877/new_address"
# Default domains: moymoy.me, moyqris.me, kintole.com, gmilio.web.id

# Single account
DISPLAY=:99 python3 main.py

# Bulk (5 accounts, 60s delay)
DISPLAY=:99 python3 main.py -n 5 -d 60
```

**Full pipeline:**
1. Temp-mail creation → 2. CF JS Challenge bypass (Chrome stealth flags) → 3. CF Signup (Turnstile) → 4. Email verify → 5. API token → 6. Validate

**CF Protection Layers Handled:**
- ✅ JS Challenge ("Just a moment…") — auto-bypass via Chrome stealth flags (`disable-blink-features` + Chrome 150 UA)
- ✅ Turnstile widget (iframe) — nodriver verify_cf()
- ⚠️ Managed Challenge ("Let us know you are human") — detected, requires phone-in-the-loop
- ⚠️ Rate Limit (429) — detected, try residential proxy

**Output format:** `account_id:workers_ai_token` in `results.json`

### VPS Deployment

```bash
./deploy-browserfarm.sh
```

## 🔧 Development

### Project Structure

- **src/browser_bot.py**: Main CFAutoGrabber class with login, token creation logic
- **src/turnstile_solver.py**: Turnstile challenge solving (isolated page approach)
- **src/utils.py**: Helper functions (load_accounts, load_proxy_config, save_results)
- **signup_from_scratch/**: Standalone signup pipeline (no existing email needed)
- **mail-adapter/**: Temp-mail API bridge for signup pipeline
- **browser_bot.py**: Backward compatibility wrapper for existing scripts

### Running Tests

```bash
cd tests
python test_login.py
```

## 🔒 Security

See [SECURITY.md](SECURITY.md) for details on reporting vulnerabilities and security best practices.

---

## 📜 Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for our community guidelines and standards.

---

## 📝 License

MIT
