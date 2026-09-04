"""
AUTOMATION DASHBOARD — WHATSAPP COMMON

FINAL PRODUCTION WHATSAPP LAYER

Flow:

    Persistent Chrome profile
            ↓
    WhatsApp Web
            ↓
    Target group
            ↓
    Number message
            ↓
    Attach
            ↓
    Photos & videos
            ↓
    Native file chooser
            ↓
    Image preview
            ↓
    Send

IMPORTANT:
- No generic input[type=file]
- No sticker picker
- No clipboard
- No drag/drop
- No captions
- No coordinate-based verification
"""

from pathlib import Path
import time

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

import config


# ============================================================================
# CONFIG
# ============================================================================

TARGET_GROUP = "prep@automation_test"

WHATSAPP_URL = "https://web.whatsapp.com/"

PROFILE_DIR = Path(config.CHROME_PROFILE_DIR)

STARTUP_TIMEOUT = 45
GROUP_TIMEOUT = 12
ELEMENT_TIMEOUT = 10


# ============================================================================
# GLOBALS
# ============================================================================

_pw = None
_context = None
_page = None


# ============================================================================
# LOGGING
# ============================================================================

def log(message):

    print(
        f"[{time.strftime('%H:%M:%S')}] {message}",
        flush=True
    )


# ============================================================================
# START WHATSAPP
# ============================================================================

