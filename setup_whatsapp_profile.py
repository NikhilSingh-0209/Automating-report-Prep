"""
ONE-TIME WHATSAPP PROFILE SETUP

Creates a NEW persistent Chrome profile:
    automation_dashboard\chrome_profile_wa

You log in once using the QR code.
The sender will reuse this exact profile later.
"""

from pathlib import Path
import time

from playwright.sync_api import sync_playwright


BASE = Path(__file__).resolve().parent
PROFILE = BASE / "chrome_profile_wa"
URL = "https://web.whatsapp.com/"


def main():
    print("=" * 78)
    print("AUTOMATION DASHBOARD — WHATSAPP PROFILE SETUP")
    print("=" * 78)
    print()
    print(f"New persistent profile:")
    print(PROFILE)
    print()
    print("1. A NEW Chrome profile will open.")
    print("2. Scan the WhatsApp QR code with the phone/account you want.")
    print("3. Wait until the complete WhatsApp chat list appears.")
    print("4. DO NOT close Chrome.")
    print("5. This script will wait until WhatsApp is authenticated.")
    print()

    PROFILE.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()

    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE),
        headless=False,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        viewport=None,
    )

    page = context.pages[0] if context.pages else context.new_page()
    page.goto(URL, wait_until="domcontentloaded")

    print("=" * 78)
    print("SCAN QR / COMPLETE WHATSAPP LOGIN")
    print("=" * 78)

    deadline = time.time() + 300

    while time.time() < deadline:
        try:
            url = page.url.lower()

            if (
                "web.whatsapp.com" in url
                and (
                    page.locator("#pane-side").count() > 0
                    or page.locator(
                        'div[aria-label="Search or start a new chat"]'
                    ).count() > 0
                )
            ):
                print()
                print("✓ WHATSAPP LOGIN DETECTED")
                print()
                print("Persistent profile is now:")
                print(PROFILE)
                print()
                print("This profile will be reused by the sender.")
                print("Leave Chrome open for 5 seconds so the session settles.")
                time.sleep(5)
                print()
                print("✓ WHATSAPP PROFILE SETUP COMPLETE")
                input("\nPress ENTER to close Chrome...")
                context.close()
                pw.stop()
                return

        except Exception:
            pass

        time.sleep(2)

    context.close()
    pw.stop()

    raise SystemExit(
        "WhatsApp login was not detected within 5 minutes."
    )


if __name__ == "__main__":
    main()
