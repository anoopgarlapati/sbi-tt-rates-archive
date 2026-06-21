"""Shared logic for writing parsed PDF results to per-currency, per-year CSVs."""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PAIR_CSV_HEADER = [
    "date", "tt_buying", "tt_selling",
    "bill_buying", "bill_selling",
    "card_buying", "card_selling",
    "cn_buying", "cn_selling",
    "publication_only", "source_file",
]

METADATA_CSV_HEADER = [
    "date", "source_file", "currencies_found", "status", "parse_warnings", "processed_at",
]


def pair_year_csv_path(rates_dir: str, pair: str, year: str) -> Path:
    return Path(rates_dir) / pair / f"{year}.csv"


def load_existing_dates(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        return {row["date"] for row in reader}


def write_currency_rows(result: dict, rates_dir: str = "rates") -> dict:
    """Write per-currency CSVs for the parsed result. Returns a metadata row dict."""
    rates_path = Path(rates_dir)
    date = result["date"]
    source_file = result["source_file"]
    status = result["parse_status"]
    warnings = result["parse_warnings"]
    currencies = result["currencies"]

    year = date[:4] if date else "unknown"

    if status == "success" and currencies:
        for currency in currencies:
            pair = currency["pair"]
            pair_dir = rates_path / pair
            pair_dir.mkdir(parents=True, exist_ok=True)

            csv_path = pair_dir / f"{year}.csv"
            existing_dates = load_existing_dates(csv_path)

            if date in existing_dates:
                logger.debug("Date %s already in %s — skipping", date, csv_path)
                continue

            is_new = not csv_path.exists()
            with csv_path.open("a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=PAIR_CSV_HEADER)
                if is_new:
                    writer.writeheader()
                    logger.info("New currency/year CSV: %s", csv_path)

                writer.writerow({
                    "date": date,
                    "tt_buying": currency.get("tt_buying", ""),
                    "tt_selling": currency.get("tt_selling", ""),
                    "bill_buying": currency.get("bill_buying", ""),
                    "bill_selling": currency.get("bill_selling", ""),
                    "card_buying": currency.get("card_buying", ""),
                    "card_selling": currency.get("card_selling", ""),
                    "cn_buying": currency.get("cn_buying", ""),
                    "cn_selling": currency.get("cn_selling", ""),
                    "publication_only": str(currency.get("publication_only", False)).lower(),
                    "source_file": source_file,
                })

    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "date": date,
        "source_file": source_file,
        "currencies_found": len(currencies),
        "status": status,
        "parse_warnings": "; ".join(warnings),
        "processed_at": processed_at,
    }


def write_metadata_rows(rows: list, rates_dir: str = "rates") -> None:
    """Write sorted metadata rows to _metadata.csv."""
    metadata_path = Path(rates_dir) / "_metadata.csv"
    rows_sorted = sorted(rows, key=lambda r: (r["date"], r["source_file"]))
    with metadata_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows_sorted)


def append_to_csvs(result: dict, rates_dir: str = "rates") -> None:
    """Write currency CSVs and append one row to _metadata.csv. Used by daily_update."""
    metadata_row = write_currency_rows(result, rates_dir=rates_dir)

    metadata_path = Path(rates_dir) / "_metadata.csv"
    is_new = not metadata_path.exists()
    with metadata_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_CSV_HEADER)
        if is_new:
            writer.writeheader()
        writer.writerow(metadata_row)