def start_whatsapp():

    global _pw
    global _context
    global _page

    if not PROFILE_DIR.exists():

        raise RuntimeError(
            f"WhatsApp profile does not exist:\n"
            f"{PROFILE_DIR}"
        )

    log("Starting persistent Chrome profile.")
    log(f"Profile: {PROFILE_DIR}")

    try:

        _pw = sync_playwright().start()

        _context = _pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport=None,
            args=[
                "--start-maximized",
                "--disable-notifications",
            ],
        )

        # --------------------------------------------------------------------
        # REUSE EXISTING PAGE
        # --------------------------------------------------------------------

        pages = _context.pages

        if pages:

            _page = pages[0]

            log(
                f"Reusing existing Chrome page "
                f"({len(pages)} page(s) detected)."
            )

            for extra in pages[1:]:

                try:
                    extra.close()
                except Exception:
                    pass

        else:

            log(
                "No existing page found. Creating first page."
            )

            _page = _context.new_page()

        # --------------------------------------------------------------------
        # OPEN WHATSAPP
        # --------------------------------------------------------------------

        current_url = _page.url or ""

        if "web.whatsapp.com" not in current_url:

            log("Opening WhatsApp Web.")

            _page.goto(
                WHATSAPP_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

        else:

            log(
                "WhatsApp Web already open."
            )

        return _pw, _context, _page

    except Exception:

        try:
            if _context:
                _context.close()
        except Exception:
            pass

        try:
            if _pw:
                _pw.stop()
        except Exception:
            pass

        _pw = None
        _context = None
        _page = None

        raise


# ============================================================================
# WAIT FOR WHATSAPP
# ============================================================================

def wait_for_whatsapp(
    page,
    timeout=STARTUP_TIMEOUT
):

    log("Waiting for WhatsApp Web.")

    deadline = time.time() + timeout

    qr_logged = False

    while time.time() < deadline:

        try:

            url = page.url or ""

            if "web.whatsapp.com" not in url:

                time.sleep(0.5)
                continue

            # ----------------------------------------------------------------
            # LOGGED-IN SHELL
            # ----------------------------------------------------------------

            shell_selectors = [
                '[data-testid="chat-list"]',
                '[data-testid="chat-list-search"]',
                'button[aria-label*="Search"]',
                'div[contenteditable="true"]',
            ]

            for selector in shell_selectors:

                try:

                    locator = page.locator(selector)

                    count = locator.count()

                    for i in range(
                        min(count, 3)
                    ):

                        element = locator.nth(i)

                        try:

                            if element.is_visible():

                                log(
                                    "✓ WhatsApp Web session is ready."
                                )

                                return True

                        except Exception:
                            continue

                except Exception:
                    continue

            # ----------------------------------------------------------------
            # QR
            # ----------------------------------------------------------------

            qr_selectors = [
                'canvas[aria-label*="Scan"]',
                '[data-testid="qrcode"]',
                'div[data-ref]',
            ]

            if not qr_logged:

                for selector in qr_selectors:

                    try:

                        locator = page.locator(selector)

                        if locator.count() > 0:

                            for i in range(
                                min(locator.count(), 2)
                            ):

                                if locator.nth(i).is_visible():

                                    log(
                                        "⚠ WhatsApp login screen detected."
                                    )

                                    log(
                                        "Scan the QR code if required."
                                    )

                                    qr_logged = True
                                    break

                        if qr_logged:
                            break

                    except Exception:
                        continue

            time.sleep(0.5)

        except Exception:

            time.sleep(0.5)

    raise RuntimeError(
        "WhatsApp Web did not become ready within "
        f"{timeout} seconds."
    )


# ============================================================================
# SEARCH BOX
# ============================================================================

def find_search_box(
    page,
    timeout=ELEMENT_TIMEOUT
):

    selectors = [
        'div[contenteditable="true"][aria-label*="Search"]',
        'div[contenteditable="true"][data-placeholder*="Search"]',
        'input[placeholder*="Search"]',
        'input[aria-label*="Search"]',
    ]

    deadline = time.time() + timeout

    while time.time() < deadline:

        for selector in selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    element = locator.nth(i)

                    if element.is_visible():

                        return element

            except Exception:
                continue

        time.sleep(0.25)

    raise RuntimeError(
        "Could not find WhatsApp search box."
    )


# ============================================================================
# FIND GROUP DIRECTLY
# ============================================================================

def find_group_direct(
    page,
    group_name
):

    try:

        locator = page.get_by_text(
            group_name,
            exact=True
        )

        for i in range(locator.count()):

            element = locator.nth(i)

            try:

                if element.is_visible():
                    return element

            except Exception:
                continue

    except Exception:
        pass

    for selector in [
        '[role="listitem"]',
        '[data-testid="cell-frame-container"]',
    ]:

        try:

            rows = page.locator(selector)

            for i in range(rows.count()):

                row = rows.nth(i)

                try:

                    if not row.is_visible():
                        continue

                    text = row.inner_text(
                        timeout=500
                    ).strip()

                    if group_name.lower() in text.lower():

                        return row

                except Exception:
                    continue

        except Exception:
            continue

    return None


# ============================================================================
# OPEN GROUP
# ============================================================================

def open_group(
    page,
    group_name
):

    log(
        f"Opening target group: {group_name}"
    )

    # ------------------------------------------------------------------------
    # DIRECT
    # ------------------------------------------------------------------------

    direct = find_group_direct(
        page,
        group_name
    )

    if direct:

        try:

            direct.click()

            time.sleep(1)

            log(
                "✓ Target group opened."
            )

            return

        except Exception:
            pass

    # ------------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------------

    search = find_search_box(page)

    try:

        search.click()

    except Exception:
        pass

    try:

        search.fill(group_name)

    except Exception:

        search.press("Control+A")
        search.press("Backspace")
        search.type(group_name)

    time.sleep(1)

    # ------------------------------------------------------------------------
    # EXACT RESULT
    # ------------------------------------------------------------------------

    try:

        result = page.get_by_text(
            group_name,
            exact=True
        )

        for i in range(result.count()):

            element = result.nth(i)

            try:

                if element.is_visible():

                    element.click()

                    time.sleep(1)

                    log(
                        "✓ Target group opened."
                    )

                    return

            except Exception:
                continue

    except Exception:
        pass

    # ------------------------------------------------------------------------
    # ROW FALLBACK
    # ------------------------------------------------------------------------

    for selector in [
        '[role="listitem"]',
        '[data-testid="cell-frame-container"]',
    ]:

        try:

            rows = page.locator(selector)

            for i in range(rows.count()):

                row = rows.nth(i)

                try:

                    if not row.is_visible():
                        continue

                    text = row.inner_text(
                        timeout=500
                    ).strip()

                    if group_name.lower() in text.lower():

                        row.click()

                        time.sleep(1)

                        log(
                            "✓ Target group opened."
                        )

                        return

                except Exception:
                    continue

        except Exception:
            continue

    raise RuntimeError(
        f"Could not find target group:\n{group_name}"
    )


# ============================================================================
# VERIFY GROUP
# ============================================================================

def verify_group(
    page,
    group_name,
    timeout=GROUP_TIMEOUT
):

    log(
        f"Verifying target group: {group_name}"
    )

    deadline = time.time() + timeout

    while time.time() < deadline:

        # --------------------------------------------------------------------
        # Exact text
        # --------------------------------------------------------------------

        try:

            locator = page.get_by_text(
                group_name,
                exact=True
            )

            for i in range(locator.count()):

                element = locator.nth(i)

                try:

                    if element.is_visible():

                        log(
                            "✓ Target group verified."
                        )

                        return True

                except Exception:
                    continue

        except Exception:
            pass

        # --------------------------------------------------------------------
        # Header
        # --------------------------------------------------------------------

        for selector in [
            'header',
            '[data-testid="conversation-header"]',
            '[data-testid="conversation-info-header"]',
        ]:

            try:

                headers = page.locator(selector)

                for i in range(headers.count()):

                    header = headers.nth(i)

                    try:

                        if not header.is_visible():
                            continue

                        text = header.inner_text(
                            timeout=500
                        ).strip()

                        if group_name.lower() in text.lower():

                            log(
                                "✓ Target group verified."
                            )

                            return True

                    except Exception:
                        continue

            except Exception:
                continue

        time.sleep(0.25)

    raise RuntimeError(
        f"Could not verify target group:\n{group_name}"
    )


# ============================================================================
# MESSAGE BOX
# ============================================================================

def find_message_box(
    page,
    timeout=ELEMENT_TIMEOUT
):

    selectors = [
        'footer div[contenteditable="true"]',
        'div[contenteditable="true"][data-placeholder*="Type a message"]',
        'div[contenteditable="true"][aria-label*="message"]',
        'div[contenteditable="true"][aria-label*="Message"]',
    ]

    deadline = time.time() + timeout

    while time.time() < deadline:

        for selector in selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    element = locator.nth(i)

                    try:

                        if not element.is_visible():
                            continue

                        aria = (
                            element.get_attribute(
                                "aria-label"
                            )
                            or ""
                        ).lower()

                        placeholder = (
                            element.get_attribute(
                                "data-placeholder"
                            )
                            or ""
                        ).lower()

                        if "search" in aria:
                            continue

                        if "search" in placeholder:
                            continue

                        return element

                    except Exception:
                        continue

            except Exception:
                continue

        time.sleep(0.25)

    raise RuntimeError(
        "Could not find WhatsApp message composer."
    )


# ============================================================================
# SEND TEXT
# ============================================================================

def send_text(
    page,
    message
):

    if not message:

        raise RuntimeError(
            "Cannot send empty WhatsApp message."
        )

    log(
        "Sending number message."
    )

    box = find_message_box(page)

    try:

        box.fill(message)

    except Exception:

        box.click()
        box.press("Control+A")
        box.press("Backspace")
        box.type(message)

    box.press("Enter")

    time.sleep(1)

    log(
        "✓ Number message sent."
    )


# ============================================================================
# ATTACH BUTTON
# ============================================================================

def find_attach_button(
    page,
    timeout=ELEMENT_TIMEOUT
):

    selectors = [
        'button[aria-label*="Attach"]',
        'button[title*="Attach"]',
        '[data-testid="clip"]',
        'span[data-icon="clip"]',
    ]

    deadline = time.time() + timeout

    while time.time() < deadline:

        for selector in selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    element = locator.nth(i)

                    try:

                        if element.is_visible():
                            return element

                    except Exception:
                        continue

            except Exception:
                continue

        time.sleep(0.25)

    raise RuntimeError(
        "Could not find WhatsApp Attach button."
    )


# ============================================================================
# PHOTOS & VIDEOS
# ============================================================================

def find_photos_videos_option(
    page,
    timeout=ELEMENT_TIMEOUT
):

    selectors = [
        'text="Photos & videos"',
        'span:has-text("Photos & videos")',
        '[aria-label*="Photos"]',
    ]

    deadline = time.time() + timeout

    while time.time() < deadline:

        for selector in selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    element = locator.nth(i)

                    try:

                        if element.is_visible():
                            return element

                    except Exception:
                        continue

            except Exception:
                continue

        time.sleep(0.25)

    raise RuntimeError(
        "Could not find 'Photos & videos' option."
    )


# ============================================================================
# ATTACH IMAGE
# ============================================================================

def attach_image(
    page,
    image_path
):

    image_path = Path(image_path)

    if not image_path.exists():

        raise RuntimeError(
            f"Image does not exist:\n{image_path}"
        )

    if image_path.suffix.lower() not in [
        ".png",
        ".jpg",
        ".jpeg",
    ]:

        raise RuntimeError(
            f"Unsupported image format:\n{image_path}"
        )

    log(
        f"Attaching image: {image_path.name}"
    )

    # ------------------------------------------------------------------------
    # ATTACH
    # ------------------------------------------------------------------------

    attach = find_attach_button(page)

    attach.click()

    time.sleep(0.5)

    # ------------------------------------------------------------------------
    # PHOTOS & VIDEOS
    # ------------------------------------------------------------------------

    photos = find_photos_videos_option(page)

    try:

        with page.expect_file_chooser(
            timeout=10000
        ) as chooser_info:

            photos.click()

        chooser = chooser_info.value

        chooser.set_files(
            str(image_path)
        )

    except PlaywrightTimeoutError as error:

        raise RuntimeError(
            "WhatsApp did not open the photo file chooser."
        ) from error

    time.sleep(1.5)

    log(
        "✓ Image attached."
    )


# ============================================================================
# MEDIA SEND BUTTON — REFINED
# ============================================================================

def find_media_send_button(
    page,
    timeout=15
):

    """
    Locate the Send button inside the WhatsApp media composer.

    WhatsApp changes its DOM frequently, so we intentionally use multiple
    semantic strategies rather than one brittle selector.
    """

    log(
        "Looking for media Send button."
    )

    deadline = time.time() + timeout

    while time.time() < deadline:

        # ====================================================================
        # METHOD 1
        # Standard accessible buttons
        # ====================================================================

        selectors = [
            'button[aria-label="Send"]',
            'button[aria-label="Send message"]',
            'button[aria-label*="Send"]',
            '[role="button"][aria-label="Send"]',
            '[role="button"][aria-label*="Send"]',
            'button[title="Send"]',
            'button[title*="Send"]',
        ]

        for selector in selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    element = locator.nth(i)

                    try:

                        if element.is_visible():

                            log(
                                f"✓ Media Send button found "
                                f"via {selector}"
                            )

                            return element

                    except Exception:
                        continue

            except Exception:
                continue

        # ====================================================================
        # METHOD 2
        # WhatsApp send icon
        # ====================================================================

        icon_selectors = [
            'span[data-icon="send"]',
            'span[data-icon="send-filled"]',
            '[data-testid="send"]',
            '[data-testid*="send"]',
        ]

        for selector in icon_selectors:

            try:

                locator = page.locator(selector)

                for i in range(locator.count()):

                    icon = locator.nth(i)

                    try:

                        if not icon.is_visible():
                            continue

                        # The icon itself may not be clickable.
                        # Find its closest button/role=button.
                        button = icon.locator(
                            "xpath=ancestor::*[@role='button' or self::button][1]"
                        )

                        if button.count() > 0:

                            candidate = button.first

                            if candidate.is_visible():

                                log(
                                    f"✓ Media Send button found "
                                    f"via icon {selector}"
                                )

                                return candidate

                        # If icon itself is clickable, return it.
                        return icon

                    except Exception:
                        continue

            except Exception:
                continue

        # ====================================================================
        # METHOD 3
        # Inspect visible buttons by accessible text/attributes
        # ====================================================================

        try:

            buttons = page.locator(
                'button, [role="button"]'
            )

            for i in range(buttons.count()):

                button = buttons.nth(i)

                try:

                    if not button.is_visible():
                        continue

                    aria = (
                        button.get_attribute(
                            "aria-label"
                        )
                        or ""
                    ).strip().lower()

                    title = (
                        button.get_attribute(
                            "title"
                        )
                        or ""
                    ).strip().lower()

                    data_testid = (
                        button.get_attribute(
                            "data-testid"
                        )
                        or ""
                    ).strip().lower()

                    text = ""

                    try:
                        text = button.inner_text(
                            timeout=300
                        ).strip().lower()
                    except Exception:
                        pass

                    combined = " ".join([
                        aria,
                        title,
                        data_testid,
                        text,
                    ])

                    if (
                        "send" in combined
                        and "forward" not in combined
                    ):

                        log(
                            "✓ Media Send button found "
                            "via semantic button scan."
                        )

                        return button

                except Exception:
                    continue

        except Exception:
            pass

        # ====================================================================
        # METHOD 4
        # Search SVG/icon parent containers
        # ====================================================================

        try:

            svg = page.locator(
                "svg"
            )

            for i in range(svg.count()):

                element = svg.nth(i)

                try:

                    if not element.is_visible():
                        continue

                    parent = element.locator(
                        "xpath=ancestor::*[@role='button' or self::button][1]"
                    )

                    if parent.count() == 0:
                        continue

                    candidate = parent.first

                    if not candidate.is_visible():
                        continue

                    aria = (
                        candidate.get_attribute(
                            "aria-label"
                        )
                        or ""
                    ).lower()

                    title = (
                        candidate.get_attribute(
                            "title"
                        )
                        or ""
                    ).lower()

                    if (
                        "send" in aria
                        or "send" in title
                    ):

                        log(
                            "✓ Media Send button found "
                            "via SVG parent."
                        )

                        return candidate

                except Exception:
                    continue

        except Exception:
            pass

        time.sleep(0.3)

    # =========================================================================
    # DEBUG INFORMATION
    # =========================================================================

    # If we reach this point, save a screenshot and dump visible buttons.
    try:

        debug_dir = Path(
            config.WHATSAPP_DIR
        ) / "debug"

        debug_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        screenshot_path = (
            debug_dir
            / "media_send_button_failed.png"
        )

        page.screenshot(
            path=str(screenshot_path),
            full_page=False
        )

        log(
            f"Debug screenshot saved:\n"
            f"{screenshot_path}"
        )

    except Exception:
        pass

    # Dump visible buttons to terminal.
    try:

        buttons = page.locator(
            'button, [role="button"]'
        )

        print()
        print(
            "VISIBLE BUTTONS AT FAILURE:"
        )
        print(
            "-" * 70
        )

        shown = 0

        for i in range(buttons.count()):

            if shown >= 30:
                break

            button = buttons.nth(i)

            try:

                if not button.is_visible():
                    continue

                aria = (
                    button.get_attribute(
                        "aria-label"
                    )
                    or ""
                )

                title = (
                    button.get_attribute(
                        "title"
                    )
                    or ""
                )

                testid = (
                    button.get_attribute(
                        "data-testid"
                    )
                    or ""
                )

                text = ""

                try:
                    text = button.inner_text(
                        timeout=200
                    ).strip()
                except Exception:
                    pass

                print(
                    f"{shown + 1}. "
                    f"aria={aria!r} | "
                    f"title={title!r} | "
                    f"testid={testid!r} | "
                    f"text={text!r}"
                )

                shown += 1

            except Exception:
                continue

    except Exception:
        pass

    raise RuntimeError(
        "Could not find media Send button."
    )


# ============================================================================
# SEND IMAGE
# ============================================================================

def send_image(
    page,
    image_path
):

    attach_image(
        page,
        image_path
    )

    # ------------------------------------------------------------------------
    # MEDIA PREVIEW
    # ------------------------------------------------------------------------

    deadline = time.time() + 10

    preview_found = False

    while time.time() < deadline:

        try:

            # Look for images that are currently visible.
            images = page.locator(
                "img"
            )

            for i in range(images.count()):

                image = images.nth(i)

                try:

                    if image.is_visible():

                        preview_found = True
                        break

                except Exception:
                    continue

            if preview_found:
                break

        except Exception:
            pass

        time.sleep(0.3)

    if not preview_found:

        raise RuntimeError(
            "Image attached but media preview "
            "was not detected."
        )

    log(
        "✓ Media preview detected."
    )

    # ------------------------------------------------------------------------
    # SEND
    # ------------------------------------------------------------------------

    send_button = find_media_send_button(
        page,
        timeout=15
    )

    send_button.click()

    # ------------------------------------------------------------------------
    # WAIT FOR WHATSAPP TO FINISH THE MEDIA SEND
    # ------------------------------------------------------------------------
    #
    # Do not immediately start attaching the next image. WhatsApp can keep
    # the media composer alive briefly after the Send click. If the next
    # attachment starts during that transition, the second image can replace
    # or interfere with the previous media send.
    #
    # We wait for the normal chat composer/Attach button to become available
    # again. This makes image sending strictly sequential.
    # ------------------------------------------------------------------------

    settle_deadline = time.time() + 12

    while time.time() < settle_deadline:

        try:

            # The media composer normally closes and the regular Attach
            # button becomes available again.
            attach_buttons = page.locator(
                'button[aria-label*="Attach"], '
                'button[title*="Attach"], '
                '[data-testid="clip"], '
                'span[data-icon="clip"]'
            )

            attach_visible = False

            for i in range(attach_buttons.count()):

                try:

                    if attach_buttons.nth(i).is_visible():

                        attach_visible = True
                        break

                except Exception:
                    continue

            # If the normal composer is back, give WhatsApp a small final
            # processing window before the next image is attached.
            if attach_visible:

                time.sleep(1.5)

                log(
                    f"✓ Image send completed: "
                    f"{Path(image_path).name}"
                )

                return

        except Exception:
            pass

        time.sleep(0.3)

    # Conservative fallback: the Send click has already happened. Wait a
    # little longer rather than immediately attaching another image.
    time.sleep(2)

    log(
        f"✓ Image send completed: "
        f"{Path(image_path).name}"
    )


# ============================================================================
# CLOSE
# ============================================================================

def close_whatsapp(
    pw=None,
    context=None
):

    global _pw
    global _context
    global _page

    log(
        "Closing WhatsApp."
    )

    active_context = context or _context
    active_pw = pw or _pw

    try:

        if active_context:
            active_context.close()

    except Exception:
        pass

    try:

        if active_pw:
            active_pw.stop()

    except Exception:
        pass

    _page = None
    _context = None
    _pw = None

    log(
        "✓ WhatsApp closed."
    )