"""Thin wrapper called by GitHub Actions after a new PDF is downloaded."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from csv_writer import append_to_csvs, load_existing_dates, pair_year_csv_path  # type: ignore[import]
from parse_pdf import parse_pdf  # type: ignore[import]
from validate import validate  # type: ignore[import]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RATES_DIR = "rates"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: daily_update.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    repo_root = Path(__file__).parent.parent

    result = parse_pdf(pdf_path)
    rel_path = str(Path(pdf_path).relative_to(repo_root)) if Path(pdf_path).is_absolute() else pdf_path
    result["source_file"] = rel_path

    date = result["date"]
    year = date[:4] if date else ""

    # Idempotency: if date already present in USD-INR/{year}.csv, exit cleanly
    if date and year:
        usd_csv = pair_year_csv_path(RATES_DIR, "USD-INR", year)
        if date in load_existing_dates(usd_csv):
            logger.info("Date %s already in CSVs — nothing to do", date)
            sys.exit(0)

    if result["parse_status"] == "failed":
        logger.error("Parse failed for %s: %s", pdf_path, result["parse_warnings"])
    else:
        for w in result.get("parse_warnings", []):
            logger.warning("%s", w)

    append_to_csvs(result, rates_dir=RATES_DIR)

    ok = validate(rates_dir=RATES_DIR)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
