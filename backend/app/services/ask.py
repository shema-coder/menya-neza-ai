"""Evidence-grounded question answering for MENYA NEZA AI.

This is a rule-based data assistant, not a general-purpose language model.
Answers are calculated from the existing processed NISR dataset.
"""

import re
from typing import Any

from . import agriculture
from .question_bank import lookup_question
from .conversation import (
    latest_record_context,
    is_contextual_follow_up,
    comparison_requested,
    compare_records,
)

SOURCE = "NISR Seasonal Agricultural Survey 2025"
LIMITATION = (
    "These are historical survey records, not live market availability, "
    "current prices, weather forecasts, or official disaster warnings."
)


def _number(value: Any) -> str:
    if value is None:
        return "not reported"
    number = float(value)
    if number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def _find_crop(question: str) -> str | None:
    """Match a crop name against the crops actually present in the dataset."""
    normalized = question.casefold()
    crops = sorted(agriculture.list_crops(), key=len, reverse=True)

    aliases = {
        "maize": ("maize", "corn", "ibigori"),
        "beans": ("beans", "ibishyimbo"),
        "cassava": ("cassava", "imyumbati"),
        "irish potatoes": ("irish potatoes", "potatoes", "ibirayi"),
        "sweet potatoes": ("sweet potatoes", "ibijumba"),
        "banana": ("banana", "bananas", "ibitoki"),
        "sorghum": ("sorghum", "amasaka"),
        "wheat": ("wheat", "ingano"),
        "vegetables": ("vegetables", "imboga"),
    }

    for crop in crops:
        terms = aliases.get(crop.casefold(), (crop.casefold(),))
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized)
               for term in terms):
            return crop
    return None


def _find_season(question: str) -> str | None:
    """Recognize season references in English and Kinyarwanda."""
    patterns = (
        r"\bseason\s*([abc])\b",
        r"\b([abc])\s*season\b",
        r"\b(?:igihembwe|gihembwe)(?:\s+cya)?\s*([abc])\b",
        r"\bigihembwe\s+([abc])\s+cya\b",
    )

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None

def _find_district(question: str) -> str | None:
    normalized = question.casefold()
    for district in sorted(agriculture.list_districts(),
                           key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(district.casefold()) + r"(?!\w)",
                     normalized):
            return district
    return None


