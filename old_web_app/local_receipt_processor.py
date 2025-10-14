#!/usr/bin/env python3
"""
Local Receipt Processor - Proof of Concept
Simulates the AWS Textract expense processing pipeline locally
"""

import os
import json
import sys
from datetime import datetime
from textractprettyprinter.t_pretty_print_expense import get_string
from textractprettyprinter.t_pretty_print_expense import Textract_Expense_Pretty_Print, Pretty_Print_Table_Format

def create_mock_textract_response():
    """
    Create a mock Textract AnalyzeExpense response for testing
    This simulates what AWS Textract would return for a receipt
    """
    return {
        "DocumentMetadata": {
            "Pages": 1
        },
        "ExpenseDocuments": [
            {
                "ExpenseIndex": 1,
                "SummaryFields": [
                    {
                        "Type": {
                            "Text": "VENDOR_NAME",
                            "Confidence": 99.84
                        },
                        "ValueDetection": {
                            "Text": "COFFEE SHOP DOWNTOWN",
                            "Confidence": 99.84,
                            "Geometry": {
                                "BoundingBox": {
                                    "Width": 0.3,
                                    "Height": 0.05,
                                    "Left": 0.35,
                                    "Top": 0.1
                                },
                                "Polygon": [
                                    {"X": 0.35, "Y": 0.1},
                                    {"X": 0.65, "Y": 0.1},
                                    {"X": 0.65, "Y": 0.15},
                                    {"X": 0.35, "Y": 0.15}
                                ]
                            }
                        }
                    },
                    {
                        "Type": {
                            "Text": "TOTAL",
                            "Confidence": 99.91
                        },
                        "ValueDetection": {
                            "Text": "$15.47",
                            "Confidence": 99.91,
                            "Geometry": {
                                "BoundingBox": {
                                    "Width": 0.15,
                                    "Height": 0.04,
                                    "Left": 0.7,
                                    "Top": 0.8
                                },
                                "Polygon": [
                                    {"X": 0.7, "Y": 0.8},
                                    {"X": 0.85, "Y": 0.8},
                                    {"X": 0.85, "Y": 0.84},
                                    {"X": 0.7, "Y": 0.84}
                                ]
                            }
                        }
                    },
                    {
                        "Type": {
                            "Text": "INVOICE_RECEIPT_DATE",
                            "Confidence": 95.12
                        },
                        "ValueDetection": {
                            "Text": "2024-09-24",
                            "Confidence": 95.12,
                            "Geometry": {
                                "BoundingBox": {
                                    "Width": 0.2,
                                    "Height": 0.04,
                                    "Left": 0.4,
                                    "Top": 0.15
                                },
                                "Polygon": [
                                    {"X": 0.4, "Y": 0.15},
                                    {"X": 0.6, "Y": 0.15},
                                    {"X": 0.6, "Y": 0.19},
                                    {"X": 0.4, "Y": 0.19}
                                ]
                            }
                        }
                    }
                ],
                "LineItemGroups": [
                    {
                        "LineItemGroupIndex": 1,
                        "LineItems": [
                            {
                                "LineItemExpenseFields": [
                                    {
                                        "Type": {
                                            "Text": "ITEM",
                                            "Confidence": 99.5
                                        },
                                        "ValueDetection": {
                                            "Text": "Large Coffee",
                                            "Confidence": 99.5
                                        }
                                    },
                                    {
                                        "Type": {
                                            "Text": "PRICE",
                                            "Confidence": 99.8
                                        },
                                        "ValueDetection": {
                                            "Text": "$4.50",
                                            "Confidence": 99.8
                                        }
                                    }
                                ]
                            },
                            {
                                "LineItemExpenseFields": [
                                    {
                                        "Type": {
                                            "Text": "ITEM",
                                            "Confidence": 99.2
                                        },
                                        "ValueDetection": {
                                            "Text": "Blueberry Muffin",
                                            "Confidence": 99.2
                                        }
                                    },
                                    {
                                        "Type": {
                                            "Text": "PRICE",
                                            "Confidence": 99.9
                                        },
                                        "ValueDetection": {
                                            "Text": "$3.25",
                                            "Confidence": 99.9
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

def process_receipt(receipt_path, output_dir="output"):
    """
    Process a receipt file and generate formatted output
    For now, uses mock data - in real implementation would call Textract
    """
    print(f"Processing receipt: {receipt_path}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # In a real implementation, you would:
    # 1. Read the image file
    # 2. Call AWS Textract AnalyzeExpense API
    # 3. Get the JSON response
    # For now, we use mock data

    mock_response = create_mock_textract_response()

    # Pretty print the response using the same library as the Lambda function
    try:
        pretty_printed_string = get_string(
            textract_json=mock_response,
            output_type=[
                Textract_Expense_Pretty_Print.SUMMARY,
                Textract_Expense_Pretty_Print.LINEITEMGROUPS
            ],
            table_format=Pretty_Print_Table_Format.fancy_grid
        )

        # Generate output filename
        base_name = os.path.splitext(os.path.basename(receipt_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}-analyzeexpenseresponse.txt")

        # Save the formatted output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Receipt processed at: {datetime.now().isoformat()}\n")
            f.write(f"Input file: {receipt_path}\n")
            f.write("="*50 + "\n\n")
            f.write(pretty_printed_string)

        print(f"Output saved to: {output_file}")

        # Also save the raw JSON for reference
        json_output_file = os.path.join(output_dir, f"{base_name}-raw-response.json")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(mock_response, f, indent=2)

        print(f"Raw JSON saved to: {json_output_file}")

        return output_file

    except Exception as e:
        print(f"Error processing receipt: {e}")
        return None

def batch_process_receipts(input_dir, output_dir="output"):
    """
    Process all receipt images in a directory
    """
    if not os.path.exists(input_dir):
        print(f"Input directory does not exist: {input_dir}")
        return

    # Common image file extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.pdf'}

    processed_files = []

    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                result = process_receipt(file_path, output_dir)
                if result:
                    processed_files.append(result)

    print(f"\nProcessed {len(processed_files)} receipt files:")
    for file_path in processed_files:
        print(f"  - {file_path}")

def main():
    """Main function"""
    print("Local Receipt Processor - Proof of Concept")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single file: python local_receipt_processor.py <receipt_file>")
        print("  Batch mode:  python local_receipt_processor.py <input_directory>")
        print("\nExample:")
        print("  python local_receipt_processor.py receipt.jpg")
        print("  python local_receipt_processor.py ./receipts/")
        return

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    if os.path.isfile(input_path):
        # Process single file
        process_receipt(input_path, output_dir)
    elif os.path.isdir(input_path):
        # Process directory
        batch_process_receipts(input_path, output_dir)
    else:
        print(f"Error: Path does not exist: {input_path}")

if __name__ == "__main__":
    main()