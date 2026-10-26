"""Generate bilingual stored Q&A entries from processed NISR records."""

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = (
    ROOT / "data" / "processed"
    / "nisr_sas_2025_crop_production_long.csv"
)
OUTPUT_FILE = (
    ROOT / "data" / "knowledge"
    / "nisr_sas_2025_question_bank.jsonl"
)

SOURCE = "NISR Seasonal Agricultural Survey 2025"
LIMITATION = (
    "These are historical survey records, not live market prices, "
    "current production estimates, weather forecasts, or official disaster warnings."
)

CROP_RW = {
    "maize": "ibigori",
    "corn": "ibigori",
    "beans": "ibishyimbo",
    "cassava": "imyumbati",
    "irish potatoes": "ibirayi",
    "potatoes": "ibirayi",
    "sweet potatoes": "ibijumba",
    "banana": "ibitoki",
    "bananas": "ibitoki",
    "sorghum": "amasaka",
    "wheat": "ingano",
    "vegetables": "imboga",
}


def number(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return "not reported"
    if value.is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def int_or_none(value: Any) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None and parsed.is_integer() else None


def question_variants(crop: str, district: str, season: str, year: int):
    crop_rw = CROP_RW.get(crop.casefold(), crop)

    english = [
        f"How much {crop} did {district} report in Season {season} {year}?",
        f"What was the reported {crop} production in {district} during Season {season} of {year}?",
        f"How many metric tonnes of {crop} were recorded for {district} in Season {season}, {year}?",
        f"Give me the {year} Season {season} {crop} production figure for {district}.",
    ]

    kinyarwanda = [
        f"Toni zingahe z' {crop_rw} zatangajwe mu karere ka {district} mu gihembwe {season} cya {year}?",
        f"Umusaruro w' {crop_rw} mu karere ka {district} mu gihembwe {season} cya {year} wari ungana iki?",
        f"Ni uwuhe mubare w'umusaruro w' {crop_rw} watangajwe i {district} mu gihembwe {season} cya {year}?",
        f"Mpa amakuru y'umusaruro w' {crop_rw} muri {district}, igihembwe {season}, {year}.",
    ]

    return [("en", q) for q in english] + [("rw", q) for q in kinyarwanda]


def make_response(row: dict[str, str]) -> dict[str, Any]:
    crop = row.get("crop") or "crop"
    district = row.get("district") or "district"
    season = row.get("season") or "unknown"
    year = int_or_none(row.get("year")) or 2025
    period = row.get("season_period") or f"Season {season}, {year}"
    value = number(row.get("production_mt"))
    table = int_or_none(row.get("source_table"))
    page = int_or_none(row.get("source_page"))
    crop_rw = CROP_RW.get(crop.casefold(), crop)

    if value is None:
        answer_en = (
            f"The production value for {crop} in {district}, Season {season}, "
            f"{year} was not reported in the loaded record. A missing value "
            "must not be interpreted as zero."
        )
        answer_rw = (
            f"Umubare w'umusaruro w' {crop_rw} mu karere ka {district}, "
            f"mu gihembwe {season} cya {year}, ntiwatangajwe. "
            "Kubura kw'agaciro ntibisobanura ko umusaruro wari zeru."
        )
    else:
        answer_en = (
            f"{district} reported {fmt(value)} metric tonnes of {crop} in "
            f"Season {season} ({period}).\n\n"
            "Context: this is a historical district-level survey figure, "
            "not a live estimate. District records may be incomplete and "
            "must not automatically be treated as a complete national total."
        )
        answer_rw = (
            f"Mu bushakashatsi bwa NISR SAS 2025, akarere ka {district} "
            f"katangaje toni {fmt(value)} z'umusaruro w' {crop_rw} mu "
            f"gihembwe {season} ({period}).\n\n"
            "Ibisobanuro: iyi ni imibare y'amateka ku rwego rw'akarere, "
            "si igipimo cy'umusaruro w'ubu. Imibare y'uturere ishobora "
            "kuba ituzuye; ntigomba guhita ifatwa nk'igiteranyo cy'igihugu."
        )

    evidence = [{
        "district": district,
        "crop": crop,
        "season": season,
        "year": year,
        "season_period": period,
        "production_mt": value,
        "source": SOURCE,
        "source_table": table,
        "source_page": page,
        "value_status": row.get("source_value_status"),
    }]

    return {
        "status": "answered",
        "answer_en": answer_en,
        "answer_rw": answer_rw,
        "evidence": evidence,
        "source": SOURCE,
        "source_note": (
            f"Historical district record. Source table: {table if table is not None else 'not specified'}; "
            f"page: {page if page is not None else 'not specified'}."
        ),
        "limitation": LIMITATION,
    }


def main() -> None:
    if not SOURCE_FILE.is_file():
        raise SystemExit(f"Required source dataset not found: {SOURCE_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    source_rows = 0
    seen = set()

    with SOURCE_FILE.open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        required = {
            "year", "season", "district", "crop", "production_mt",
            "source_value_status", "source_table", "source_page",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                "Source CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )

        with OUTPUT_FILE.open("w", encoding="utf-8", newline="\n") as out:
            for row_index, row in enumerate(reader, start=1):
                crop = (row.get("crop") or "").strip()
                district = (row.get("district") or "").strip()
                season = (row.get("season") or "").strip().upper()
                year = int_or_none(row.get("year"))

                if not crop or not district or not season or year is None:
                    continue

                source_rows += 1
                response_data = make_response(row)

                for variant_index, (language, question) in enumerate(
                    question_variants(crop, district, season, year), start=1
                ):
                    normalized = re.sub(
                        r"\s+", " ",
                        re.sub(r"[^\w]+", " ", question.casefold())
                    ).strip()
                    unique_key = (language, normalized)
                    if unique_key in seen:
                        continue
                    seen.add(unique_key)

                    if language == "rw":
                        answer = response_data["answer_rw"]
                        response_data["answer_rw"] = answer
                        stored_response = {
                            "status": response_data["status"],
                            "answer": answer,
                            "evidence": response_data["evidence"],
                            "source": response_data["source"],
                            "source_note": response_data["source_note"],
                            "limitation": response_data["limitation"],
                        }
                    else:
                        stored_response = {
                            "status": response_data["status"],
                            "answer": response_data["answer_en"],
                            "evidence": response_data["evidence"],
                            "source": response_data["source"],
                            "source_note": response_data["source_note"],
                            "limitation": response_data["limitation"],
                        }

                    record_key = f"nisr-sas-2025-row-{row_index:05d}"
                    entry = {
                        "id": f"{record_key}-{language}-{variant_index}",
                        "record_key": record_key,
                        "language": language,
                        "intent": "district_crop_season_production",
                        "question": question,
                        "response": stored_response,
                    }
                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    total += 1

    if total < 1000:
        raise SystemExit(
            f"Only generated {total} questions. Review the source dataset; "
            "the build requires at least 1,000 entries."
        )

    print(f"Source records processed: {source_rows:,}")
    print(f"Unique question entries written: {total:,}")
    print(f"Languages: English and Kinyarwanda")
    print(f"Output: {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
