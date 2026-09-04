"""
AUTOMATION DASHBOARD — OUTPUT / REVENUE WHATSAPP

Sends:
    1. Revenue/Output number message
    2. CH Revenue image(s)
    3. All BDM Revenue images

No Google.
No JSON.
No formatting.
No captions.
"""

from pathlib import Path
from datetime import datetime
import re
import time

import config

from whatsapp_common import (
    TARGET_GROUP,
    start_whatsapp,
    wait_for_whatsapp,
    open_group,
    verify_group,
    send_text,
    send_image,
    close_whatsapp,
)


REVENUE_ROOT = Path(
    config.REVENUE_SCREENSHOT_DIR
)

NUMBER_FILE = (
    Path(config.WHATSAPP_DIR)
    /
    "revenue_numbers.txt"
)


RUN_PATTERN = re.compile(
    r"^\d{2}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$"
)


def banner(title):

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def parse_timestamp(folder):

    if not RUN_PATTERN.match(
        folder.name
    ):
        return None

    try:

        return datetime.strptime(
            folder.name,
            "%d_%m_%y_%H_%M_%S"
        )

    except ValueError:

        return None


def latest_run():

    if not REVENUE_ROOT.exists():

        raise RuntimeError(
            f"Revenue screenshot directory missing:\n"
            f"{REVENUE_ROOT}"
        )

    runs = []

    for folder in REVENUE_ROOT.iterdir():

        if not folder.is_dir():
            continue

        timestamp = parse_timestamp(
            folder
        )

        if timestamp:

            runs.append(
                (timestamp, folder)
            )

    if not runs:

        raise RuntimeError(
            "No revenue report run found."
        )

    runs.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return runs[0][1]


def extract_bdm_number(path):

    match = re.search(
        r"BDM_revenue_(\d+)_",
        path.name,
        re.IGNORECASE
    )

    if match:

        return int(
            match.group(1)
        )

    return 999999


def find_images(run_dir):

    ch_dir = run_dir / "CH"
    bdm_dir = run_dir / "BDM"

    if not ch_dir.exists():
        raise RuntimeError(
            f"CH revenue folder missing:\n{ch_dir}"
        )

    if not bdm_dir.exists():
        raise RuntimeError(
            f"BDM revenue folder missing:\n{bdm_dir}"
        )

    ch = sorted(
        ch_dir.glob("*.png")
    )

    bdm = sorted(
        bdm_dir.glob("*.png"),
        key=lambda p: (
            extract_bdm_number(p),
            p.name
        )
    )

    if not ch:
        raise RuntimeError(
            "No CH Revenue image found."
        )

    if not bdm:
        raise RuntimeError(
            "No BDM Revenue images found."
        )

    return ch + bdm


def load_message():

    if not NUMBER_FILE.exists():

        raise RuntimeError(
            f"Missing:\n{NUMBER_FILE}"
        )

    message = (
        NUMBER_FILE
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    if not message:

        raise RuntimeError(
            "revenue_numbers.txt is empty."
        )

    return message


def main():

    banner(
        "AUTOMATION DASHBOARD — OUTPUT / REVENUE DELIVERY"
    )

    run_dir = latest_run()

    message = load_message()

    images = find_images(
        run_dir
    )

    print()
    print(
        f"Target group : {TARGET_GROUP}"
    )

    print(
        f"Report run   : {run_dir.name}"
    )

    print(
        f"Total images : {len(images)}"
    )

    print()

    for index, image in enumerate(
        images,
        1
    ):

        print(
            f"{index}. {image.name}"
        )

    pw = None
    context = None

    try:

        pw, context, page = (
            start_whatsapp()
        )

        wait_for_whatsapp(
            page
        )

        open_group(
            page,
            TARGET_GROUP
        )

        verify_group(
            page,
            TARGET_GROUP
        )

        # ----------------------------------------------------------
        # Number message
        # ----------------------------------------------------------

        send_text(
            page,
            message
        )

        time.sleep(2)

        # ----------------------------------------------------------
        # Images
        # ----------------------------------------------------------

        banner(
            "SENDING OUTPUT / REVENUE"
        )

        for index, image in enumerate(
            images,
            1
        ):

            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"[{index}/{len(images)}] "
                f"Sending {image.name}",
                flush=True
            )

            send_image(
                page,
                image
            )

            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"✓ [{index}/{len(images)}] sent",
                flush=True
            )

            if index < len(images):

                time.sleep(4)

        # ----------------------------------------------------------
        # Success
        # ----------------------------------------------------------

        banner(
            "OUTPUT / REVENUE DELIVERY — PASSED"
        )

        print()
        print(
            "✓ Number message sent"
        )

        print(
            "✓ CH Revenue sent"
        )

        print(
            f"✓ {len(images) - 1} BDM Revenue image(s) sent"
        )

        print(
            f"✓ Total images: {len(images)}"
        )

        print(
            f"✓ Run: {run_dir.name}"
        )

        return 0

    except Exception as error:

        banner(
            "OUTPUT / REVENUE DELIVERY — FAILED"
        )

        print()
        print(
            f"ERROR: {error}"
        )

        return 1

    finally:

        if pw and context:

            try:

                close_whatsapp(
                    pw,
                    context
                )

            except Exception:
                pass


if __name__ == "__main__":

    raise SystemExit(
        main()
    )