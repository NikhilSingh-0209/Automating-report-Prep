from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SPREADSHEET_NAME = "All_Tracker@2026"
SPREADSHEET_ID = "1myaT67gYizzWf0Rz51rsRfLyfwQuY6ld-kSPFuh2GlI"
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

GOOGLE_PROFILE_DIR = BASE_DIR / "google_profile"
CHROME_PROFILE_DIR = BASE_DIR / "chrome_profile_wa"

SCREENSHOT_DIR = BASE_DIR / "screenshots"
LEAD_SCREENSHOT_DIR = SCREENSHOT_DIR / "leads"
REVENUE_SCREENSHOT_DIR = SCREENSHOT_DIR / "revenue"

WHATSAPP_DIR = BASE_DIR / "whatsapp_output"
INPUT_DIR = BASE_DIR / "input"

CH_LEADS = {
    "sheet": "Lead_tracker_CH",
    "range": "A1:L12",
    "rows": 12,
    "columns": 12,
}

CH_REVENUE = {
    "sheet": "Rev_tracker_CH",
    "range": "A1:G14",
    "rows": 14,
    "columns": 7,
}

BDM_LEADS = {
    "sheet": "Lead_tracker_BDM",
    "range": "A1:M67",
    "rows": 67,
    "columns": 13,
}

BDM_REVENUE = {
    "sheet": "Rev_tracker_BDM",
    "range": "A1:H68",
    "rows": 68,
    "columns": 8,
}

SOURCES = {
    "ch_leads": CH_LEADS,
    "ch_revenue": CH_REVENUE,
    "bdm_leads": BDM_LEADS,
    "bdm_revenue": BDM_REVENUE,
}

for p in (
    GOOGLE_PROFILE_DIR, CHROME_PROFILE_DIR,
    SCREENSHOT_DIR, LEAD_SCREENSHOT_DIR, REVENUE_SCREENSHOT_DIR,
    WHATSAPP_DIR, INPUT_DIR,
):
    p.mkdir(parents=True, exist_ok=True)