def answer_question(question: str, language: str = "en") -> dict[str, Any]:
    """Answer supported production and data-quality questions with evidence."""
    original = question.strip()
    text = original.casefold()

    if not original:
        return {
            "status": "needs_question",
            "answer": "Please enter a question about crop production, seasons, districts, or data quality.",
            "evidence": [],
            "source": SOURCE,
        }

    unsupported_terms = (
        "weather", "rainfall forecast", "will it rain", "disaster prediction",
        "flood risk", "drought prediction", "live price", "current price",
        "price today", "today's price", "stock available",
    )
    if any(term in text for term in unsupported_terms):
        return {
            "status": "unsupported",
            "answer": (
                "I can't reliably answer that from the available historical "
                "production data. This assistant does not currently provide "
                "verified live prices, live weather, or official disaster warnings."
            ),
            "evidence": [],
            "source": SOURCE,
            "limitation": LIMITATION,
        }

    crop = _find_crop(text)
    season = _find_season(text)
    district = _find_district(text)
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else 2025

    available_years = {
        item["year"] for item in agriculture.list_seasons()
        if item.get("year") is not None
    }
    if year not in available_years:
        return {
            "status": "unsupported",
            "answer": (
                f"The loaded dataset does not contain {year}. "
                f"Available years: {', '.join(map(str, sorted(available_years)))}."
            ),
            "evidence": [],
            "source": SOURCE,
        }

    # NST2_REFERENCE_ANSWER_HANDLER
    # Report reference indicators without claiming target achievement.
    if crop and any(term in text for term in (
        "nst2", "national strategy", "target", "mid-term target",
        "end-term target", "policy target",
    )):
        from .intelligence import supply_price_report

        report = supply_price_report(
            crop=crop,
            season=season or "B",
            year=year,
            district=district,
        )
        alignment = report.get("nst2_alignment", {})
        references = alignment.get("reference_indicators", {})

        if not references:
            return {
                "status": "no_data",
                "answer": (
                    f"No exact NST2 reference indicator is available for "
                    f"{crop} in the loaded reference registry. This does "
                    "not establish that the crop has no policy target."
                ),
                "evidence": [],
                "source": report.get("source", SOURCE),
                "limitation": alignment.get("note", LIMITATION),
            }

        lines = [
            f"NST2 reference indicators for {crop}:",
            "These are policy reference values, not proof of target achievement.",
        ]

        for indicator, values in references.items():
            if not isinstance(values, dict):
                continue
            unit = values.get("unit", "unit not specified")
            baseline = values.get("baseline")
            mid_target = values.get("mid_term_target")
            end_target = values.get("end_term_target")
            lines.append(
                f"{indicator.replace('_', ' ').capitalize()} "
                f"({unit}): baseline {_number(baseline)}; "
                f"mid-term target {_number(mid_target)}; "
                f"end-term target {_number(end_target)}."
            )

        lines.append(
            "Progress has not been calculated. Official indicator definitions, "
            "reporting periods, crop labels, and units must be verified first. "
            "A seasonal NISR district subtotal must not be treated as an "
            "annual national result."
        )

        return {
            "status": "answered",
            "answer": "\n".join(lines),
            "evidence": [{
                "crop": crop,
                "nst2_reference_indicators": references,
                "target_comparison_status": alignment.get(
                    "target_comparison_status"
                ),
                "note": alignment.get("note"),
            }],
            "source": report.get("source", SOURCE),
            "limitation": alignment.get("note", LIMITATION),
        }

    # Compare a named crop across seasons A, B, and C.
    if crop and any(term in text for term in
                    ("compare", "comparison", "across seasons",
                     "between seasons", "seasonal", "all seasons",
                     "gereranya", "kugereranya", "mu bihembwe",
                     "mu bihe bya", "ibihembwe bya",
                     "itandukaniro hagati y'ibihembwe")):
        result = agriculture.seasonal_comparison(year=year, crop=crop)
        if not result.get("eligible") or not result.get("seasons"):
            return {
                "status": "no_data",
                "answer": (
                    f"I couldn't make a complete A/B/C comparison for {crop} "
                    f"in {year} from the available records."
                ),
                "evidence": [],
                "source": SOURCE,
                "limitation": LIMITATION,
            }

        details = result["seasons"]
        language_rw = language.casefold().strip() in {
            "rw", "kin", "kinyarwanda"
        }

        if language_rw:
            crop_names_rw = {
                "maize": "ibigori",
                "beans": "ibishyimbo",
                "cassava": "imyumbati",
                "irish potatoes": "ibirayi",
                "sweet potatoes": "ibijumba",
                "banana": "ibitoki",
                "sorghum": "amasaka",
                "wheat": "ingano",
                "vegetables": "imboga",
            }
            crop_rw = crop_names_rw.get(crop.casefold(), crop)
            lines = [
                f"Igihembwe {item['season']}: toni "
                f"{_number(item.get('reported_district_subtotal_mt'))} "
                f"zatangajwe mu turere {item.get('reported_districts', 0)}."
                for item in details
            ]
            answer = (
                f"Amakuru y'umusaruro w' {crop_rw} mu mwaka wa {year}:\n"
                + "\n".join(lines)
                + "\n\nIcyitonderwa: igiteranyo cy'imibare y'uturere "
                "ntikigomba guhita gifatwa nk'umusaruro wose w'igihugu, "
                "kuko amakuru amwe ashobora kuba atuzuye."
            )
            source_note = (
                "Imibare ishingiye ku nyandiko z'ubushakashatsi bwa NISR "
                "SAS 2025. Reba ibimenyetso kugira ngo umenye amakuru "
                "y'ibihembwe byagereranyijwe."
            )
        else:
            lines = [
                f"Season {item['season']}: "
                f"{_number(item.get('reported_district_subtotal_mt'))} metric tonnes "
                f"reported across {item.get('reported_districts', 0)} districts."
                for item in details
            ]
            answer = f"{crop} production records for {year}:\n" + "\n".join(lines)
            source_note = (
                "District subtotals can be incomplete and should not automatically "
                "be interpreted as published national totals."
            )

        return {
            "status": "answered",
            "answer": answer,
            "evidence": details,
            "source": SOURCE,
            "source_note": source_note,
            "limitation": LIMITATION,
        }

    # District-specific crop record.
    if crop and season and district:
        rows = agriculture.filter_production(
            district=district, season=season, crop=crop, year=year
        )
        if not rows:
            return {
                "status": "no_data",
                "answer": f"No matching record was found for {crop} in {district}, Season {season}, {year}.",
                "evidence": [],
                "source": SOURCE,
            }

        row = rows[0]
        value = row.get("production_mt")
        if value is None:
            answer = (
                f"The {crop} production value for {district}, Season {season}, "
                f"{year} was not reported in the loaded record. Missing is not zero."
            )
        else:
            answer = (
                f"{district} reported {_number(value)} metric tonnes of {crop} "
                f"in Season {season} ({row.get('season_period') or year})."
            )

        evidence = [{
            "district": district,
            "crop": crop,
            "season": season,
            "year": year,
            "season_period": row.get("season_period"),
            "production_mt": value,
            "source": row.get("source", SOURCE),
            "source_table": row.get("source_table"),
            "source_page": row.get("source_page"),
            "value_status": row.get("source_value_status"),
        }]
        return {
            "status": "answered",
            "answer": answer,
            "evidence": evidence,
            "source": SOURCE,
            "limitation": LIMITATION,
        }

    # Highest reported district for a crop in a season.
    if crop and season and any(term in text for term in
                               ("highest", "most", "top", "largest",
                                "leading", "which district")):
        result = agriculture.supply_origins(
            crop=crop, season=season, year=year
        )
        ranked = [
            item for item in result.get("districts", [])
            if item.get("rank") is not None and item.get("production_mt") is not None
        ]
        if not ranked:
            return {
                "status": "no_data",
                "answer": f"No reported district values were available for {crop}, Season {season}, {year}.",
                "evidence": [],
                "source": SOURCE,
            }

        top = ranked[0]
        return {
            "status": "answered",
            "answer": (
                f"{top['district']} had the highest reported {crop} production "
                f"in Season {season} {year}, at "
                f"{_number(top['production_mt'])} metric tonnes. "
                "This ranks reported survey values, not current market supply."
            ),
            "evidence": [top],
            "source": SOURCE,
            "limitation": LIMITATION,
        }

    # General data-quality questions.
    if any(term in text for term in
           ("data quality", "missing data", "missing records",
            "incomplete", "validation", "reliable", "reliability",
            "ubwiza bw'amakuru", "amakuru atuzuye", "amakuru abura",
            "imbogamizi z'ubwiza", "kwizerwa kw'amakuru")):
        quality = agriculture.data_quality(season=season, crop=crop)
        quality_answer = (
            f"The data-quality check returned {quality['records_returned']} "
            f"validation records. Status counts: {quality['status_counts']}. "
            "These are data-quality diagnostics, not agricultural risk levels."
        )

        if language.casefold().strip() in {"rw", "kin", "kinyarwanda"}:
            quality_answer = (
                f"Igenzura ry'ubwiza bw'amakuru ryasuzumye inyandiko "
                f"{quality['records_returned']}. Ibyiciro byabonetse: "
                f"{quality['status_counts']}. Ibi bigaragaza imiterere "
                "y'amakuru, si igipimo cy'ibyago by'ubuhinzi."
            )

        return {
            "status": "answered",
            "answer": quality_answer,
            "evidence": [{
                "records_returned": quality["records_returned"],
                "status_counts": quality["status_counts"],
            }],
            "source": quality.get("source", SOURCE),
            "limitation": quality.get("note"),
        }

    if crop and season:
        summaries = agriculture.production_summaries(
            season=season, crop=crop, year=year
        )
        if summaries:
            summary = summaries[0]
            return {
                "status": "answered",
                "answer": (
                    f"For {crop}, Season {season} {year}, the sum of reported "
                    f"district values is {_number(summary['reported_district_sum_mt'])} "
                    f"metric tonnes. Values were reported for "
                    f"{summary['reported_records']} of "
                    f"{summary['expected_districts_in_dataset']} districts; "
                    f"{summary['missing_production_records']} records have no production value."
                ),
                "evidence": [summary],
                "source": SOURCE,
                "limitation": summary.get("interpretation_note", LIMITATION),
            }

    return {
        "status": "needs_clarification",
        "answer": (
            "I can answer questions about a crop in a district and season, "
            "the highest reported district for a crop, comparisons across "
            "Seasons A/B/C, or production-data quality. Try: "
            "'How much maize did Huye report in Season B 2025?'"
        ),
        "evidence": [],
        "source": SOURCE,
        "limitation": LIMITATION,
    }

