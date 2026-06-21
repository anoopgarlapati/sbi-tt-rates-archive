"""Parse a single SBI TT Rates PDF and return a structured dict."""

import re
import sys
import logging
import threading
from pathlib import Path

# MuPDF (underlying library) is not thread-safe — serialize all parse calls
_PARSE_LOCK = threading.Lock()

logger = logging.getLogger(__name__)

# Pairs quoted per 100 foreign currency units — divide all rates by 100
PER_100_PAIRS = {"JPY-INR", "THB-INR", "KRW-INR"}

# Pairs flagged as publication-only
PUBLICATION_ONLY_PAIRS = {"KRW-INR", "TRY-INR"}

# Column indices in the parsed data row (0-based, after stripping empty cells)
RATE_COLUMNS = [
    "tt_buying", "tt_selling",
    "bill_buying", "bill_selling",
    "card_buying", "card_selling",
    "cn_buying", "cn_selling",
]


def _extract_date_from_content(markdown: str) -> str | None:
    match = re.search(r"\b(\d{2})-(\d{2})-(\d{4})\b", markdown)
    if match:
        dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
        return f"{yyyy}-{mm}-{dd}"
    return None


def _extract_date_from_filename(pdf_path: str) -> str | None:
    stem = Path(pdf_path).stem  # e.g. "2020-07-02-14:15" or "2020-07-02"
    match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    if match:
        return match.group(1)
    return None


def _clean_rate(value: str) -> str:
    v = value.strip().replace(",", "")
    if v in ("", "0", "0.00", "0.0"):
        return ""
    return v


def _divide_by_100(value: str) -> str:
    if value == "":
        return ""
    try:
        return f"{float(value) / 100:.4f}".rstrip("0").rstrip(".")
    except ValueError:
        return value


def _parse_table_rows(markdown: str, warnings: list) -> list:
    # Older PDFs say "LACS", newer say "LAKHS" — "BETWEEN" alone uniquely identifies this section
    marker = "TRANSACTIONS BETWEEN"
    idx = markdown.find(marker)
    if idx == -1:
        warnings.append("Reference rates section header not found in PDF content")
        return []

    section = markdown[idx:]
    currencies = []

    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue

        # Split pipe-delimited cells, strip whitespace, drop empty border cells
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]

        # Skip header/separator/note rows
        if len(cells) < 3:
            continue
        if re.match(r"^[-:]+$", cells[0]):
            continue
        # Skip rows where the second cell doesn't look like a pair code (e.g. CURRENCY | USD/INR | ...)
        if "/" not in cells[1]:
            continue

        # Strip markdown bold/italic markers that appear in some PDFs
        pair_code = re.sub(r"\*+", "", cells[1]).strip()
        currency_name = re.sub(r"\*+", "", cells[0]).strip()
        pair_key = pair_code.replace("/", "-")  # "USD/INR" → "USD-INR"

        # Expect at least 9 cells: currency, pair, 8 rate values
        if len(cells) < 10:
            warnings.append(f"Skipping row with too few cells for pair {pair_key}: {cells}")
            continue

        raw_rates = cells[2:10]
        rates = [_clean_rate(r) for r in raw_rates]

        # Divide per-100-unit pairs
        if pair_key in PER_100_PAIRS:
            rates = [_divide_by_100(r) for r in rates]

        entry = {
            "pair": pair_key,
            "name": currency_name,
            "publication_only": pair_key in PUBLICATION_ONLY_PAIRS,
        }
        for col, val in zip(RATE_COLUMNS, rates):
            entry[col] = val

        currencies.append(entry)

    return currencies


def parse_pdf(pdf_path: str) -> dict:
    warnings = []
    try:
        import pymupdf4llm  # noqa: PLC0415

        with _PARSE_LOCK:
            raw = pymupdf4llm.to_markdown(pdf_path, table_strategy="lines_strict")
        markdown: str = raw if isinstance(raw, str) else ""

        date = _extract_date_from_content(markdown)
        if date is None:
            date = _extract_date_from_filename(pdf_path)
            if date:
                warnings.append(
                    f"Date not found in PDF content; fell back to filename date: {date}"
                )
            else:
                warnings.append("Could not extract date from PDF content or filename")
                date = ""

        currencies = _parse_table_rows(markdown, warnings)

        return {
            "date": date,
            "source_file": pdf_path,
            "parse_status": "success",
            "parse_warnings": warnings,
            "currencies": currencies,
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "date": _extract_date_from_filename(pdf_path) or "",
            "source_file": pdf_path,
            "parse_status": "failed",
            "parse_warnings": [str(exc)],
            "currencies": [],
        }


if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: parse_pdf.py <path-to-pdf>")
        sys.exit(1)

    result = parse_pdf(sys.argv[1])
    print(json.dumps(result, indent=2))
