#!/usr/bin/env python3
"""
CSV Writer for Receipt Processing
Manages CSV file creation and safe appending of receipt data
"""

import csv
import os
from datetime import datetime
from typing import List, Dict
import fcntl
from pathlib import Path


def write_csv(rows: List[Dict], out_path: str) -> None:
    """
    Write receipt data rows to CSV file, creating headers if needed

    Args:
        rows: List of dictionaries containing receipt data
        out_path: Output CSV file path

    Headers:
        date, start_time, end_time, total, source_file, processed_at

    The function:
        - Creates output directory if it doesn't exist
        - Creates CSV file with headers if it doesn't exist
        - Appends rows safely with file locking
        - Adds processed_at timestamp automatically
    """
    # Define CSV headers
    headers = ['date', 'start_time', 'end_time', 'total', 'source_file', 'processed_at']

    # Create output directory if it doesn't exist
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(out_path)

    # Add processed_at timestamp to each row if not present
    for row in rows:
        if 'processed_at' not in row or not row['processed_at']:
            row['processed_at'] = datetime.now().isoformat()

    # Open file in append mode with UTF-8 encoding
    with open(out_path, 'a', newline='', encoding='utf-8') as csvfile:
        try:
            # Get exclusive lock for thread-safe writing
            fcntl.flock(csvfile.fileno(), fcntl.LOCK_EX)

            writer = csv.DictWriter(csvfile, fieldnames=headers)

            # Write headers if this is a new file
            if not file_exists:
                writer.writeheader()

            # Write data rows
            for row in rows:
                # Ensure all required fields are present (use None for missing)
                clean_row = {}
                for header in headers:
                    clean_row[header] = row.get(header, None)

                writer.writerow(clean_row)

        finally:
            # Release lock
            fcntl.flock(csvfile.fileno(), fcntl.LOCK_UN)


def read_csv(csv_path: str) -> List[Dict]:
    """
    Read existing CSV data (utility function for testing/verification)

    Args:
        csv_path: Path to CSV file

    Returns:
        List of dictionaries with CSV data
    """
    if not os.path.exists(csv_path):
        return []

    rows = []
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)

    return rows


if __name__ == "__main__":
    # Test module directly
    print("CSV Writer Module Test")
    print("-" * 40)

    # Test data
    test_rows = [
        {
            'date': '2024-01-15',
            'start_time': '10:30 AM',
            'end_time': '11:15 AM',
            'total': '125.50',
            'source_file': 'test_receipt.jpg',
            'processed_at': None  # Will be auto-filled
        },
        {
            'date': '2024-01-16',
            'start_time': '14:00',
            'end_time': '15:30',
            'total': '89.75',
            'source_file': 'receipt2.jpg'
            # processed_at will be auto-added
        }
    ]

    # Test file path
    test_path = "output/test_receipts.csv"

    # Write test data
    print(f"Writing {len(test_rows)} rows to {test_path}")
    write_csv(test_rows, test_path)
    print("Done!")

    # Verify by reading back
    print("\nReading back CSV:")
    saved_rows = read_csv(test_path)
    for row in saved_rows:
        print(row)