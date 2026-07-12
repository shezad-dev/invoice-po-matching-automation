# Invoice vs PO Matching Automation

Automated matching of invoices against purchase orders with OCR support for scanned documents. Generates formatted PDF reports and sends them via email.

## Features

- Reads POs from CSV file
- Extracts invoice data from PDFs and TXT files
- OCR support for scanned/image-based PDFs
- Matches invoices to POs (vendor, amount, PO number)
- Flags mismatches (vendor mismatch, amount mismatch)
- Identifies missing PO numbers
- Generates formatted PDF report with tables
- Sends email with PDF attachment

## How It Works

```

1. POs loaded from pos.csv
2. Invoices scanned from incoming folder
3. Each invoice matched against POs
4. Results categorized:
   · Matched: All fields match
   · Mismatch: Vendor or amount mismatch
   · No PO: No PO number found
   · PO Not Found: PO doesn't exist
5. PDF report generated with tables
6. Email sent with PDF attachment

```

## Folder Structure

```

Invoices/
├── incoming/      # Place invoices here
├── matched/       # Matched invoices moved here
├── mismatch/      # Mismatched invoices moved here
├── failed/        # Failed invoices moved here
├── processed/     # Processed invoices
├── pos.csv        # Purchase Orders file
└── match_report.pdf  # Generated report

```

## Requirements

- Python 3
- PyPDF2
- fpdf2
- pdf2image
- pytesseract
- pillow

## Installation

```bash
pkg install tesseract poppler
python -m pip install PyPDF2 fpdf2 pdf2image pytesseract pillow
```

Configuration

Edit these variables in the script:

```python
INVOICE_FOLDER = "/storage/emulated/0/Invoices/incoming/"
PO_CSV = "/storage/emulated/0/Invoices/pos.csv"
GMAIL_USER = "your_email@gmail.com"
GMAIL_PASSWORD = "your_app_password"
ALERT_EMAIL = "manager@company.com"
```

POS CSV Format

```csv
PO_Number,Vendor,Amount,Date,Status,Description
PO-00001,Acme Corp,1200.50,2025-10-01,Open,Website Development
```

Invoice Format

```
Invoice #: INV-0001
PO Number: PO-00001
Vendor: Acme Corp
Amount: 1200.50
Date: 2025-10-05
```

Running the Script

```bash
python invoice_po_matcher.py
```

Output

· On Screen: Processing status and summary
· Email: Summary + PDF report attachment
· PDF: Formatted report with tables

PDF Report Example

```
======================================================================
              INVOICE vs PO MATCHING REPORT
              Generated: 2026-07-12 03:30:00
======================================================================

SUMMARY
============================================================
| Category       | Count |
|----------------|-------|
| Matched        | 27    |
| Mismatch       | 2     |
| No PO          | 1     |
| PO Not Found   | 0     |
============================================================

MISMATCHES
============================================================
| File              | Issue                               |
|-------------------|-------------------------------------|
| INV-0009.txt      | Amount: PO $2692.66 vs $2664.70     |
| INV-0037.txt      | Vendor: PO Theta vs Lambda          |
============================================================
```

Technologies

· Python 3
· PyPDF2 (PDF text extraction)
· pdf2image + pytesseract (OCR for scanned PDFs)
· fpdf2 (PDF report generation)
· Gmail SMTP (Email)

## Author

Shezad Dev

· GitHub: shezad-dev

License

MIT
