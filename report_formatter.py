"""
STEP 4 — REPORT FORMATTER / IMAGE ENGINE

Input:
    four in-memory Python tables:
      ch_leads
      ch_revenue
      bdm_leads
      bdm_revenue

Output:
    screenshots/
      leads/
        CH/
        BDM/
      revenue/
        CH/
        BDM/

    whatsapp_output/
      leads_numbers.txt
      revenue_numbers.txt

Important:
- No Google access here.
- No JSON dependency.
- No hardcoded total BDM image count.
- Source values are preserved; only display formatting is applied.
- Revenue numbers are ALWAYS displayed with exactly 2 decimals.
- Percentages are ALWAYS displayed with exactly 2 decimals.
- BDM image count is derived from actual rows.
"""

from datetime import datetime
from pathlib import Path
import csv
import io
import math
import re

from PIL import Image, ImageDraw, ImageFont

import config


# ======================================================================
# OPTIONAL MANUAL-PASTE MODE
# ======================================================================

RAW_CH_LEADS = r"""
"""

RAW_CH_REVENUE = r"""
"""

RAW_BDM_LEADS = r"""
"""

RAW_BDM_REVENUE = r"""
"""


# ======================================================================
# GENERAL HELPERS
# ======================================================================

def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", "").strip()


def parse_tsv(text):
    if not text or not text.strip():
        return None

    rows = []
    reader = csv.reader(
        io.StringIO(text.strip()),
        delimiter="\t",
        quotechar='"'
    )

    for row in reader:
        rows.append([clean(x) for x in row])

    while rows and not any(rows[-1]):
        rows.pop()

    return rows or None


def number(value):
    """
    Convert a cell to float without changing the underlying source data.
    Handles:
      5
      5.00
      1,234.56
      57.00%
    """
    s = clean(value)

    if not s:
        return None

    s = (
        s.replace(",", "")
         .replace("₹", "")
         .replace("%", "")
    )

    s = re.sub(r"[^\d.\-]", "", s)

    if not s or s in {"-", ".", "-."}:
        return None

    try:
        return float(s)
    except ValueError:
        return None


def fmt_2(value):
    """
    Exact two-decimal display.

    This is intentionally used for:
      Target
      Actual
      FTD
      D-1
      D-2
      D-3
      MTD
    """
    n = number(value)
    if n is None:
        return clean(value)
    return f"{n:.2f}"


def fmt_int(value):
    n = number(value)
    if n is None:
        return clean(value)
    return f"{n:,.0f}"


def fmt_pct(value):
    n = number(value)
    if n is None:
        return clean(value)

    # Source sheets show percentage as e.g. 1.32%.
    # If a raw numeric percentage is already "1.32", keep it as 1.32%.
    return f"{n:.2f}%"


def is_total(row):
    for value in row[:3]:
        if clean(value).lower() == "total":
            return True
    return False


def rows_with_data(rows):
    return [row for row in rows if any(clean(x) for x in row)]


def font(size, bold=False, times=False):
    if times:
        candidates = (
            ["timesbd.ttf", "times.ttf"]
            if bold
            else ["times.ttf"]
        )
    else:
        candidates = (
            ["arialbd.ttf", "segoeuib.ttf"]
            if bold
            else ["arial.ttf", "segoeui.ttf"]
        )

    for filename in candidates:
        path = Path(r"C:\Windows\Fonts") / filename
        if path.exists():
            return ImageFont.truetype(str(path), size)

    return ImageFont.load_default()


def text_size(draw, text, f):
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw, text, f, max_width):
    text = clean(text)

    if not text:
        return ""

    # Preserve manual line breaks if they exist.
    paragraphs = text.split("\n")
    output = []

    for paragraph in paragraphs:
        words = paragraph.split()

        if not words:
            output.append("")
            continue

        current = ""

        for word in words:
            candidate = word if not current else current + " " + word
            w, _ = text_size(draw, candidate, f)

            if w <= max_width:
                current = candidate
            else:
                if current:
                    output.append(current)
                current = word

        if current:
            output.append(current)

    return "\n".join(output)


