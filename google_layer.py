
from datetime import datetime
import csv
import io
import time
from pathlib import Path

import pyperclip
from playwright.sync_api import sync_playwright
import config


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def parse_tsv(text):
    reader = csv.reader(io.StringIO(text), delimiter="\t", quotechar='"')
    rows = []
    for row in reader:
        rows.append([str(v).replace("\r", "").strip() for v in row])
    while rows and all(not x for x in rows[-1]):
        rows.pop()
    return rows


def start_google():
    if not config.GOOGLE_PROFILE_DIR.exists():
        raise RuntimeError("google_profile is missing. Run setup_google_profile.py first.")

    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(config.GOOGLE_PROFILE_DIR),
        channel="chrome",
        headless=False,
        viewport={"width": 1600, "height": 900},
        args=["--start-maximized", "--no-first-run", "--no-default-browser-check"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.bring_to_front()
    return pw, ctx, page


def open_sheet(page):
    page.goto(config.SPREADSHEET_URL, wait_until="domcontentloaded", timeout=120000)
    deadline = time.time() + 90
    while time.time() < deadline:
        url = page.url
        if "docs.google.com/spreadsheets/" in url and config.SPREADSHEET_ID in url:
            time.sleep(2)
            return
        time.sleep(1)
    raise RuntimeError(f"Google Sheets did not become ready. URL: {page.url}")


def select_worksheet(page, sheet_name):
    # Prefer direct tab click. Fall back to keyboard sheet navigation.
    selectors = [
        f'[aria-label="{sheet_name}"]',
        f'[data-tooltip="{sheet_name}"]',
        f'text="{sheet_name}"',
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            for i in range(loc.count()):
                item = loc.nth(i)
                if item.is_visible(timeout=700):
                    item.click(force=True, timeout=5000)
                    time.sleep(1)
                    return
        except Exception:
            pass

    # Reliable Sheets fallback: open sheet list with Alt+Shift+S,
    # then use keyboard search/navigation if available.
    raise RuntimeError(f"Could not select worksheet: {sheet_name}")


def select_range(page, sheet_name, cell_range):
    address = f"'{sheet_name}'!{cell_range}"
    page.keyboard.press("Control+J")
    time.sleep(.4)
    page.keyboard.type(address, delay=5)
    page.keyboard.press("Enter")
    time.sleep(1)


def copy_range(page, source):
    try:
        pyperclip.copy("")
    except Exception:
        pass

    page.keyboard.press("Control+C")

    for _ in range(30):
        time.sleep(.4)
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""
        if "\t" in text and "\n" in text:
            return text

    raise RuntimeError(
        f"Clipboard extraction failed for {source['sheet']}!{source['range']}"
    )


def extract_all():
    sources = config.SOURCES
    pw = ctx = None
    try:
        pw, ctx, page = start_google()
        open_sheet(page)

        result = {}
        for key, source in sources.items():
            log(f"Extracting {source['sheet']}!{source['range']}")
            select_worksheet(page, source["sheet"])
            select_range(page, source["sheet"], source["range"])
            rows = parse_tsv(copy_range(page, source))

            if len(rows) != source["rows"]:
                raise RuntimeError(
                    f"{source['sheet']}: expected {source['rows']} rows, got {len(rows)}"
                )
            for i, row in enumerate(rows, 1):
                if len(row) != source["columns"]:
                    raise RuntimeError(
                        f"{source['sheet']}: row {i} expected {source['columns']} columns, got {len(row)}"
                    )

            result[key] = rows
            log(f"  ✓ {len(rows)} rows × {len(rows[0])} cols")

        return result
    finally:
        if ctx:
            try: ctx.close()
            except Exception: pass
        if pw:
            try: pw.stop()
            except Exception: pass
