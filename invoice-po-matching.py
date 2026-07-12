#!/usr/bin/env python3
"""
Invoice vs PO Matching Automation

This script automates the matching of invoices against purchase orders (POs).
It reads POs from a CSV file, extracts data from invoice PDFs and text files,
matches each invoice to its corresponding PO, and generates a PDF report
with the results. The report is then emailed as an attachment.

Key Features:
- OCR support for scanned image-based PDFs
- Matches invoices to POs by PO number, vendor, and amount
- Categorizes results: Matched, Mismatch, No PO, PO Not Found
- Generates formatted PDF report with tables
- Sends email with PDF attachment

Author: Shezad Dev
GitHub: github.com/shezad-dev
"""

# ============ IMPORT LIBRARIES ============
import os          # For file and folder operations
import re          # For pattern matching in text (regex)
import csv         # For reading CSV files
import smtplib     # For sending emails
from email.mime.text import MIMEText          # For email body
from email.mime.multipart import MIMEMultipart # For email with attachments
from email.mime.base import MIMEBase          # For attaching files
from email import encoders                    # For encoding attachments
from datetime import datetime                 # For timestamps
from fpdf import FPDF                         # For generating PDF reports

# ============ CONFIGURATION ============
# Replace these with your own values

# Folder paths on your phone's storage
INVOICE_FOLDER = "/storage/emulated/0/Invoices/incoming/"    # Where new invoices go
PROCESSED_FOLDER = "/storage/emulated/0/Invoices/processed/" # After processing
FAILED_FOLDER = "/storage/emulated/0/Invoices/failed/"       # If extraction fails
MATCHED_FOLDER = "/storage/emulated/0/Invoices/matched/"     # Perfect matches
MISMATCH_FOLDER = "/storage/emulated/0/Invoices/mismatch/"   # Mismatches found
PO_CSV = "/storage/emulated/0/Invoices/pos.csv"              # PO data file

# Email credentials - REPLACE THESE WITH YOUR OWN
GMAIL_USER = "your_email@gmail.com"           # Your email address
GMAIL_PASSWORD = "your_app_password"          # App password (not regular password)
ALERT_EMAIL = "manager@company.com"           # Where the report is sent

