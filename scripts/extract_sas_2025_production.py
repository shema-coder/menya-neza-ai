import csv
import re
from pathlib import Path

SOURCE = Path("data/raw/sas_2025/SAS_2025_Final_report.txt")
OUTPUT = Path(
    "data/processed/nisr_sas_2025_crop_production_long.csv"
)
VALIDATION = Path(
    "data/processed/nisr_sas_2025_crop_production_validation.csv"
)

DISTRICTS = [
    "Nyarugenge", "Gasabo", "Kicukiro", "Nyanza", "Gisagara",
    "Nyaruguru", "Huye", "Nyamagabe", "Ruhango", "Muhanga",
    "Kamonyi", "Karongi", "Rutsiro", "Rubavu", "Nyabihu",
    "Ngororero", "Rusizi", "Nyamasheke", "Rulindo", "Gakenke",
    "Musanze", "Burera", "Gicumbi", "Rwamagana", "Nyagatare",
    "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Bugesera",
]

CROPS_AB = [
    "Maize", "Sorghum", "Paddy rice", "Wheat", "Other cereals",
    "Cassava", "Sweet potatoes", "Irish potatoes", "Yams & Taro",
    "Banana", "Cooking banana", "Dessert banana", "Banana for beer",
    "Beans", "Bush bean", "Climbing bean", "Pea", "Ground nuts",
    "Soya bean", "Vegetables", "Fruits", "Fodder crops", "Other crops",
]

CROPS_C = [
    "Sweet potatoes", "Irish potatoes", "Beans", "Bush bean",
    "Climbing bean", "Peas", "Soya beans", "Groundnut", "Vegetables",
]

TABLES = [
    {
        "number": 24,
        "season": "A",
        "period": "2024-09 to 2025-02",
        "page": 61,
        "crops": CROPS_AB,
    },
    {
        "number": 25,
        "season": "B",
        "period": "2025-03 to 2025-06",
        "page": 62,
        "crops": CROPS_AB,
    },
    {
        "number": 26,
        "season": "C",
        "period": "2025-07 to 2025-09",
        "page": 63,
        "crops": CROPS_C,
    },
]

VALUE_PATTERN = re.compile(r"^(?:-|(?:\d[\d,]*))$")


def parse_value(token):
    """Return numeric value and status while preserving source meaning."""
    if token == "-":
        return None, "not_reported"

    return int(token.replace(",", "")), "reported"


def extract_table(lines, table):
    title_pattern = re.compile(
        rf"^\s*Table\s+{table['number']}\s*:",
        re.IGNORECASE,
    )

    # Use the last matching heading to avoid the table of contents.
    matches = [
        i for i, line in enumerate(lines)
        if title_pattern.search(line)
    ]

    if not matches:
        raise ValueError(
            f"Could not find Table {table['number']} in the report."
        )

    start = matches[-1]
    parsed_rows = {}
    expected_columns = len(table["crops"])

    for line_number, line in enumerate(lines[start + 1:], start + 2):
        stripped = line.strip()

        if stripped.startswith("Source: NISR, SAS 2025"):
            break

        tokens = stripped.split()
        if not tokens:
            continue

        district = tokens[0]
        if district not in DISTRICTS and district != "National":
            continue

        values = tokens[1:]

        if len(values) != expected_columns:
            raise ValueError(
                f"Table {table['number']}, line {line_number}: "
                f"{district} has {len(values)} values; "
                f"expected {expected_columns}. Check the source table."
            )

        if not all(VALUE_PATTERN.fullmatch(value) for value in values):
            raise ValueError(
                f"Unexpected value in Table {table['number']}, "
                f"line {line_number}: {values}"
            )

        if district in parsed_rows:
            raise ValueError(
                f"Duplicate row for {district} in Table {table['number']}."
            )

        parsed_rows[district] = values

    expected_rows = set(DISTRICTS) | {"National"}
    actual_rows = set(parsed_rows)

    if actual_rows != expected_rows:
        missing = sorted(expected_rows - actual_rows)
        unexpected = sorted(actual_rows - expected_rows)
        raise ValueError(
            f"Table {table['number']} row check failed. "
            f"Missing: {missing}; unexpected: {unexpected}"
        )

    return parsed_rows


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source report not found: {SOURCE}")

    lines = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    production_rows = []
    validation_rows = []

    for table in TABLES:
        rows = extract_table(lines, table)
        crops = table["crops"]
        national_values = rows["National"]

        for crop_index, crop in enumerate(crops):
            national_value, _ = parse_value(national_values[crop_index])

            district_values = []
            missing_count = 0

            for district in DISTRICTS:
                source_value = rows[district][crop_index]
                numeric_value, status = parse_value(source_value)

                if numeric_value is None:
                    missing_count += 1
                else:
                    district_values.append(numeric_value)

                production_rows.append({
                    "year": 2025,
                    "season": table["season"],
                    "season_period": table["period"],
                    "district": district,
                    "crop": crop,
                    "production_mt": (
                        "" if numeric_value is None else numeric_value
                    ),
                    "source_value": source_value,
                    "source_value_status": status,
                    "source": "NISR SAS 2025",
                    "source_table": table["number"],
                    "source_page": table["page"],
                })

            district_sum = sum(district_values)
            complete = missing_count == 0

            # A partial district sum must not be compared as if it
            # represented the complete set of district observations.
            difference = (
                district_sum - national_value if complete else ""
            )

            if not complete:
                check_status = "INCOMPLETE_DISTRICT_DATA"
            elif difference == 0:
                check_status = "MATCH"
            elif abs(difference) <= 3:
                check_status = "SMALL_DIFFERENCE_REVIEW"
            else:
                check_status = "LARGE_DIFFERENCE_REVIEW"

            validation_rows.append({
                "year": 2025,
                "season": table["season"],
                "crop": crop,
                "district_sum_mt": district_sum,
                "district_sum_completeness": (
                    "COMPLETE" if complete else "PARTIAL"
                ),
                "published_national_mt": national_value,
                "difference_mt": difference,
                "district_missing_count": missing_count,
                "validation_status": check_status,
                "source_table": table["number"],
                "source_page": table["page"],
            })

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=production_rows[0].keys())
        writer.writeheader()
        writer.writerows(production_rows)

    with VALIDATION.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=validation_rows[0].keys())
        writer.writeheader()
        writer.writerows(validation_rows)

    print("Extraction completed.")
    print(f"Production records: {len(production_rows)}")
    print(f"Validation checks: {len(validation_rows)}")
    print(f"Production CSV: {OUTPUT}")
    print(f"Validation CSV: {VALIDATION}")
    print("\nValidation status counts:")

    counts = {}
    for row in validation_rows:
        status = row["validation_status"]
        counts[status] = counts.get(status, 0) + 1

    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
