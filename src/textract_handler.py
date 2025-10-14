#!/usr/bin/env python3
"""
AWS Textract Handler for Receipt Processing
Handles image-to-text extraction and field parsing
"""

import boto3
import os
import re
from PIL import Image
from io import BytesIO
from typing import Dict, List, Optional


def extract_blocks(path: str) -> str:
    """
    Extract text blocks from a receipt image using AWS Textract

    Args:
        path: Path to the receipt image file

    Returns:
        Concatenated text lines from the receipt

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: For AWS Textract API errors
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image file not found: {path}")

    # Read image file
    with open(path, 'rb') as f:
        image_bytes = f.read()

    # Optionally preprocess image with Pillow if needed
    try:
        img = Image.open(BytesIO(image_bytes))
        # Convert to RGB if needed (removes alpha channel, handles different formats)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Convert back to bytes
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG')
        image_bytes = img_buffer.getvalue()
    except Exception as e:
        print(f"Warning: Could not preprocess image: {e}")
        # Continue with original bytes

    # Create Textract client
    # Check for region from environment (with fallback support)
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

    try:
        textract = boto3.client('textract', region_name=region)
    except Exception as e:
        raise Exception(f"Failed to create Textract client. Check AWS credentials: {e}")

    # Call Textract analyze_expense API
    try:
        response = textract.analyze_expense(
            Document={
                'Bytes': image_bytes
            }
        )
    except Exception as e:
        raise Exception(f"Textract API error: {e}")

    # Extract all text from the response
    all_text_lines = []

    # Extract from ExpenseDocuments
    for expense_doc in response.get('ExpenseDocuments', []):
        # Get summary fields
        for field in expense_doc.get('SummaryFields', []):
            if 'ValueDetection' in field:
                text = field['ValueDetection'].get('Text', '')
                if text:
                    all_text_lines.append(text)

        # Get line items
        for line_group in expense_doc.get('LineItemGroups', []):
            for line_item in line_group.get('LineItems', []):
                for field in line_item.get('LineItemExpenseFields', []):
                    if 'ValueDetection' in field:
                        text = field['ValueDetection'].get('Text', '')
                        if text:
                            all_text_lines.append(text)

    # Also extract from Blocks if available for more complete text
    for block in response.get('Blocks', []):
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '')
            if text and text not in all_text_lines:
                all_text_lines.append(text)

    # Return concatenated text
    return '\n'.join(all_text_lines)


def parse_fields(lines: str) -> Dict[str, Optional[str]]:
    """
    Parse specific fields from extracted receipt text using regex

    Args:
        lines: Concatenated text lines from receipt

    Returns:
        Dictionary with parsed fields: date, start_time, end_time, total
        Fields will be None if not found
    """
    fields = {
        'date': None,
        'start_time': None,
        'end_time': None,
        'total': None
    }

    # Parse date - multiple formats
    date_patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',  # MM-DD-YYYY or DD-MM-YYYY
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY-MM-DD
        r'\b(\d{1,2}\s+\w+\s+\d{4})\b',        # DD Month YYYY
        r'\b(\w+\s+\d{1,2},?\s+\d{4})\b',      # Month DD, YYYY
    ]

    for pattern in date_patterns:
        match = re.search(pattern, lines, re.IGNORECASE)
        if match:
            fields['date'] = match.group(1)
            break

    # Parse time - look for time ranges or individual times
    time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)'
    time_matches = re.findall(time_pattern, lines)

    if len(time_matches) >= 2:
        # Found at least two times, use first as start, second as end
        fields['start_time'] = time_matches[0]
        fields['end_time'] = time_matches[1]
    elif len(time_matches) == 1:
        # Only one time found, use it as start_time
        fields['start_time'] = time_matches[0]

    # Also check for explicit time range pattern
    time_range_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*[-to]+\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)'
    range_match = re.search(time_range_pattern, lines, re.IGNORECASE)
    if range_match:
        fields['start_time'] = range_match.group(1)
        fields['end_time'] = range_match.group(2)

    # Parse total amount - focus on AED currency
    total_patterns = [
        r'AED\s*([\d,]+\.?\d*)',                    # AED 123.45
        r'([\d,]+\.?\d*)\s*AED',                    # 123.45 AED
        r'TOTAL[:\s]+AED\s*([\d,]+\.?\d*)',         # TOTAL: AED 123.45
        r'TOTAL[:\s]+([\d,]+\.?\d*)',               # TOTAL: 123.45
        r'AMOUNT[:\s]+AED\s*([\d,]+\.?\d*)',        # AMOUNT: AED 123.45
        r'GRAND\s+TOTAL[:\s]+([\d,]+\.?\d*)',       # GRAND TOTAL: 123.45
        r'(?:TOTAL|AMOUNT|SUM)[:\s]*\$?([\d,]+\.?\d*)', # Generic total patterns
    ]

    for pattern in total_patterns:
        match = re.search(pattern, lines, re.IGNORECASE)
        if match:
            # Extract the numeric value
            total_str = match.group(1) if 'AED' in pattern else match.group(1)
            # Remove commas and ensure it's a valid number
            total_str = total_str.replace(',', '')
            try:
                # Validate it's a number
                float(total_str)
                fields['total'] = total_str
                break
            except ValueError:
                continue

    # If no total found with patterns, look for largest number as fallback
    if not fields['total']:
        # Find all numbers that look like prices
        price_pattern = r'\b(\d+\.?\d{0,2})\b'
        prices = re.findall(price_pattern, lines)
        if prices:
            # Get the largest value as likely total
            try:
                numeric_prices = [float(p) for p in prices if float(p) > 0]
                if numeric_prices:
                    fields['total'] = str(max(numeric_prices))
            except ValueError:
                pass

    return fields


if __name__ == "__main__":
    # Test module directly
    import sys
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"Testing with: {test_path}")

        try:
            # Extract text
            text = extract_blocks(test_path)
            print("\n--- Extracted Text ---")
            print(text)

            # Parse fields
            fields = parse_fields(text)
            print("\n--- Parsed Fields ---")
            for key, value in fields.items():
                print(f"{key}: {value}")

        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python -m src.textract_handler <image_path>")