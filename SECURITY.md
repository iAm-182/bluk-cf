# Security Policy

## Intended Use

This project is for authorized automation, testing, and research. Only use it on Cloudflare accounts, domains, mail infrastructure, and 9Router instances that you own or have explicit permission to manage.

## Secret Handling

The following files/data are sensitive and must not be committed or shared publicly:

- `config.json` — live mail API/proxy configuration
- `results.json` — generated passwords, mailbox JWTs, Account IDs, API tokens
- `*.txt` exports containing full `cfut_` API tokens
- Proxy credentials
- GitHub Personal Access Tokens
- Cloudflare API tokens

The repository `.gitignore` excludes common local secret files, but you should still run a scan before pushing:

```bash
git status --ignored --short
git ls-files -z | xargs -0 grep -InE 'ghp_|cfut_|proxy|password|api[_-]?key|token|jwt' || true
```

Expected false positives include placeholder strings such as `cfut_xxx` in documentation and variable names in source code.

## Token Rotation

If a token is exposed:

1. Revoke the Cloudflare API token from the Cloudflare dashboard.
2. Revoke/rotate any GitHub PAT from GitHub Developer Settings.
3. Rotate proxy credentials if they were exposed.
4. Delete local TXT exports that contain full tokens.
5. Re-run the bot to generate fresh credentials if needed.

## Operational Safety

- Use residential/clean proxies where authorized; datacenter/VPS IPs are often rate-limited.
- Start with small runs (`--accounts 1`) before bulk runs.
- Treat `--workers > 1` as advanced; parallel signup can increase rate-limit risk.
- Keep delays between accounts to reduce transient browser/proxy failures.
- Do not publish real output logs containing generated credentials.

## Reporting Security Issues

If you find a vulnerability in this repository, open a private advisory or contact the maintainer directly. Do not publish working secrets, tokens, or third-party account data in public issues.