# ============ FUNCTION 1: EXTRACT TEXT FROM PDF ============
def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file.
    
    LOGIC:
    1. First tries PyPDF2 - this works for text-based PDFs (normal PDFs)
    2. If PyPDF2 fails or returns no text, tries OCR (Tesseract)
    3. OCR converts the PDF pages to images and reads text from them
    4. This handles scanned/image-based PDFs that have no selectable text
    
    ARGUMENTS:
        pdf_path: Full path to the PDF file
    
    RETURNS:
        Extracted text as a string, or empty string if nothing found
    """
    text = ""
    
    # LOGIC: Step 1 - Try PyPDF2 for text-based PDFs
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text += page_text
        if text.strip():
            return text  # If we got text, return it
    except Exception as e:
        print(f"PyPDF2 error: {e}")
    
    # LOGIC: Step 2 - If PyPDF2 failed, try OCR for scanned PDFs
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image
        
        print("   Using OCR for scanned PDF...")
        # LOGIC: Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=200)
        # LOGIC: Use Tesseract to read text from each image
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"OCR error: {e}")
    
    return ""  # Return empty if nothing worked

# ============ FUNCTION 2: READ POS FROM CSV ============
def read_pos():
    """
    Reads Purchase Orders from a CSV file.
    
    LOGIC:
    1. Opens the CSV file at PO_CSV path
    2. Reads each row using csv.DictReader
    3. Extracts PO Number, Vendor, Amount, Date, Status, Description
    4. Builds a dictionary (lookup map) with PO Number as the key
    
    ARGUMENTS:
        None (uses global PO_CSV)
    
    RETURNS:
        Dictionary: {PO_Number: {vendor, amount, date, status, description}}
        Returns None if file can't be read
    """
    pos_map = {}
    try:
        with open(PO_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                po_num = row.get('PO_Number', '').strip()
                if po_num:
                    pos_map[po_num] = {
                        'vendor': row.get('Vendor', '').strip(),
                        'amount': float(row.get('Amount', 0)),
                        'date': row.get('Date', '').strip(),
                        'status': row.get('Status', '').strip(),
                        'description': row.get('Description', '').strip()
                    }
        return pos_map
    except Exception as e:
        print(f"Error reading PO CSV: {e}")
        return None

# ============ FUNCTION 3: EXTRACT INVOICE DATA ============
def extract_invoice_data(text):
    """
    Extracts key fields from invoice text using regex patterns.
    
    LOGIC:
    1. Searches for Invoice Number using patterns like "Invoice #: INV-001"
    2. Searches for PO Number using patterns like "PO Number: PO-00001"
    3. Searches for Vendor name
    4. Searches for Amount (with $ sign or without)
    5. Searches for Date in YYYY-MM-DD format
    
    ARGUMENTS:
        text: Raw text extracted from the invoice
    
    RETURNS:
        Dictionary: {invoice_number, po_number, vendor, amount, date}
    """
    data = {
        'invoice_number': '',
        'po_number': '',
        'vendor': '',
        'amount': 0,
        'date': ''
    }
    
    if not text:
        return data
    
    # LOGIC: Extract Invoice Number
    match = re.search(r'Invoice\s*#?\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
    if match:
        data['invoice_number'] = match.group(1).strip()
    
    # LOGIC: Extract PO Number
    match = re.search(r'PO\s*Number\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
    if match:
        data['po_number'] = match.group(1).strip()
    
    # LOGIC: Extract Vendor
    match = re.search(r'Vendor\s*:?\s*([^\n]+)', text, re.IGNORECASE)
    if match:
        data['vendor'] = match.group(1).strip()
    
    # LOGIC: Extract Amount
    match = re.search(r'Amount\s*:?\s*[$£€]?\s*([0-9,]+\.?[0-9]{0,2})', text, re.IGNORECASE)
    if match:
        try:
            data['amount'] = float(match.group(1).replace(',', ''))
        except:
            pass
    
    # LOGIC: Extract Date
    match = re.search(r'Date\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if match:
        data['date'] = match.group(1).strip()
    
    return data

# ============ FUNCTION 4: MATCH INVOICE TO PO ============
def match_invoice(invoice_data, pos_map):
    """
    Matches an invoice to a PO by comparing fields.
    
    LOGIC:
    1. If no PO number, return "NO_PO"
    2. If PO number not in pos_map, return "PO_NOT_FOUND"
    3. If vendor doesn't match, return "VENDOR_MISMATCH"
    4. If amount doesn't match (diff > 0.01), return "AMOUNT_MISMATCH"
    5. If all match, return "MATCHED"
    
    ARGUMENTS:
        invoice_data: Dictionary from extract_invoice_data()
        pos_map: Dictionary from read_pos()
    
    RETURNS:
        result: String (MATCHED, NO_PO, PO_NOT_FOUND, VENDOR_MISMATCH, AMOUNT_MISMATCH)
        notes: String with details about the match
    """
    po_num = invoice_data['po_number']
    
    # LOGIC: No PO number found in invoice
    if not po_num:
        return "NO_PO", "No PO number found"
    
    # LOGIC: PO number exists but not in our PO list
    if po_num not in pos_map:
        return "PO_NOT_FOUND", f"PO {po_num} not found"
    
    # LOGIC: PO exists, get its data
    po = pos_map[po_num]
    
    # LOGIC: Check if vendor matches
    if invoice_data['vendor'] and po['vendor']:
        if invoice_data['vendor'].lower() != po['vendor'].lower():
            return "VENDOR_MISMATCH", f"Vendor: PO {po['vendor']} vs Invoice {invoice_data['vendor']}"
    
    # LOGIC: Check if amount matches (allow 1 cent difference)
    if invoice_data['amount'] and po['amount']:
        if abs(invoice_data['amount'] - po['amount']) > 0.01:
            return "AMOUNT_MISMATCH", f"Amount: PO ${po['amount']:.2f} vs Invoice ${invoice_data['amount']:.2f}"
    
    # LOGIC: Everything matches
    return "MATCHED", "All match"

# ============ FUNCTION 5: GENERATE PDF REPORT ============
def generate_pdf_report(matched, mismatched, no_po, po_not_found, mismatch_details):
    """
    Creates a formatted PDF report with tables.
    
    LOGIC:
    1. Create a new PDF document
    2. Add title and timestamp
    3. Create a SUMMARY table with counts
    4. Create MISMATCHES table with details
    5. Create NO PO table
    6. Create PO NOT FOUND table
    7. Add footer
    8. Save the PDF to file
    
    ARGUMENTS:
        matched: List of matched invoice filenames
        mismatched: List of mismatched invoice filenames
        no_po: List of invoices with no PO number
        po_not_found: List of invoices with PO not found
        mismatch_details: List of mismatch details
    
    RETURNS:
        pdf_path: Path to the generated PDF file
    """
    pdf = FPDF()
    pdf.add_page()
    
    # LOGIC: Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(200, 12, "INVOICE vs PO MATCHING REPORT", ln=True, align="C")
    pdf.ln(4)
    
    # LOGIC: Date
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(200, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(8)
    
    # LOGIC: Divider line
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ===== SUMMARY TABLE =====
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(200, 10, "SUMMARY", ln=True)
    pdf.ln(4)
    
    # LOGIC: Table headers
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(70, 10, "Category", border=1, fill=True)
    pdf.cell(50, 10, "Count", border=1, fill=True, ln=True)
    
    # LOGIC: Table rows
    pdf.set_font("Helvetica", "", 11)
    rows = [
        ("Matched", len(matched)),
        ("Mismatch", len(mismatched)),
        ("No PO", len(no_po)),
        ("PO Not Found", len(po_not_found))
    ]
    
    for label, value in rows:
        pdf.cell(70, 8, label, border=1)
        pdf.cell(50, 8, str(value), border=1, ln=True)
    
    pdf.ln(8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # ===== MISMATCHES TABLE =====
    if mismatched:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(200, 10, "MISMATCHES", ln=True)
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(50, 8, "File", border=1, fill=True)
        pdf.cell(140, 8, "Issue", border=1, fill=True, ln=True)
        
        pdf.set_font("Helvetica", "", 9)
        for item in mismatch_details:
            parts = item.split(" | ", 1)
            filename = parts[0] if len(parts) > 0 else ""
            issue = parts[1] if len(parts) > 1 else item
            pdf.cell(50, 6, filename[:30], border=1)
            pdf.cell(140, 6, issue[:60], border=1, ln=True)
        
        pdf.ln(4)
    
    # ===== NO PO TABLE =====
    if no_po:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(200, 10, "NO PO NUMBER", ln=True)
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(50, 8, "File", border=1, fill=True)
        pdf.cell(140, 8, "Issue", border=1, fill=True, ln=True)
        
        pdf.set_font("Helvetica", "", 9)
        for item in no_po:
            pdf.cell(50, 6, item[:30], border=1)
            pdf.cell(140, 6, "No PO number found", border=1, ln=True)
        
        pdf.ln(4)
    
    # ===== PO NOT FOUND TABLE =====
    if po_not_found:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(200, 10, "PO NOT FOUND", ln=True)
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(50, 8, "File", border=1, fill=True)
        pdf.cell(140, 8, "PO", border=1, fill=True, ln=True)
        
        pdf.set_font("Helvetica", "", 9)
        for item in po_not_found:
            pdf.cell(50, 6, item[:30], border=1)
            pdf.cell(140, 6, "PO not in system", border=1, ln=True)
        
        pdf.ln(4)
    
    # ===== FOOTER =====
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(2)
    pdf.cell(200, 8, "This is an automated reconciliation report.", align="C")
    
    # LOGIC: Save the PDF
    pdf_filename = "/storage/emulated/0/Invoices/match_report.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

# ============ FUNCTION 6: SEND EMAIL WITH PDF ============
def send_email_with_pdf(subject, body, pdf_path):
    """
    Sends an email with a PDF attachment.
    
    LOGIC:
    1. Create email with subject, from, to, and body
    2. Attach the PDF file
    3. Connect to Gmail SMTP server
    4. Login and send the email
    5. Close the connection
    
    ARGUMENTS:
        subject: Email subject line
        body: Email body text
        pdf_path: Path to PDF file to attach
    
    RETURNS:
        True if successful, False otherwise
    """
    try:
        # LOGIC: Create email
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # LOGIC: Attach PDF
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'pdf')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="match_report.pdf"')
            msg.attach(part)
        
        # LOGIC: Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

# ============ MAIN FUNCTION ============
def main():
    """
    Main function - runs the entire matching process.
    
    LOGIC OVERVIEW:
    1. Read POs from CSV file
    2. Create folders if they don't exist
    3. Scan the incoming folder for invoices
    4. For each invoice:
       a. Extract text (using PyPDF2 or OCR)
       b. Extract invoice data (invoice #, PO #, vendor, amount, date)
       c. Match against POs
       d. Categorize the result
       e. Move the file to the appropriate folder
    5. Generate a PDF report with all results
    6. Send the report via email
    """
    print("\n" + "="*60)
    print("  INVOICE vs PO MATCHING (with OCR)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # LOGIC: Step 1 - Read POs
    print("Reading POs...")
    pos_map = read_pos()
    if not pos_map:
        print("No POs found. Check pos.csv")
        return
    print(f"{len(pos_map)} POs loaded\n")
    
    # LOGIC: Step 2 - Create folders if they don't exist
    for folder in [INVOICE_FOLDER, PROCESSED_FOLDER, FAILED_FOLDER, MATCHED_FOLDER, MISMATCH_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    
    # LOGIC: Step 3 - Scan incoming folder for invoices
    files = os.listdir(INVOICE_FOLDER)
    invoice_files = [f for f in files if f.lower().endswith(('.pdf', '.txt'))]
    
    if not invoice_files:
        print("No invoices found.")
        return
    
    print(f"{len(invoice_files)} invoices found\n")
    
    # LOGIC: Lists to store results
    matched = []
    mismatched = []
    no_po = []
    po_not_found = []
    mismatch_details = []
    
    # LOGIC: Step 4 - Process each invoice
    for filename in invoice_files:
        filepath = os.path.join(INVOICE_FOLDER, filename)
        print(f"Processing: {filename}")
        
        # LOGIC: Extract text from PDF or read from TXT
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        else:
            with open(filepath, 'r') as f:
                text = f.read()
        
        if not text:
            print("   No text extracted")
            os.rename(filepath, os.path.join(FAILED_FOLDER, filename))
            continue
        
        # LOGIC: Extract invoice data
        invoice_data = extract_invoice_data(text)
        print(f"   Invoice: {invoice_data['invoice_number']}")
        print(f"   PO: {invoice_data['po_number']}")
        print(f"   Amount: ${invoice_data['amount']:.2f}")
        
        # LOGIC: Match against POs
        result, notes = match_invoice(invoice_data, pos_map)
        print(f"   Result: {result}")
        print(f"   Notes: {notes}\n")
        
        # LOGIC: Move file to appropriate folder
        if result == "MATCHED":
            matched.append(filename)
            os.rename(filepath, os.path.join(MATCHED_FOLDER, filename))
        elif result in ["VENDOR_MISMATCH", "AMOUNT_MISMATCH"]:
            mismatched.append(filename)
            mismatch_details.append(f"{filename} | {notes}")
            os.rename(filepath, os.path.join(MISMATCH_FOLDER, filename))
        else:
            if result == "NO_PO":
                no_po.append(filename)
            elif result == "PO_NOT_FOUND":
                po_not_found.append(filename)
            os.rename(filepath, os.path.join(FAILED_FOLDER, filename))
    
    # LOGIC: Step 5 - Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Matched: {len(matched)}")
    print(f"Mismatch: {len(mismatched)}")
    print(f"No PO: {len(no_po)}")
    print(f"PO Not Found: {len(po_not_found)}")
    print("="*60 + "\n")
    
    # LOGIC: Step 6 - Generate PDF report
    print("Generating PDF report...")
    pdf_path = generate_pdf_report(matched, mismatched, no_po, po_not_found, mismatch_details)
    
    # LOGIC: Step 7 - Send email
    body = f"""
INVOICE vs PO MATCHING REPORT
==================================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
--------------------------------------------------
Matched: {len(matched)}
Mismatch: {len(mismatched)}
No PO: {len(no_po)}
PO Not Found: {len(po_not_found)}

PDF report attached.
"""
    
    print("Sending email with PDF attachment...")
    send_email_with_pdf(
        f"Invoice-PO Match Report: {len(mismatched)} issues",
        body,
        pdf_path
    )
    print("Email sent with PDF")
    print("\nDone.")

if __name__ == "__main__":
    main()
