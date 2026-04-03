SECTION 1 — OVERVIEW
CryptEX is a live crypto grid trading CLI application in this repository.
It runs a static neutral grid strategy, submits real Kraken spot orders, tracks fills, and enforces risk stops.
WARNING: This bot can trade real money and can lose capital.

SECTION 2 — REQUIREMENTS
- Windows 10/11 (PowerShell)
- Python 3.11+
- Internet connection
- Kraken account with API access

SECTION 3 — INSTALLATION
1. Clone the repository.
2. Open PowerShell in the repo root.
3. Create and activate a virtual environment:
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
4. Install dependencies:
   pip install -e .

SECTION 4 — API SETUP
1. In Kraken, create an API key with permissions for balances, open orders, add order, cancel order, and trades history.
2. Set environment variables in PowerShell:
   setx KRAKEN_API_KEY "your_key"
   setx KRAKEN_API_SECRET "your_secret"
3. Restart PowerShell so new variables are loaded.

Optional .env file in repo root:
KRAKEN_API_KEY=your_key
KRAKEN_API_SECRET=your_secret

SECTION 5 — RUNNING THE BOT
Run this exact command:
crypt_ex run --strategy strategies/doge_usd_grid_live.json --live

What happens:
- loads and validates strategy JSON
- validates live arming and Kraken credentials
- loads Kraken symbol constraints
- reconciles open orders
- places the initial live grid
- enters the runtime loop for fills/risk checks

SECTION 6 — SAFETY NOTES
- This places real orders on Kraken.
- Start with small quote allocation.
- Verify symbol, bounds, and risk limits before each run.
- If the engine detects uncertainty, it stops and cancels managed orders.

SECTION 7 — TROUBLESHOOTING
- "missing KRAKEN_API_KEY/KRAKEN_API_SECRET": set env vars and restart shell.
- "live mode requested ... --live": add the --live flag.
- Kraken request/authentication errors: verify key permissions and secret value.
- Connection errors: verify internet access and Kraken API status.
