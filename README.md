# AWS Receipt Reader — OneDrive Edition

This module forms part of the Ricochet Analytics pipeline under Tabeq Technologies LLC.

A local Python microservice that converts scanned receipts into structured CSV data using AWS Textract.

## Overview

This microservice is designed for use with the Ricochet POS system. It runs locally, receives scanned receipt images from Microsoft Lens via OneDrive synchronization, and outputs structured CSV files containing extracted expense data.

## Features

- Local CLI for manual processing of receipt images.
- Watcher mode to automatically monitor a OneDrive input folder and process new receipts as they arrive.
- Uses AWS Textract AnalyzeExpense for OCR and extraction of expense fields.
- Robust regex parsing for date, start time, end time, and total fields.
- Outputs CSV files with the columns: `date, start_time, end_time, total, source_file, processed_at`.

## Installation & Setup

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file and configure your AWS credentials and region:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   ```env
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   AWS_REGION=us-east-1
   ```

## Usage

### CLI Example

Process a single receipt image manually:
```bash
python -m src.main --in receipts/sample1.jpg --out output/ingest.csv
```

### Watcher Example

Monitor a OneDrive folder and automatically process new receipts:
```bash
python -m src.watcher \
  --in "C:\Users\<user>\OneDrive\Ricochet\Receipts\Input" \
  --out "C:\Users\<user>\OneDrive\Ricochet\Receipts\Output\ingest.csv"
```

**Note:** For real-world scanning, use the Microsoft Lens app to scan receipts and sync them to the designated OneDrive input folder.

## Dependencies

All dependencies are listed in `requirements.txt`:
- `boto3`
- `pandas`
- `python-dotenv`
- `Pillow`
- `watchdog`

## Security

- Store AWS credentials and configuration only in your local `.env` file. Never commit `.env` or sensitive credentials to version control.
- Use an AWS IAM user with least-privilege permissions for Textract AnalyzeExpense access.

## Roadmap

- **v0.1.0-onedrive** — Current release: local CLI and watcher functionality.
- **Future:** Integrate an API ingestion endpoint for backend system integration.

## License

This project is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.
