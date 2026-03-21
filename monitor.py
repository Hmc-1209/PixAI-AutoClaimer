"""
PixAI Auto Claim Monitor
Runs once on startup. Claims for any account that hasn't been claimed
since today's daily reset (08:00 Taiwan time = 00:00 UTC).
"""
import asyncio
import json
import os
from datetime import datetime, timezone

from claimer import claim_for_account
from logger import get_logger, ensure_yearly_handler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
DELAY_BETWEEN_ACCOUNTS = 10  # seconds between accounts


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def today_reset_utc() -> datetime:
    """PixAI resets at 08:00 Taiwan time = 00:00 UTC each day."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def needs_claim(state: dict, username: str) -> bool:
    if username not in state:
        return True
    last_claimed = state[username].get("last_claimed")
    if not last_claimed:
        return True
    last_dt = datetime.fromisoformat(last_claimed)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    return last_dt < today_reset_utc()


async def run():
    logger = get_logger()
    ensure_yearly_handler(logger)

    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        accounts = json.load(f)

    state = load_state()
    to_claim = [a for a in accounts if needs_claim(state, a["username"])]

    logger.info(f"PixAI monitor started — {len(accounts)} accounts total, {len(to_claim)} need claiming")

    if not to_claim:
        logger.info("All accounts already claimed since today's reset (00:00 UTC). Nothing to do.")
        return

    labels = [a.get("note") or a["username"] for a in to_claim]
    logger.info(f"Accounts to claim: {labels}")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, account in enumerate(to_claim):
        email    = account["email"].strip()
        password = account["password"].strip()
        username = account["username"].strip()
        note     = account.get("note", "").strip() or None

        result = await claim_for_account(email, password, username, note)
        logger.info(str(result))

        if result.success:
            success_count += 1
        elif result.already_claimed:
            skip_count += 1
        else:
            fail_count += 1

        if result.success or result.already_claimed:
            state[username] = {
                "note": note or username,
                "last_claimed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "balance": result.balance,
            }
            save_state(state)

        if i < len(to_claim) - 1:
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    logger.info(f"Done — claimed: {success_count} | already done: {skip_count} | failed: {fail_count}")


if __name__ == "__main__":
    asyncio.run(run())
