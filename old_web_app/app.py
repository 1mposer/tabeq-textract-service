#!/usr/bin/env python3
"""
Receipt Processor Web Interface
Beautiful, elegant web app for processing receipt images
"""

import os
import json
import csv
import io
import zipfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from textractprettyprinter.t_pretty_print_expense import get_string
from textractprettyprinter.t_pretty_print_expense import Textract_Expense_Pretty_Print, Pretty_Print_Table_Format

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configuration
UPLOAD_FOLDER = 'web_uploads'
OUTPUT_FOLDER = 'web_output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff', 'tif', 'pdf'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_mock_textract_response(filename):
    """Create mock textract response with varied data for demo"""
    vendors = [
        "COFFEE SHOP DOWNTOWN", "WALMART SUPERCENTER", "TARGET STORE",
        "STARBUCKS COFFEE", "AMAZON.COM", "BEST BUY"
    ]
    items = [
        [("Large Coffee", "$4.50"), ("Blueberry Muffin", "$3.25")],
        [("Groceries", "$45.67"), ("Milk", "$3.99"), ("Bread", "$2.49")],
        [("Office Supplies", "$23.45"), ("Notebook", "$5.99")],
        [("Cappuccino", "$5.25"), ("Croissant", "$4.75")],
        [("Electronics", "$129.99"), ("USB Cable", "$12.99")],
        [("Software", "$89.99")]
    ]

    # Use filename to create some variation
    vendor_idx = hash(filename) % len(vendors)
    items_idx = hash(filename) % len(items)

    selected_vendor = vendors[vendor_idx]
    selected_items = items[items_idx]

    # Calculate total
    total = sum(float(price.replace('$', '')) for _, price in selected_items)

    line_items = []
    for item_name, item_price in selected_items:
        line_items.append({
            "LineItemExpenseFields": [
                {
                    "Type": {"Text": "ITEM", "Confidence": 99.5},
                    "ValueDetection": {"Text": item_name, "Confidence": 99.5}
                },
                {
                    "Type": {"Text": "PRICE", "Confidence": 99.8},
                    "ValueDetection": {"Text": item_price, "Confidence": 99.8}
                }
            ]
        })

    return {
        "DocumentMetadata": {"Pages": 1},
        "ExpenseDocuments": [{
            "ExpenseIndex": 1,
            "SummaryFields": [
                {
                    "Type": {"Text": "VENDOR_NAME", "Confidence": 99.84},
                    "ValueDetection": {
                        "Text": selected_vendor,
                        "Confidence": 99.84,
                        "Geometry": {
                            "BoundingBox": {"Width": 0.3, "Height": 0.05, "Left": 0.35, "Top": 0.1},
                            "Polygon": [{"X": 0.35, "Y": 0.1}, {"X": 0.65, "Y": 0.1},
                                      {"X": 0.65, "Y": 0.15}, {"X": 0.35, "Y": 0.15}]
                        }
                    }
                },
                {
                    "Type": {"Text": "TOTAL", "Confidence": 99.91},
                    "ValueDetection": {
                        "Text": f"${total:.2f}",
                        "Confidence": 99.91,
                        "Geometry": {
                            "BoundingBox": {"Width": 0.15, "Height": 0.04, "Left": 0.7, "Top": 0.8},
                            "Polygon": [{"X": 0.7, "Y": 0.8}, {"X": 0.85, "Y": 0.8},
                                      {"X": 0.85, "Y": 0.84}, {"X": 0.7, "Y": 0.84}]
                        }
                    }
                },
                {
                    "Type": {"Text": "INVOICE_RECEIPT_DATE", "Confidence": 95.12},
                    "ValueDetection": {
                        "Text": datetime.now().strftime("%Y-%m-%d"),
                        "Confidence": 95.12,
                        "Geometry": {
                            "BoundingBox": {"Width": 0.2, "Height": 0.04, "Left": 0.4, "Top": 0.15},
                            "Polygon": [{"X": 0.4, "Y": 0.15}, {"X": 0.6, "Y": 0.15},
                                      {"X": 0.6, "Y": 0.19}, {"X": 0.4, "Y": 0.19}]
                        }
                    }
                }
            ],
            "LineItemGroups": [{"LineItemGroupIndex": 1, "LineItems": line_items}]
        }]
    }

