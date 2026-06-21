"""Backfill all historical PDFs into per-currency, per-year CSVs.

PDFs are processed sequentially (pymupdf4llm / MuPDF is not thread-safe).
Year grouping is preserved for progress logging.
"""

import argparse
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from csv_writer import load_existing_dates, pair_year_csv_path, write_currency_rows, write_metadata_rows  # type: ignore[import]
from parse_pdf import parse_pdf  # type: ignore[import]
from validate import validate  # type: ignore[import]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PDF_STEM_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def collect_pdfs(repo_root: Path) -> list[Path]:
    pdfs = []
    for pdf in repo_root.rglob("*.pdf"):
        parts = pdf.relative_to(repo_root).parts
        if (
            len(parts) == 3
            and re.match(r"^\d{4}$", parts[0])
            and re.match(r"^\d{2}$", parts[1])
            and PDF_STEM_RE.match(pdf.stem)
        ):
            pdfs.append(pdf)
    pdfs.sort()
    return pdfs


def _date_from_path(pdf: Path) -> str:
    m = PDF_STEM_RE.match(pdf.stem)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def run_backfill(repo_root: Path, rates_dir: str, force: bool) -> bool:
    """Parse all PDFs and write CSVs. Returns True if validation passes."""
    all_pdfs = collect_pdfs(repo_root)
    logger.info("Found %d PDF files", len(all_pdfs))

    pdfs_by_year: dict[str, list[Path]] = {}
    for pdf in all_pdfs:
        pdfs_by_year.setdefault(pdf.parts[-3], []).append(pdf)
    logger.info("Years: %s", sorted(pdfs_by_year.keys()))

    total_parsed = total_skipped = total_failed = 0
    all_pairs: set[str] = set()
    all_metadata: list[dict] = []

    # Global dedup: a PDF in 2021/ can produce a date in 2020, so tracking
    # must span across directory years.
    processed_dates: dict[str, str] = {}

    for year in sorted(pdfs_by_year.keys()):
        year_parsed = year_skipped = year_failed = 0

        for pdf in pdfs_by_year[year]:
            rel_path = str(pdf.relative_to(repo_root))
            date_key = _date_from_path(pdf)

            if date_key and date_key in processed_dates:
                year_skipped += 1
                continue

            if not force and date_key:
                usd_csv = pair_year_csv_path(rates_dir, "USD-INR", date_key[:4])
                if date_key in load_existing_dates(usd_csv):
                    year_skipped += 1
                    processed_dates[date_key] = rel_path
                    continue

            result = parse_pdf(str(pdf))
            result["source_file"] = rel_path

            if result["parse_status"] == "failed":
                logger.error("Failed: %s — %s", rel_path, result["parse_warnings"])
                year_failed += 1
            else:
                for w in result["parse_warnings"]:
                    logger.warning("%s: %s", rel_path, w)
                year_parsed += 1
                for c in result["currencies"]:
                    all_pairs.add(c["pair"])

            all_metadata.append(write_currency_rows(result, rates_dir=rates_dir))

            if date_key:
                processed_dates[date_key] = rel_path

        logger.info(
            "Year %s — parsed %d, skipped %d, failed %d",
            year, year_parsed, year_skipped, year_failed,
        )
        total_parsed += year_parsed
        total_skipped += year_skipped
        total_failed += year_failed

    write_metadata_rows(all_metadata, rates_dir=rates_dir)

    logger.info("--- Backfill summary ---")
    logger.info("Total PDFs:          %d", len(all_pdfs))
    logger.info("Successfully parsed: %d", total_parsed)
    logger.info("Skipped:             %d", total_skipped)
    logger.info("Failed:              %d", total_failed)
    logger.info("Currencies found:    %s", sorted(all_pairs))

    return validate(rates_dir=rates_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical PDFs into per-year CSVs")
    parser.add_argument("--repo-root", default=".", help="Path to repo root")
    parser.add_argument("--rates-dir", default="rates", help="Output directory for CSVs")
    parser.add_argument("--force", action="store_true", help="Re-parse all PDFs ignoring existing data")
    args = parser.parse_args()

    ok = run_backfill(
        repo_root=Path(args.repo_root).resolve(),
        rates_dir=args.rates_dir,
        force=args.force,
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