def draw_centered(draw, box, text, f, fill="black"):
    x1, y1, x2, y2 = box
    wrapped = wrap_text(draw, text, f, max(10, x2 - x1 - 12))

    bbox = draw.multiline_textbbox(
        (0, 0),
        wrapped,
        font=f,
        spacing=3,
        align="center"
    )

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.multiline_text(
        (
            x1 + (x2 - x1 - tw) / 2,
            y1 + (y2 - y1 - th) / 2,
        ),
        wrapped,
        font=f,
        fill=fill,
        spacing=3,
        align="center",
    )


# ======================================================================
# DISPLAY DEFINITIONS
# ======================================================================

CH_REVENUE_COLUMNS = [
    "CH Name",
    "Target\n(lacs)",
    "Actual\n(lacs)",
    "Ach%",
    "FTD",
    "D-1",
    "MTD",
]

BDM_REVENUE_COLUMNS = [
    "CH Name",
    "BDM Name",
    "Target\n(lacs)",
    "Actual\n(lacs)",
    "Ach%",
    "FTD",
    "D-1",
    "MTD",
]

CH_LEADS_COLUMNS = [
    "CH Name",
    "Target_Leads",
    "Actual_Leads",
    "Ach %_Leads",
    "Signups",
    "Signups%",
    "#leads\nD-1",
    "#signups\nD-1",
    "#leads\nD-2",
    "#signups\nD-2",
    "#leads\nD-3",
    "#signups\nD-3",
]

BDM_LEADS_COLUMNS = [
    "CH Name",
    "BDM Name",
    "Target_Leads",
    "Actual_Leads",
    "Ach %_Leads",
    "Signups",
    "Signups%",
    "#leads\nD-1",
    "#signups\nD-1",
    "#leads\nD-2",
    "#signups\nD-2",
    "#leads\nD-3",
    "#signups\nD-3",
]


# ======================================================================
# CELL FORMATTERS
# ======================================================================

def format_revenue_row(row, bdm=False):
    expected = 8 if bdm else 7
    row = list(row) + [""] * max(0, expected - len(row))

    if bdm:
        # A B = names
        # C D = money/lacs
        # E = percentage
        # F G H = numeric
        return [
            clean(row[0]),
            clean(row[1]),
            fmt_2(row[2]),
            fmt_2(row[3]),
            fmt_pct(row[4]),
            fmt_2(row[5]),
            fmt_2(row[6]),
            fmt_2(row[7]),
        ]

    return [
        clean(row[0]),
        fmt_2(row[1]),
        fmt_2(row[2]),
        fmt_pct(row[3]),
        fmt_2(row[4]),
        fmt_2(row[5]),
        fmt_2(row[6]),
    ]


def format_lead_row(row, bdm=False):
    expected = 13 if bdm else 12
    row = list(row) + [""] * max(0, expected - len(row))

    if bdm:
        return [
            clean(row[0]),
            clean(row[1]),
            fmt_int(row[2]),
            fmt_int(row[3]),
            fmt_pct(row[4]),
            fmt_int(row[5]),
            fmt_pct(row[6]),
            fmt_int(row[7]),
            fmt_int(row[8]),
            fmt_int(row[9]),
            fmt_int(row[10]),
            fmt_int(row[11]),
            fmt_int(row[12]),
        ]

    return [
        clean(row[0]),
        fmt_int(row[1]),
        fmt_int(row[2]),
        fmt_pct(row[3]),
        fmt_int(row[4]),
        fmt_pct(row[5]),
        fmt_int(row[6]),
        fmt_int(row[7]),
        fmt_int(row[8]),
        fmt_int(row[9]),
        fmt_int(row[10]),
        fmt_int(row[11]),
    ]


# ======================================================================
# IMAGE ENGINE
# ======================================================================
def draw_dashed_rectangle(
    draw,
    box,
    fill=None,
    outline="black",
    width=1,
    dash=7,
    gap=4
):
    """Draw a filled rectangle with dashed borders."""
    x1, y1, x2, y2 = box

    if fill is not None:
        draw.rectangle(box, fill=fill)

    def dashed_line(xa, ya, xb, yb):
        if xa == xb:
            length = abs(yb - ya)
            direction = 1 if yb >= ya else -1
            pos = 0

            while pos < length:
                end = min(pos + dash, length)

                draw.line(
                    (
                        xa,
                        ya + direction * pos,
                        xb,
                        ya + direction * end
                    ),
                    fill=outline,
                    width=width
                )

                pos += dash + gap

        else:
            length = abs(xb - xa)
            direction = 1 if xb >= xa else -1
            pos = 0

            while pos < length:
                end = min(pos + dash, length)

                draw.line(
                    (
                        xa + direction * pos,
                        ya,
                        xa + direction * end,
                        yb
                    ),
                    fill=outline,
                    width=width
                )

                pos += dash + gap

    dashed_line(x1, y1, x2, y1)
    dashed_line(x1, y2, x2, y2)
    dashed_line(x1, y1, x1, y2)
    dashed_line(x2, y1, x2, y2)

