STEP 4 — REPORT FORMATTER

Files:
  report_formatter.py
      Main formatter/image engine.

  step4_test.py
      Tests the formatter using the JSON snapshots already produced by
      google_extractor.py. This does NOT open Chrome.

Production:
  automation_memory.py
      Google -> memory -> formatter

JSON/debug:
  automation_json.py
      Google -> JSON -> formatter

IMPORTANT:
  Do not use input_formatter.py anymore.

STEP 4 TEST:

    python step4_test.py

This should generate:

    screenshots/
      leads/
        <timestamp>/
          CH/
          BDM/

      revenue/
        <timestamp>/
          CH/
          BDM/

and:

    whatsapp_output/
      leads_numbers.txt
      revenue_numbers.txt

Revenue display:
  Target, Actual, FTD, D-1 and MTD => exactly 2 decimals
  Ach% => exactly 2 decimals

Lead display:
  lead/signup counts => integers
  Ach% / Signups% => exactly 2 decimals

BDM:
  No hardcoded image count.
  BDM_ROWS_PER_IMAGE controls only readability.
  Number of images = ceil(actual BDM rows / BDM_ROWS_PER_IMAGE).

The next stage after this is WhatsApp distribution.
