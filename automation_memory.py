"""
OVERALL RUNNER — NO JSON VERSION

Flow:
Google Sheets -> clipboard -> Python memory -> formatter -> PNG/text
No intermediate JSON, no input_formatter.py, no schema adapter.
This is the recommended production version.
"""

from google_layer import extract_all
from report_formatter import format_all

def main():
    print("=" * 78)
    print("AUTOMATION DASHBOARD — DIRECT MEMORY PIPELINE")
    print("=" * 78)

    raw = extract_all()
    outputs = format_all(raw)

    print("\n✓ Direct-memory pipeline completed.")
    print(f"Generated files: {outputs}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
