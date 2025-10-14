#!/usr/bin/env python3
"""
CSV Generator for Receipt Processing
Converts processed receipt data to CSV format
"""

import csv
import json
import os
import glob
from datetime import datetime

def extract_data_from_json(json_file_path):
    """
    Extract relevant data from Textract JSON response
    """
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Initialize extracted data
    extracted = {
        'filename': os.path.basename(json_file_path).replace('-raw-response.json', ''),
        'vendor_name': '',
        'total': '',
        'date': '',
        'items': [],
        'processed_at': datetime.now().isoformat()
    }

    # Extract summary fields
    for expense_doc in data.get('ExpenseDocuments', []):
        for field in expense_doc.get('SummaryFields', []):
            field_type = field.get('Type', {}).get('Text', '')
            field_value = field.get('ValueDetection', {}).get('Text', '')

            if field_type == 'VENDOR_NAME':
                extracted['vendor_name'] = field_value
            elif field_type == 'TOTAL':
                extracted['total'] = field_value
            elif field_type == 'INVOICE_RECEIPT_DATE':
                extracted['date'] = field_value

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
                    extracted['items'].append({
                        'item': item_name,
                        'price': item_price
                    })

    return extracted

def generate_summary_csv(output_dir="output"):
    """
    Generate a summary CSV with one row per receipt
    """
    json_files = glob.glob(os.path.join(output_dir, "*-raw-response.json"))

    if not json_files:
        print("No JSON files found to process")
        return

    csv_file_path = os.path.join(output_dir, "receipt_summary.csv")

    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'vendor_name', 'total', 'date', 'item_count', 'processed_at']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for json_file in json_files:
            try:
                data = extract_data_from_json(json_file)
                writer.writerow({
                    'filename': data['filename'],
                    'vendor_name': data['vendor_name'],
                    'total': data['total'],
                    'date': data['date'],
                    'item_count': len(data['items']),
                    'processed_at': data['processed_at']
                })
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

    print(f"Summary CSV generated: {csv_file_path}")
    return csv_file_path

def generate_detailed_csv(output_dir="output"):
    """
    Generate a detailed CSV with one row per line item
    """
    json_files = glob.glob(os.path.join(output_dir, "*-raw-response.json"))

    if not json_files:
        print("No JSON files found to process")
        return

    csv_file_path = os.path.join(output_dir, "receipt_details.csv")

    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'vendor_name', 'receipt_total', 'receipt_date',
                     'item_name', 'item_price', 'processed_at']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for json_file in json_files:
            try:
                data = extract_data_from_json(json_file)

                # If there are line items, write one row per item
                if data['items']:
                    for item in data['items']:
                        writer.writerow({
                            'filename': data['filename'],
                            'vendor_name': data['vendor_name'],
                            'receipt_total': data['total'],
                            'receipt_date': data['date'],
                            'item_name': item['item'],
                            'item_price': item['price'],
                            'processed_at': data['processed_at']
                        })
                else:
                    # If no line items, write summary info only
                    writer.writerow({
                        'filename': data['filename'],
                        'vendor_name': data['vendor_name'],
                        'receipt_total': data['total'],
                        'receipt_date': data['date'],
                        'item_name': '',
                        'item_price': '',
                        'processed_at': data['processed_at']
                    })
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

    print(f"Detailed CSV generated: {csv_file_path}")
    return csv_file_path

def main():
    """Main function"""
    print("CSV Generator for Receipt Processing")
    print("=" * 40)

    # Generate both CSV formats
    summary_csv = generate_summary_csv()
    detailed_csv = generate_detailed_csv()

    print(f"\nCSV files generated:")
    if summary_csv:
        print(f"  - Summary: {summary_csv}")
    if detailed_csv:
        print(f"  - Detailed: {detailed_csv}")

if __name__ == "__main__":
    main()