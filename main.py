import asyncio
import json
import os
from datetime import datetime, timezone

from claimer import claim_for_account
from logger import get_logger, ensure_yearly_handler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.json")
DELAY_BETWEEN_ACCOUNTS = 10  # seconds between accounts


def load_accounts() -> list[dict]:
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"accounts.json not found: {ACCOUNTS_FILE}")
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        accounts = json.load(f)
    if not accounts:
        raise ValueError("accounts.json is empty")
    return accounts


async def run_all_accounts():
    logger = get_logger()
    ensure_yearly_handler(logger)

    try:
        accounts = load_accounts()
    except Exception as e:
        logger.error(f"Failed to load accounts: {e}")
        return

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info(f"===== Starting claim run: {len(accounts)} accounts [{now_utc}] =====")

    total_success = 0
    total_already = 0
    total_failed = 0

    for i, account in enumerate(accounts):
        email    = account.get("email", "").strip()
        password = account.get("password", "").strip()
        username = account.get("username", "").strip()
        note     = account.get("note", "").strip() or None

        if not email or not password or not username:
            logger.warning(f"Account #{i+1} missing fields, skipping")
            continue

        logger.info(f"Processing: {note or email}")
        result = await claim_for_account(email, password, username, note)
        logger.info(str(result))

        if result.already_claimed:
            total_already += 1
        elif result.success:
            total_success += 1
        else:
            total_failed += 1

        if i < len(accounts) - 1:
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    logger.info(f"===== Done | claimed: {total_success} | skipped: {total_already} | failed: {total_failed} =====")


if __name__ == "__main__":
    asyncio.run(run_all_accounts())
    input("\nFinished! Press Enter to close...")
