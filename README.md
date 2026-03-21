# PixAI Daily Claimer

Automatically claims the free 10,000 daily points on [PixAI.art](https://pixai.art) for multiple accounts. Runs on Windows startup, claims any account that hasn't been claimed since the daily reset, then exits silently.

## How it works

- PixAI resets daily points at **08:00 Taiwan time (00:00 UTC)**
- On every login, the monitor checks each account against `state.json`
- If an account hasn't been claimed since today's reset, it opens Chrome off-screen (`-3000,0`), logs in, passes Cloudflare Turnstile automatically, and claims the points
- Results (last claimed time + balance) are saved to `state.json`
- Logs are written to `logs/YYYY-MM.log` (monthly)

## Requirements

- Windows 10/11
- Python 3.10+
- Google Chrome installed at the default path (`C:\Program Files\Google\Chrome\Application\chrome.exe`)

## Setup

**1. Install dependencies (run once)**
```
setup.bat
```

**2. Configure accounts**

Copy `accounts.example.json` to `accounts.json` and fill in your PixAI credentials:
```json
[
  {"email": "you@gmail.com", "password": "yourpassword", "username": "your-pixai-username", "note": "Account01"},
  ...
]
```

**3. Set up autostart (run as Administrator)**
```
setup_autostart.bat
```
This registers a Windows Task Scheduler job that runs `monitor.py` once, 1 minute after every login.

## Manual run

Double-click `run_claim.bat` to trigger a claim check immediately without waiting for the next login.

## File overview

| File | Purpose |
|---|---|
| `monitor.py` | Main entry point — checks accounts and claims if needed |
| `claimer.py` | Browser automation logic (login, Turnstile, claim) |
| `logger.py` | Monthly rotating log file handler |
| `main.py` | Alternative entry point for claiming all accounts unconditionally |
| `accounts.json` | Your credentials (**gitignored**) |
| `accounts.example.json` | Template for accounts.json |
| `state.json` | Last claim time and balance per account (**gitignored**) |
| `sessions/` | Chrome profile data per account (**gitignored**) |
| `setup.bat` | One-time dependency installer |
| `setup_autostart.bat` | Registers autostart via Task Scheduler |
| `run_claim.bat` | Manual trigger |

## Notes

- Chrome runs off-screen at position `-3000,0` so it never overlaps your work
- Cloudflare Turnstile passes automatically (~1 second) when run from a residential IP with a real Chrome installation
- Sessions are persisted per account in `sessions/`, so login only happens once per account
- If an account fails, others continue unaffected
