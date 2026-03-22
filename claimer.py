import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

LOGIN_URL = "https://pixai.art/login"
BASE_URL = "https://pixai.art/zh"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
DEBUG_DIR = os.path.join(BASE_DIR, "logs", "debug")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


@dataclass
class ClaimResult:
    email: str
    success: bool
    already_claimed: bool
    credits_claimed: Optional[int]
    error: Optional[str]
    note: Optional[str] = None
    balance: Optional[int] = None

    def __str__(self):
        label = self.note or self.email
        bal = f" (balance: {self.balance:,} pts)" if self.balance else ""
        if self.already_claimed:
            return f"[{label}] Already claimed today, skipping{bal}"
        if self.success:
            credits_str = f" (+{self.credits_claimed:,} pts)" if self.credits_claimed else ""
            return f"[{label}] Claim successful{credits_str}{bal}"
        return f"[{label}] Failed: {self.error}"


def _extract(result):
    """Extract value from Pydoll CDP response: {id, result: {result: {type, value}}}"""
    if isinstance(result, dict):
        return result.get("result", {}).get("result", {}).get("value")
    return result


async def _js(tab, code: str):
    result = await tab.execute_script(f"(() => {{ {code} }})()")
    return _extract(result)


async def _screenshot(tab, name: str):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    try:
        await tab.take_screenshot(path)
    except Exception:
        pass


async def _get_url(tab) -> str:
    try:
        result = await tab.execute_script("window.location.href")
        return _extract(result) or ""
    except Exception:
        return ""


async def _get_balance(tab) -> Optional[int]:
    result = await _js(tab, r"""
        const text = document.body.innerText;
        // Modal header: "可用點數 🟡 X,XXX"
        const modalMatch = text.match(/可用點數[\s\S]{0,10}?([\d,]+)/);
        if (modalMatch) return modalMatch[1].replace(/,/g, '');
        // Profile page: "X,XXX +" (balance with + indicator next to coin icon)
        const profileMatch = text.match(/([\d,]+)\s*\+/);
        if (profileMatch) return profileMatch[1].replace(/,/g, '');
        return null;
    """)
    if result:
        try:
            return int(str(result).replace(",", ""))
        except ValueError:
            pass
    return None


async def _login(tab, email: str, password: str, logger) -> bool:
    safe = email.replace("@", "_").replace(".", "_")
    logger.info(f"[{safe}] Navigating to login page...")
    await tab.go_to(LOGIN_URL)
    await asyncio.sleep(5)
    await _screenshot(tab, f"{safe}_1_login_page")

    # Wait for buttons to appear
    for _ in range(15):
        has_buttons = await _js(tab, "return document.querySelectorAll('button').length > 0")
        if has_buttons:
            break
        await asyncio.sleep(1)
    await asyncio.sleep(2)

    # Click email login button
    try:
        btn = await tab.find(tag_name="button", text="電子郵件", timeout=10)
        await btn.click()
    except Exception:
        clicked = await _js(tab, """
            const btns = Array.from(document.querySelectorAll('button'));
            const t = btns.find(b => b.textContent.includes('電子郵件') || b.textContent.toLowerCase().includes('email'));
            if (t) { t.click(); return true; }
            return false;
        """)
        if not clicked:
            raise RuntimeError("Email login button not found")
    await asyncio.sleep(3)
    await _screenshot(tab, f"{safe}_2_after_email_btn")

    # Wait for email input
    for _ in range(10):
        has_email = await _js(tab, 'return !!document.querySelector(\'input[type="email"]\')')
        if has_email:
            break
        await asyncio.sleep(1)
    else:
        raise RuntimeError("Email input not found")

    # Fill form using React-compatible native setter
    filled = await _js(tab, f"""
        const emailInput = document.querySelector('input[type="email"]');
        const pwInput = document.querySelector('input[type="password"]');
        if (!emailInput) return 'no_email';
        if (!pwInput) return 'no_pw';
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(emailInput, {repr(email)});
        emailInput.dispatchEvent(new Event('input', {{bubbles: true}}));
        nativeSetter.call(pwInput, {repr(password)});
        pwInput.dispatchEvent(new Event('input', {{bubbles: true}}));
        return 'ok';
    """)
    if filled != "ok":
        raise RuntimeError(f"Form fill failed: {filled}")

    await _screenshot(tab, f"{safe}_3_filled")

    submitted = await _js(tab, """
        const btn = document.querySelector('button[type="submit"]');
        if (btn) { btn.click(); return true; }
        return false;
    """)
    if not submitted:
        raise RuntimeError("Submit button not found")

    await asyncio.sleep(6)
    await _screenshot(tab, f"{safe}_4_after_login")

    url = await _get_url(tab)
    if "login" in url.lower():
        raise RuntimeError(f"Login failed, still on login page (URL: {url})")

    logger.info(f"[{safe}] Login successful")
    return True


async def _is_logged_in(tab) -> bool:
    url = await _get_url(tab)
    if "login" in url.lower():
        return False
    result = await _js(tab, """
        const loginBtn = Array.from(document.querySelectorAll('a, button'))
            .find(el => el.textContent.trim() === '登入' || (el.href && el.href.includes('/login')));
        return !loginBtn;
    """)
    return bool(result)


