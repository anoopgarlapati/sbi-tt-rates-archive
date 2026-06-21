"""Sanity checks on CSV data. Exits with code 1 on critical failure."""

import csv
import sys
from datetime import date
from pathlib import Path


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def validate(rates_dir: str = "rates") -> bool:
    rates_path = Path(rates_dir)
    critical_fail = False
    warnings = []

    metadata_path = rates_path / "_metadata.csv"
    if not metadata_path.exists():
        print("CRITICAL: _metadata.csv not found")
        return False

    metadata_rows = _load_csv(metadata_path)
    if len(metadata_rows) == 0:
        print("CRITICAL: _metadata.csv has zero rows")
        critical_fail = True

    # Pair directories are subdirectories of rates/
    pair_dirs = [p for p in rates_path.iterdir() if p.is_dir()]

    if not pair_dirs:
        print("CRITICAL: No currency pair directories found in rates/")
        return False

    for pair_dir in sorted(pair_dirs):
        year_csvs = sorted(pair_dir.glob("*.csv"))
        if not year_csvs:
            print(f"CRITICAL: {pair_dir.name}/ has no year CSV files")
            critical_fail = True
            continue

        all_dates = []
        for csv_path in year_csvs:
            rows = _load_csv(csv_path)
            if len(rows) == 0:
                print(f"CRITICAL: {pair_dir.name}/{csv_path.name} has no data rows")
                critical_fail = True
                continue
            all_dates.extend(r["date"] for r in rows)

        if len(all_dates) != len(set(all_dates)):
            seen: set = set()
            dupes = [d for d in all_dates if d in seen or seen.add(d)]  # type: ignore[func-returns-value]
            print(f"CRITICAL: Duplicate dates in {pair_dir.name}: {dupes[:5]}")
            critical_fail = True

    usd_dir = rates_path / "USD-INR"
    if usd_dir.exists():
        usd_rows: list[dict] = []
        for csv_path in sorted(usd_dir.glob("*.csv")):
            usd_rows.extend(_load_csv(csv_path))

        for row in usd_rows:
            val = row.get("tt_buying", "")
            if val:
                try:
                    f = float(val)
                    if not (50.0 <= f <= 150.0):
                        warnings.append(
                            f"USD-INR tt_buying out of range [50,150]: {val} on {row['date']}"
                        )
                except ValueError:
                    warnings.append(f"USD-INR non-numeric tt_buying on {row['date']}: {val}")

        sorted_dates = sorted(r["date"] for r in usd_rows if r.get("date"))
        for i in range(1, len(sorted_dates)):
            prev = date.fromisoformat(sorted_dates[i - 1])
            curr = date.fromisoformat(sorted_dates[i])
            if (curr - prev).days > 5:
                warnings.append(
                    f"USD-INR gap of {(curr - prev).days} days: "
                    f"{sorted_dates[i - 1]} → {sorted_dates[i]}"
                )

    for w in warnings:
        print(f"WARNING: {w}")

    return not critical_fail


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate SBI TT Rates CSVs")
    parser.add_argument("--rates-dir", default="rates", help="Path to rates directory")
    args = parser.parse_args()

    ok = validate(rates_dir=args.rates_dir)
    if not ok:
        sys.exit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