# QUESTION_BANK_INTEGRATION
# Exact stored questions use their saved response. Other questions use
# the existing evidence-first rules, including natural Kinyarwanda wording.
_rule_based_answer_question = answer_question

_KINYARWANDA_CROPS = {
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


def _localize_district_production(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Render an evidence-backed district production answer in Kinyarwanda."""
    evidence = result.get("evidence") or []
    if not evidence or not isinstance(evidence[0], dict):
        return result

    row = evidence[0]
    required = ("district", "crop", "season", "year")
    if any(row.get(field) is None for field in required):
        return result

    district = str(row["district"])
    crop = str(row["crop"])
    season = str(row["season"])
    year = row["year"]
    crop_rw = _KINYARWANDA_CROPS.get(crop.casefold(), crop)
    value = row.get("production_mt")
    period = row.get("season_period") or result.get("season_period") or str(year)

    if value is None:
        answer = (
            f"Nta mubare w'umusaruro w'{crop_rw} watangajwe mu karere ka "
            f"{district} mu gihembwe {season} cya {year}. "
            "Kubura kw'umubare ntibisobanura ko umusaruro wari zeru."
        )
    else:
        try:
            value_text = _number(value)
        except (TypeError, ValueError):
            return result

        answer = (
            f"Mu bushakashatsi bwa NISR SAS 2025, akarere ka {district} "
            f"katangaje toni {value_text} z'umusaruro w'{crop_rw} "
            f"mu gihembwe {season} cya {year} ({period}).\n\n"
            "Ibisobanuro: iyi ni imibare y'amateka ku rwego rw'akarere, "
            "si igipimo cy'umusaruro w'ubu. Imibare y'uturere ishobora "
            "kuba ituzuye; ntigomba guhita ifatwa nk'igiteranyo cy'igihugu."
        )

    localized = dict(result)
    localized["answer"] = answer
    return localized


def answer_question(
    question: str,
    language: str = "en",
    conversation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Answer questions and resolve supported contextual follow-ups."""
    language_code = str(language or "en").casefold().strip()
    original = str(question or "").strip()

    previous_hint = latest_record_context(conversation)
    crop = _find_crop(original.casefold())
    district = _find_district(original.casefold())
    season = _find_season(original.casefold())

    year_match = re.search(r"\b(20\d{2})\b", original)
    explicit_year = int(year_match.group(1)) if year_match else None

    if previous_hint and is_contextual_follow_up(
        original,
        crop=crop,
        district=district,
        season=season,
    ):
        # Re-fetch the previous record from the local source dataset.
        # Never trust numeric evidence sent back by the browser.
        verified_rows = agriculture.filter_production(
            district=previous_hint.get("district"),
            crop=previous_hint.get("crop"),
            season=previous_hint.get("season"),
            year=previous_hint.get("year"),
        )
        previous = verified_rows[0] if verified_rows else None

        if previous:
            crop = crop or str(previous.get("crop"))
            district = district or str(previous.get("district"))
            year = explicit_year or previous.get("year") or 2025
            target_season = season or previous.get("season")

            compare = (
                comparison_requested(original)
                and season is not None
                and season != previous.get("season")
            )

            if compare and crop and district:
                target_rows = agriculture.filter_production(
                    district=district,
                    crop=crop,
                    season=target_season,
                    year=year,
                )
                if not target_rows:
                    return {
                        "status": "no_data",
                        "answer": (
                            f"No record was found for {crop} in {district}, "
                            f"Season {target_season}, {year}."
                        ),
                        "evidence": [],
                        "source": SOURCE,
                        "limitation": LIMITATION,
                    }

                target = target_rows[0]
                comparison_result = compare_records(
                    previous,
                    target,
                    language=language_code,
                    source=SOURCE,
                    limitation=LIMITATION,
                )

                # Answer yes/no comparison questions directly.
                question_text = original.casefold()
                asks_if_higher = any(phrase in question_text for phrase in (
                    "was that higher",
                    "was it higher",
                    "was that greater",
                    "was it greater",
                ))

                previous_value = previous.get("production_mt")
                target_value = target.get("production_mt")

                if (
                    asks_if_higher
                    and previous_value is not None
                    and target_value is not None
                    and comparison_result.get("status") == "answered"
                ):
                    previous_value = float(previous_value)
                    target_value = float(target_value)
                    difference = abs(previous_value - target_value)
                    amount = _number(difference)
                    previous_season = previous.get("season")
                    target_season = target.get("season")
                    district_name = previous.get("district")
                    crop_name = previous.get("crop")

                    if previous_value > target_value:
                        answer = (
                            f"Yes. For {district_name}, reported {crop_name} "
                            f"production in Season {previous_season} was higher "
                            f"than Season {target_season} by {amount} metric "
                            f"tonnes ({_number(previous_value)} versus "
                            f"{_number(target_value)})."
                        )
                    elif previous_value < target_value:
                        answer = (
                            f"No. For {district_name}, reported {crop_name} "
                            f"production in Season {previous_season} was lower "
                            f"than Season {target_season} by {amount} metric "
                            f"tonnes ({_number(previous_value)} versus "
                            f"{_number(target_value)})."
                        )
                    else:
                        answer = (
                            f"No. Reported {crop_name} production in "
                            f"{district_name} was equal in Seasons "
                            f"{previous_season} and {target_season}: "
                            f"{_number(previous_value)} metric tonnes in each."
                        )

                    if language_code in {"rw", "kin", "kinyarwanda"}:
                        if previous_value < target_value:
                            answer = (
                                f"Oya. Mu karere ka {district_name}, umusaruro "
                                f"w' {crop_name} watangajwe mu gihembwe "
                                f"{previous_season} wari munsi y'uw'igihembwe "
                                f"{target_season}ho toni {amount} "
                                f"({_number(previous_value)} ugereranyije na "
                                f"{_number(target_value)})."
                            )
                        elif previous_value > target_value:
                            answer = (
                                f"Yego. Mu karere ka {district_name}, umusaruro "
                                f"w' {crop_name} watangajwe mu gihembwe "
                                f"{previous_season} wari hejuru y'uw'igihembwe "
                                f"{target_season}ho toni {amount}."
                            )
                        else:
                            answer = (
                                f"Umusaruro watangajwe wari ungana mu bihembwe "
                                f"{previous_season} na {target_season}: toni "
                                f"{_number(previous_value)} muri buri gihembwe."
                            )

                    comparison_result["answer"] = answer

                return comparison_result

            # Resolve a short follow-up into a complete dataset question.
            resolved = (
                f"How much {crop} did {district} report in "
                f"Season {target_season} {year}?"
            )
            result = _rule_based_answer_question(resolved, language_code)

            if language_code in {"rw", "kin", "kinyarwanda"}:
                result = _localize_district_production(result)

            result["question_context"] = {
                "used": True,
                "original_question": original,
                "interpreted_as": resolved,
                "district": district,
                "crop": crop,
                "season": target_season,
                "year": year,
            }
            return result

    # Exact stored questions remain available, but are not required.
    stored = lookup_question(original, language=language_code)
    if stored and language_code in {"rw", "kin", "kinyarwanda"}:
        return stored["response"]

    result = _rule_based_answer_question(original, language_code)

    if stored and result.get("status") in {"unsupported", "no_data"}:
        result = stored["response"]

    if language_code in {"rw", "kin", "kinyarwanda"}:
        result = _localize_district_production(result)

    return result