def render_table(
    title,
    columns,
    rows,
    output_path,
    *,
    name_columns=1,
    revenue=False,
    mobile=True,
    total_row=False,
):
    if not rows:
        return

    # Image is intentionally wide enough for desktop but compressed enough
    # that the report remains legible when opened on a phone.
    if len(columns) >= 13:
        widths = [
            175, 210,
            105, 105, 105, 90, 105,
            105, 105, 105, 105, 105, 105
        ]
    elif len(columns) == 12:
        widths = [
            190,
            105, 105, 105, 95, 105, 105, 105,
            105, 105, 105, 105
        ]
    elif len(columns) == 8:
        widths = [170, 205, 105, 105, 95, 90, 90, 100]
    else:
        widths = [220, 105, 105, 95, 90, 90, 100]

    margin = 24
    title_height = 76
    header_height = 76
    row_height = 58

    image_width = sum(widths) + margin * 2
    image_height = (
        margin
        + title_height
        + header_height
        + row_height * len(rows)
        + margin
    )

    image = Image.new("RGB", (image_width, image_height), "white")
    draw = ImageDraw.Draw(image)

    title_font = font(29, True)
    header_font = font(16, True)
    body_font = font(16, False)
    total_font = font(16, True)

    # Main title
    draw.rectangle(
        (
            margin,
            margin,
            image_width - margin,
            margin + title_height
        ),
        fill="#D8EAF5",
        outline="#777777",
        width=1,
    )

    draw_centered(
        draw,
        (
            margin,
            margin,
            image_width - margin,
            margin + title_height
        ),
        title,
        title_font,
    )

    y = margin + title_height

    # Column headers
    x = margin

    for index, column in enumerate(columns):
        draw.rectangle(
            (x, y, x + widths[index], y + header_height),
            fill="#FFF0C7",
            outline="#666666",
            width=1,
        )

        draw_centered(
            draw,
            (x, y, x + widths[index], y + header_height),
            column,
            header_font,
        )

        x += widths[index]

    y += header_height

    # Body
    for row_index, row in enumerate(rows):
        x = margin

        is_last_total = (
            total_row
            and row_index == len(rows) - 1
            and is_total(row)
        )

        fill = "#FFF0C7" if is_last_total else "white"
        current_font = total_font if is_last_total else body_font

        for column_index in range(len(columns)):
            value = (
                row[column_index]
                if column_index < len(row)
                else ""
            )

            draw.rectangle(
                (x, y, x + widths[column_index], y + row_height),
                fill=fill,
                outline="#777777",
                width=1,
            )

            wrapped = wrap_text(
                draw,
                value,
                current_font,
                widths[column_index] - 12
            )

            bbox = draw.multiline_textbbox(
                (0, 0),
                wrapped,
                font=current_font,
                spacing=2,
                align="center",
            )

            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            if column_index < name_columns:
                tx = x + 7
                align = "left"
            else:
                tx = x + (widths[column_index] - tw) / 2
                align = "center"

            ty = y + (row_height - th) / 2

            draw.multiline_text(
                (tx, ty),
                wrapped,
                font=current_font,
                fill="black",
                spacing=2,
                align=align,
            )

            x += widths[column_index]

        y += row_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)