def process_receipt_file(file_path, filename):
    """Process a single receipt file"""
    try:
        # Create mock response (in real implementation, would call Textract)
        mock_response = create_mock_textract_response(filename)

        # Pretty print the response
        pretty_printed_string = get_string(
            textract_json=mock_response,
            output_type=[
                Textract_Expense_Pretty_Print.SUMMARY,
                Textract_Expense_Pretty_Print.LINEITEMGROUPS
            ],
            table_format=Pretty_Print_Table_Format.fancy_grid
        )

        # Save outputs
        base_name = os.path.splitext(filename)[0]

        # Save pretty printed text
        txt_file = os.path.join(OUTPUT_FOLDER, f"{base_name}-response.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Receipt processed at: {datetime.now().isoformat()}\n")
            f.write(f"Input file: {filename}\n")
            f.write("=" * 50 + "\n\n")
            f.write(pretty_printed_string)

        # Save raw JSON
        json_file = os.path.join(OUTPUT_FOLDER, f"{base_name}-raw.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(mock_response, f, indent=2)

        return {
            'success': True,
            'filename': filename,
            'txt_file': txt_file,
            'json_file': json_file,
            'mock_response': mock_response
        }

    except Exception as e:
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    results = []

    for file in files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"

            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

            # Process the file
            result = process_receipt_file(file_path, filename)
            results.append(result)

    return jsonify({
        'success': True,
        'results': results,
        'total_processed': len([r for r in results if r['success']])
    })

@app.route('/download-csv')
def download_csv():
    try:
        # Generate CSV from all processed files
        json_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith('-raw.json')]

        if not json_files:
            return jsonify({'error': 'No processed files found'}), 404

        # Create a ZIP file containing both CSV formats
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Summary CSV
            summary_csv = io.StringIO()
            summary_writer = csv.writer(summary_csv)
            summary_writer.writerow(['filename', 'vendor_name', 'total', 'date', 'item_count', 'processed_at'])

            # Detailed CSV
            detailed_csv = io.StringIO()
            detailed_writer = csv.writer(detailed_csv)
            detailed_writer.writerow(['filename', 'vendor_name', 'receipt_total', 'receipt_date',
                                    'item_name', 'item_price', 'processed_at'])

            for json_file in json_files:
                json_path = os.path.join(OUTPUT_FOLDER, json_file)
                with open(json_path, 'r') as f:
                    data = json.load(f)

                # Extract data
                filename = json_file.replace('-raw.json', '')
                vendor_name = ''
                total = ''
                date = ''
                items = []
                processed_at = datetime.now().isoformat()

                for expense_doc in data.get('ExpenseDocuments', []):
                    for field in expense_doc.get('SummaryFields', []):
                        field_type = field.get('Type', {}).get('Text', '')
                        field_value = field.get('ValueDetection', {}).get('Text', '')

                        if field_type == 'VENDOR_NAME':
                            vendor_name = field_value
                        elif field_type == 'TOTAL':
                            total = field_value
                        elif field_type == 'INVOICE_RECEIPT_DATE':
                            date = field_value

                    # Extract line items
                    for line_group in expense_doc.get('LineItemGroups', []):
                        for line_item in line_group.get('LineItems', []):
                            item_name = ''
                            item_price = ''

                            for field in line_item.get('LineItemExpenseFields', []):
                                field_type = field.get('Type', {}).get('Text', '')
                                field_value = field.get('ValueDetection', {}).get('Text', '')

                                if field_type == 'ITEM':
                                    item_name = field_value
                                elif field_type == 'PRICE':
                                    item_price = field_value

                            if item_name or item_price:
                                items.append({'item': item_name, 'price': item_price})

                # Write to summary CSV
                summary_writer.writerow([filename, vendor_name, total, date, len(items), processed_at])

                # Write to detailed CSV
                if items:
                    for item in items:
                        detailed_writer.writerow([filename, vendor_name, total, date,
                                                item['item'], item['price'], processed_at])
                else:
                    detailed_writer.writerow([filename, vendor_name, total, date, '', '', processed_at])

            # Add CSVs to ZIP
            zf.writestr('receipt_summary.csv', summary_csv.getvalue())
            zf.writestr('receipt_details.csv', detailed_csv.getvalue())

        memory_file.seek(0)

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'receipt_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear')
def clear_files():
    try:
        # Clear upload and output folders
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        return jsonify({'success': True, 'message': 'All files cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)