async def _claim_daily(tab, username: str, logger) -> tuple[bool, bool, Optional[int], Optional[int]]:
    safe = username
    profile_url = f"{BASE_URL}/@{username}/artworks"

    logger.info(f"[{safe}] Navigating to profile page...")
    await tab.go_to(profile_url)
    await asyncio.sleep(6)
    await _screenshot(tab, f"{safe}_5_profile")

    check = await _js(tab, """
        const allEls = Array.from(document.querySelectorAll('*'));
        const dailyEl = allEls.find(el =>
            (el.childNodes.length > 0 &&
            Array.from(el.childNodes).some(n => n.textContent && n.textContent.trim() === '每日任務')) ||
            el.textContent.trim() === '每日任務'
        );
        if (!dailyEl) return 'no_row';
        let container = dailyEl;
        for (let i = 0; i < 6; i++) {
            if (!container.parentElement) break;
            container = container.parentElement;
            const btns = Array.from(container.querySelectorAll('button'));
            const claimBtn = btns.find(b => b.textContent.trim() === '領取');
            if (claimBtn) return claimBtn.disabled ? 'disabled' : 'ready';
        }
        return 'no_button';
    """)

    if check == "no_row":
        logger.warning(f"[{safe}] Daily task row not found")
        return False, False, None, None
    if check in ("disabled", "no_button"):
        balance = await _get_balance(tab)
        logger.info(f"[{safe}] Already claimed today")
        return False, True, None, balance

    logger.info(f"[{safe}] Opening daily claim modal...")
    await _js(tab, """
        const allEls = Array.from(document.querySelectorAll('*'));
        const dailyEl = allEls.find(el =>
            (el.childNodes.length > 0 &&
            Array.from(el.childNodes).some(n => n.textContent && n.textContent.trim() === '每日任務')) ||
            el.textContent.trim() === '每日任務'
        );
        if (!dailyEl) return false;
        let container = dailyEl;
        for (let i = 0; i < 6; i++) {
            if (!container.parentElement) break;
            container = container.parentElement;
            const btns = Array.from(container.querySelectorAll('button'));
            const claimBtn = btns.find(b => b.textContent.trim() === '領取');
            if (claimBtn) { claimBtn.click(); return true; }
        }
        return false;
    """)

    await asyncio.sleep(3)
    await _screenshot(tab, f"{safe}_6_modal_opened")

    logger.info(f"[{safe}] Waiting for Cloudflare Turnstile...")
    for i in range(40):
        await asyncio.sleep(1)

        token_set = await _js(tab, """
            const input = document.querySelector('input[name="cf-turnstile-response"]');
            return input ? input.value.length > 10 : false;
        """)
        if token_set:
            logger.info(f"[{safe}] Turnstile token received (sec {i+1})")
            break

        btn_enabled = await _js(tab, """
            const b = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.includes('領取每日'));
            if (!b) return false;
            return !b.disabled && !b.getAttribute('disabled');
        """)
        if btn_enabled:
            logger.info(f"[{safe}] Claim button enabled (sec {i+1})")
            break
    else:
        await _screenshot(tab, f"{safe}_7_turnstile_timeout")
        logger.warning(f"[{safe}] Turnstile timeout, attempting force click")

    await _screenshot(tab, f"{safe}_7_after_turnstile")
    await asyncio.sleep(1)
    await _screenshot(tab, f"{safe}_8_before_final_click")

    await _js(tab, """
        const b = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('領取每日'));
        if (b) b.click();
    """)
    logger.info(f"[{safe}] Clicked daily claim button")

    await asyncio.sleep(5)
    await _screenshot(tab, f"{safe}_9_after_claim")

    # Read balance now while modal is still showing the success state
    # ("可用點數 🟡 X,XXX" is visible in the modal header)
    balance = await _get_balance(tab)

    modal_closed = await _js(tab, """
        const b = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('領取每日'));
        return !b;
    """)

    if not modal_closed:
        await _screenshot(tab, f"{safe}_9b_modal_still_open")
        logger.warning(f"[{safe}] Modal not closed, claim may have failed")
        return False, False, None, None

    return True, False, 10000, balance


async def claim_for_account(
    email: str, password: str, username: str, note: Optional[str] = None
) -> ClaimResult:
    from logger import get_logger
    logger = get_logger()

    safe = email.replace("@", "_at_").replace(".", "_")
    profile_dir = os.path.join(SESSION_DIR, safe)
    os.makedirs(profile_dir, exist_ok=True)

    options = ChromiumOptions()
    options.binary_location = CHROME_PATH
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--window-position=-3000,0")
    options.add_argument("--lang=zh-TW")

    try:
        async with Chrome(options=options) as browser:
            tab = await browser.start()

            await tab.go_to(BASE_URL)
            await asyncio.sleep(4)

            if not await _is_logged_in(tab):
                await _login(tab, email, password, logger)

            success, already_claimed, credits, balance = await _claim_daily(tab, username, logger)

            return ClaimResult(
                email=email,
                success=success,
                already_claimed=already_claimed,
                credits_claimed=credits,
                error=None,
                note=note,
                balance=balance,
            )

    except Exception as e:
        return ClaimResult(
            email=email,
            success=False,
            already_claimed=False,
            credits_claimed=None,
            error=str(e),
            note=note,
        )