def render_bdm_revenue_table(
    columns,
    rows,
    output_path,
    page_number,
    total_pages
):
    if not rows:
        return

    widths = [190, 220, 115, 115, 110, 100, 100, 105]

    margin = 18
    metric_title_height = 52
    header_height = 62
    row_height = 43

    image_width = sum(widths) + margin * 2

    image_height = (
        margin
        + metric_title_height
        + header_height
        + row_height * len(rows)
        + margin
    )

    image = Image.new(
        "RGB",
        (image_width, image_height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    body_font = font(20, False, times=True)
    body_bold_font = font(20, True, times=True)
    header_font = font(20, True, times=True)
    metric_font = font(20, True, times=True)

    # --------------------------------------------------------------
    # TOP 15 ACTUAL VALUES
    # --------------------------------------------------------------

    actual_values = []

    for i, row in enumerate(rows):
        n = number(row[3]) if len(row) > 3 else None

        if n is not None and n > 0:
            actual_values.append((n, i))

    actual_values.sort(reverse=True)

    top15_indexes = {
        i for _, i in actual_values[:15]
    }

    # --------------------------------------------------------------
    # ACHIEVEMENT COLOR
    # --------------------------------------------------------------

    def achievement_fill(value):

        n = number(value)

        if n is None:
            return "white"

        n = max(0.0, n)

        if n <= 50:
            t = min(1.0, n / 50.0)

            return (
                248,
                int(90 + 145 * t),
                90
            )

        t = min(
            1.0,
            (n - 50) / 50.0
        )

        return (
            int(248 - 120 * t),
            int(235 - 20 * t),
            int(90 + 100 * t)
        )

    # --------------------------------------------------------------
    # M MONTH METRICS
    # --------------------------------------------------------------

    x = margin

    for i, w in enumerate(widths):

        draw.rectangle(
            (
                x,
                margin,
                x + w,
                margin + metric_title_height
            ),
            fill="#FFF000" if i >= 2 else "white"
        )

        x += w

    draw_centered(
        draw,
        (
            margin + widths[0] + widths[1],
            margin,
            margin + sum(widths),
            margin + metric_title_height
        ),
        "M Month Metrics",
        metric_font
    )

    # --------------------------------------------------------------
    # COLUMN HEADERS
    # --------------------------------------------------------------

    y = margin + metric_title_height
    x = margin

    for i, column in enumerate(columns):

        draw.rectangle(
            (
                x,
                y,
                x + widths[i],
                y + header_height
            ),
            fill="#FFF8D6"
        )

        draw_dashed_rectangle(
            draw,
            (
                x,
                y,
                x + widths[i],
                y + header_height
            ),
            outline="black",
            width=1
        )

        draw_centered(
            draw,
            (
                x + 4,
                y + 2,
                x + widths[i] - 4,
                y + header_height - 2
            ),
            column,
            header_font
        )

        x += widths[i]

    y += header_height

    # --------------------------------------------------------------
    # BODY
    # --------------------------------------------------------------

    for row_index, row in enumerate(rows):

        x = margin

        for col_index in range(len(columns)):

            value = (
                row[col_index]
                if col_index < len(row)
                else ""
            )

            fill = "white"

            # Column D — Actual
            if (
                col_index == 3
                and row_index in top15_indexes
            ):
                fill = "#C6EFCE"

            # Column E — Achievement %
            elif col_index == 4:
                fill = achievement_fill(value)

            # Column F — FTD = 0
            elif col_index == 5:

                n = number(value)

                if n is not None and n == 0:
                    fill = "#F4CCCC"

            draw_dashed_rectangle(
                draw,
                (
                    x,
                    y,
                    x + widths[col_index],
                    y + row_height
                ),
                fill=fill,
                outline="black",
                width=1
            )

            # CH Name + BDM Name bold
            # Everything centered
            current_font = (
                body_bold_font
                if col_index in (0, 1)
                else body_font
            )

            draw_centered(
                draw,
                (
                    x + 5,
                    y + 2,
                    x + widths[col_index] - 5,
                    y + row_height - 2
                ),
                value,
                current_font
            )

            x += widths[col_index]

        y += row_height

    # --------------------------------------------------------------
    # PAGE NUMBER
    # --------------------------------------------------------------

    if total_pages > 1:

        footer_font = font(
            16,
            False,
            times=True
        )

        footer = f"{page_number} / {total_pages}"

        tw, th = text_size(
            draw,
            footer,
            footer_font
        )

        draw.text(
            (
                image_width - margin - tw,
                image_height - margin - th
            ),
            footer,
            font=footer_font,
            fill="black"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image.save(
        output_path,
        format="PNG",
        optimize=True
    )



# ======================================================================
# BDM LEADS — REFERENCE STYLE
# ======================================================================

def render_bdm_leads_table(
    columns,
    rows,
    output_path,
    page_number,
    total_pages
):
    if not rows:
        return

    widths = [
        175, 205, 105, 105, 105, 95, 105,
        100, 105, 100, 105, 100, 105
    ]

    margin = 16
    metric_title_height = 52
    header_height = 68
    row_height = 43

    image_width = sum(widths) + margin * 2

    image_height = (
        margin
        + metric_title_height
        + header_height
        + row_height * len(rows)
        + margin
    )

    image = Image.new(
        "RGB",
        (image_width, image_height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    body_font = font(20, False, times=True)
    body_bold_font = font(20, True, times=True)
    header_font = font(20, True, times=True)
    metric_font = font(20, True, times=True)

    # --------------------------------------------------------------
    # TOP 15 ACTUAL LEADS
    # --------------------------------------------------------------

    actual_values = []

    for i, row in enumerate(rows):
        n = number(row[3]) if len(row) > 3 else None

        if n is not None and n > 0:
            actual_values.append((n, i))

    actual_values.sort(reverse=True)

    top15_indexes = {
        i for _, i in actual_values[:15]
    }

    # --------------------------------------------------------------
    # ACHIEVEMENT COLOR
    # --------------------------------------------------------------

    def achievement_fill(value):

        n = number(value)

        if n is None:
            return "white"

        n = max(0.0, n)

        if n <= 50:
            t = min(1.0, n / 50.0)

            return (
                248,
                int(90 + 145 * t),
                90
            )

        t = min(
            1.0,
            (n - 50) / 50.0
        )

        return (
            int(248 - 120 * t),
            int(235 - 20 * t),
            int(90 + 100 * t)
        )

    # --------------------------------------------------------------
    # M MONTH METRICS
    # --------------------------------------------------------------

    x = margin

    for i, w in enumerate(widths):

        draw.rectangle(
            (
                x,
                margin,
                x + w,
                margin + metric_title_height
            ),
            fill="#FFF000" if i >= 2 else "white"
        )

        x += w

    draw_centered(
        draw,
        (
            margin + widths[0] + widths[1],
            margin,
            margin + sum(widths),
            margin + metric_title_height
        ),
        "M Month Metrics",
        metric_font
    )

    # --------------------------------------------------------------
    # COLUMN HEADERS
    # --------------------------------------------------------------

    y = margin + metric_title_height
    x = margin

    for i, column in enumerate(columns):

        draw.rectangle(
            (
                x,
                y,
                x + widths[i],
                y + header_height
            ),
            fill="#FFF8D6"
        )

        draw_dashed_rectangle(
            draw,
            (
                x,
                y,
                x + widths[i],
                y + header_height
            ),
            outline="black",
            width=1
        )

        draw_centered(
            draw,
            (
                x + 4,
                y + 2,
                x + widths[i] - 4,
                y + header_height - 2
            ),
            column,
            header_font
        )

        x += widths[i]

    y += header_height

    # --------------------------------------------------------------
    # BODY
    # --------------------------------------------------------------

    for row_index, row in enumerate(rows):

        x = margin

        for col_index in range(len(columns)):

            value = (
                row[col_index]
                if col_index < len(row)
                else ""
            )

            fill = "white"

            # Column D — Actual Leads, top 15
            if (
                col_index == 3
                and row_index in top15_indexes
            ):
                fill = "#C6EFCE"

            # Column E — Achievement %
            elif col_index == 4:
                fill = achievement_fill(value)

            # Column F — Signups = 0
            elif col_index == 5:

                n = number(value)

                if n is not None and n == 0:
                    fill = "#F4CCCC"

            draw_dashed_rectangle(
                draw,
                (
                    x,
                    y,
                    x + widths[col_index],
                    y + row_height
                ),
                fill=fill,
                outline="black",
                width=1
            )

            # CH Name + BDM Name bold
            # Everything centered
            current_font = (
                body_bold_font
                if col_index in (0, 1)
                else body_font
            )

            draw_centered(
                draw,
                (
                    x + 5,
                    y + 2,
                    x + widths[col_index] - 5,
                    y + row_height - 2
                ),
                value,
                current_font
            )

            x += widths[col_index]

        y += row_height

    # --------------------------------------------------------------
    # PAGE NUMBER
    # --------------------------------------------------------------

    if total_pages > 1:

        footer_font = font(
            16,
            False,
            times=True
        )

        footer = f"{page_number} / {total_pages}"

        tw, th = text_size(
            draw,
            footer,
            footer_font
        )

        draw.text(
            (
                image_width - margin - tw,
                image_height - margin - th
            ),
            footer,
            font=footer_font,
            fill="black"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image.save(
        output_path,
        format="PNG",
        optimize=True
    )


# ======================================================================
# DATA NORMALISATION
# ======================================================================

def normalise(raw):
    result = dict(raw)

    for key in (
        "ch_leads",
        "ch_revenue",
        "bdm_leads",
        "bdm_revenue",
    ):
        value = result.get(key)

        if isinstance(value, str):
            result[key] = parse_tsv(value)

    return result


def validate_shape(raw):
    expected = {
        "ch_leads": 12,
        "ch_revenue": 7,
        "bdm_leads": 13,
        "bdm_revenue": 8,
    }

    for key, columns in expected.items():
        rows = raw.get(key)

        if not rows:
            raise RuntimeError(f"Missing dataset: {key}")

        for row_number, row in enumerate(rows, 1):
            if len(row) != columns:
                raise RuntimeError(
                    f"{key}: row {row_number} has {len(row)} columns; "
                    f"expected {columns}"
                )


# ======================================================================
# WHATSAPP NUMBER OUTPUT
# ======================================================================

def build_whatsapp_text(raw):
    revenue = ["REVENUE — OUTPUT", ""]

    # CH revenue: row 1 hard header, row 2 column header,
    # rows 3+ data + total.
    ch_rev = raw["ch_revenue"]
    revenue.append("CH LEVEL")

    for row in ch_rev[2:]:
        if any(clean(x) for x in row):
            revenue.append(
                " | ".join(format_revenue_row(row, bdm=False))
            )

    revenue.append("")
    revenue.append("BDM LEVEL")

    # BDM revenue: row 1 hard header, row 2 column header,
    # rows 3+ data.
    for row in raw["bdm_revenue"][2:]:
        if any(clean(x) for x in row):
            revenue.append(
                " | ".join(format_revenue_row(row, bdm=True))
            )

    leads = ["LEADS — INPUT", ""]

    leads.append("CH LEVEL")
    for row in raw["ch_leads"][2:]:
        if any(clean(x) for x in row):
            leads.append(
                " | ".join(format_lead_row(row, bdm=False))
            )

    leads.append("")
    leads.append("BDM LEVEL")

    # BDM leads:
    # row 1 = hard header
    # row 2 = totals
    # row 3 = column headers
    # row 4+ = BDM data
    for row in raw["bdm_leads"][3:]:
        if any(clean(x) for x in row):
            leads.append(
                " | ".join(format_lead_row(row, bdm=True))
            )

    config.WHATSAPP_DIR.mkdir(parents=True, exist_ok=True)

    (config.WHATSAPP_DIR / "revenue_numbers.txt").write_text(
        "\n".join(revenue),
        encoding="utf-8",
    )

    (config.WHATSAPP_DIR / "leads_numbers.txt").write_text(
        "\n".join(leads),
        encoding="utf-8",
    )


# ======================================================================
# MAIN FORMATTER
# ======================================================================

def format_all(raw):
    raw = normalise(raw)
    validate_shape(raw)

    stamp = datetime.now().strftime("%d_%m_%y_%H_%M_%S")

    # Create run-specific folders so old reports are never accidentally
    # mixed with the current report.
    lead_run_dir = config.LEAD_SCREENSHOT_DIR / stamp
    revenue_run_dir = config.REVENUE_SCREENSHOT_DIR / stamp

    ch_lead_dir = lead_run_dir / "CH"
    bdm_lead_dir = lead_run_dir / "BDM"
    ch_rev_dir = revenue_run_dir / "CH"
    bdm_rev_dir = revenue_run_dir / "BDM"

    for directory in (
        ch_lead_dir,
        bdm_lead_dir,
        ch_rev_dir,
        bdm_rev_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    # CH REVENUE
    # --------------------------------------------------------------
    ch_rev_rows = rows_with_data(raw["ch_revenue"][2:])

    formatted_ch_rev = [
        format_revenue_row(row, bdm=False)
        for row in ch_rev_rows
    ]

    render_table(
        "CH REVENUE PERFORMANCE — M MONTH",
        CH_REVENUE_COLUMNS,
        formatted_ch_rev,
        ch_rev_dir / f"CH_revenue_overall_{stamp}.png",
        name_columns=1,
        revenue=True,
        total_row=True,
    )

    # --------------------------------------------------------------
    # BDM REVENUE
    # --------------------------------------------------------------
    bdm_rev_rows = rows_with_data(raw["bdm_revenue"][2:])
    bdm_rev_rows = [
        row for row in bdm_rev_rows
        if not is_total(row)
    ]

    formatted_bdm_rev = [
        format_revenue_row(row, bdm=True)
        for row in bdm_rev_rows
    ]

    # Deliberately dynamic.
        # BDM Revenue — maximum 2 images
    bdm_rev_image_count = min(
        2,
        max(
            1,
            math.ceil(
                len(formatted_bdm_rev) / 32
            )
        )
    )

    rows_per_image = math.ceil(
        len(formatted_bdm_rev)
        / bdm_rev_image_count
    )

    for image_index in range(
        bdm_rev_image_count
    ):

        start = (
            image_index
            * rows_per_image
        )

        end = start + rows_per_image

        chunk = formatted_bdm_rev[
            start:end
        ]

        number = image_index + 1

        render_bdm_revenue_table(
            BDM_REVENUE_COLUMNS,
            chunk,
            bdm_rev_dir
            / f"BDM_revenue_{number:02d}_{stamp}.png",
            page_number=number,
            total_pages=bdm_rev_image_count,
        )

    # --------------------------------------------------------------
    # CH LEADS
    # --------------------------------------------------------------
    ch_lead_rows = rows_with_data(raw["ch_leads"][2:])

    formatted_ch_leads = [
        format_lead_row(row, bdm=False)
        for row in ch_lead_rows
    ]

    render_table(
        "CH LEADS PERFORMANCE — M MONTH",
        CH_LEADS_COLUMNS,
        formatted_ch_leads,
        ch_lead_dir / f"CH_leads_overall_{stamp}.png",
        name_columns=1,
        total_row=True,
    )

    # --------------------------------------------------------------
    # BDM LEADS
    # --------------------------------------------------------------
    bdm_lead_rows = rows_with_data(raw["bdm_leads"][3:])
    bdm_lead_rows = [
        row for row in bdm_lead_rows
        if not is_total(row)
    ]

    formatted_bdm_leads = [
        format_lead_row(row, bdm=True)
        for row in bdm_lead_rows
    ]

    # BDM Leads — maximum 2 images.
    bdm_lead_image_count = min(
        2,
        max(
            1,
            math.ceil(
                len(formatted_bdm_leads) / 32
            )
        )
    )

    rows_per_lead_image = math.ceil(
        len(formatted_bdm_leads)
        / bdm_lead_image_count
    )

    for image_index in range(
        bdm_lead_image_count
    ):

        start = (
            image_index
            * rows_per_lead_image
        )

        end = (
            start
            + rows_per_lead_image
        )

        chunk = formatted_bdm_leads[
            start:end
        ]

        number = image_index + 1

        render_bdm_leads_table(
            BDM_LEADS_COLUMNS,
            chunk,
            bdm_lead_dir
            / f"BDM_leads_{number:02d}_{stamp}.png",
            page_number=number,
            total_pages=bdm_lead_image_count,
        )

    # --------------------------------------------------------------
    # WHATSAPP NUMBERS
    # --------------------------------------------------------------
    build_whatsapp_text(raw)

    return {
        "timestamp": stamp,
        "lead_dir": str(lead_run_dir),
        "revenue_dir": str(revenue_run_dir),
        "whatsapp_dir": str(config.WHATSAPP_DIR),
        "bdm_revenue_images": bdm_rev_image_count,
        "bdm_lead_images": bdm_lead_image_count,
    }


# ======================================================================
# MANUAL PASTE TEST
# ======================================================================

if __name__ == "__main__":
    manual_raw = {
        "ch_leads": RAW_CH_LEADS,
        "ch_revenue": RAW_CH_REVENUE,
        "bdm_leads": RAW_BDM_LEADS,
        "bdm_revenue": RAW_BDM_REVENUE,
    }

    if not any(v.strip() for v in manual_raw.values()):
        print("No manual TSV data pasted.")
        print("This file is normally called by the production runner.")
        raise SystemExit(0)

    print("=" * 78)
    print("AUTOMATION DASHBOARD — STEP 4 FORMATTER")
    print("=" * 78)

    outputs = format_all(manual_raw)

    print("\n✓ STEP 4 FORMATTER PASSED")
    for key, value in outputs.items():
        print(f"{key}: {value}")
