#!/usr/bin/env python3
"""
Main CLI Orchestrator for Receipt Processing
Coordinates Textract extraction and CSV writing
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
try:
    # Try relative imports first (when run as module with -m)
    from .textract_handler import extract_blocks, parse_fields
    from .csv_writer import write_csv
except ImportError:
    # Fall back to absolute imports (when run directly)
    from textract_handler import extract_blocks, parse_fields
    from csv_writer import write_csv


def validate_environment():
    """
    Validate that required AWS credentials are configured

    Returns:
        bool: True if environment is valid, False otherwise
    """
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']

    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Please configure your AWS credentials in a .env file or environment variables.")
        print("See .env.example for the required format.")
        return False

    # Check for region (with fallback)
    if not (os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')):
        print("Warning: No AWS_REGION configured, using default: us-east-1")

    return True


def process_receipt(input_path: str, output_path: str, verbose: bool = False) -> bool:
    """
    Process a single receipt file

    Args:
        input_path: Path to receipt image
        output_path: Path to output CSV
        verbose: Enable verbose logging

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate input file exists
        if not os.path.exists(input_path):
            print(f"Error: Receipt file not found: {input_path}")
            return False

        print("Processing with AWS Textract...")

        # Extract text from image
        if verbose:
            print(f"  Extracting text from: {input_path}")

        text_content = extract_blocks(input_path)

        if verbose:
            print(f"  Extracted {len(text_content)} characters of text")
            print("\n--- Extracted Text Preview ---")
            preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
            print(preview)
            print("--- End Preview ---\n")

        # Parse fields from extracted text
        if verbose:
            print("  Parsing fields from text...")

        fields = parse_fields(text_content)

        if verbose:
            print("  Parsed fields:")
            for key, value in fields.items():
                print(f"    {key}: {value}")

        # Prepare row for CSV
        csv_row = {
            'date': fields.get('date'),
            'start_time': fields.get('start_time'),
            'end_time': fields.get('end_time'),
            'total': fields.get('total'),
            'source_file': os.path.basename(input_path),
            'processed_at': None  # Will be auto-filled by csv_writer
        }

        # Write to CSV
        if verbose:
            print(f"  Writing to CSV: {output_path}")

        write_csv([csv_row], output_path)

        print(f"Done. CSV saved to: {output_path}")
        return True

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return False

    except Exception as e:
        if "Failed to create Textract client" in str(e):
            print(f"Error: AWS credentials not configured. Please check your .env file")
            print(f"Details: {e}")
        elif "Textract API error" in str(e):
            print(f"Error: Failed to process image with Textract: {e}")
        elif "Permission" in str(e):
            print(f"Error: Cannot write to output file: {output_path}")
            print(f"Details: {e}")
        else:
            print(f"Error: An unexpected error occurred: {e}")

        if verbose:
            import traceback
            print("\n--- Full Error Trace ---")
            traceback.print_exc()

        return False


def main():
    """Main CLI entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Process receipt images with AWS Textract and export to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --in receipts/receipt1.jpeg
  python -m src.main -i receipts/receipt1.jpeg -o output/receipts.csv
  python -m src.main --in receipts/receipt1.jpeg --verbose
        """
    )

    parser.add_argument(
        '--in', '-i',
        dest='input',
        required=True,
        help='Path to receipt image file (JPG, PNG, TIFF, PDF)'
    )

    parser.add_argument(
        '--out', '-o',
        dest='output',
        default='output/receipt_data.csv',
        help='Output CSV file path (default: output/receipt_data.csv)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Process receipt
    success = process_receipt(
        args.input,
        args.output,
        args.verbose
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()