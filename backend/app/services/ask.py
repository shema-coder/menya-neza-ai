"""Evidence-grounded question answering for MENYA NEZA AI.

This is a rule-based data assistant, not a general-purpose language model.
Answers are calculated from the existing processed NISR dataset.
"""

import re
from typing import Any

from . import agriculture, tangabid, esoko_source
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

# Requests outside the assistant's verified evidence scope must be rejected
# before conversation memory or saved-question fallback can reinterpret them.
_UNSUPPORTED_TERMS = (
    "weather", "current weather", "rainfall forecast", "will it rain",
    "weather forecast", "forecast", "disaster prediction", "disaster warning",
    "flood risk", "flooding", "flood", "flood forecast",
    "drought", "drought risk", "landslide", "storm",
    "rainfall", "rainfall forecast", "temperature forecast",
    "weather tomorrow", "weather today",
    "drought prediction", "live price", "current price",
    "price today", "today's price", "prices today", "market price",
    "food prices", "stock available", "price", "prices",
    "igiciro", "ibiciro", "ikirere", "imvura", "umwuzure", "amapfa",
    "ibyago by'ibiza", "ibiza", "ububiko bw'ibiribwa", "ku isoko ubu",
)


def _is_unsupported_request(question: str) -> bool:
    """Detect requests the current verified data cannot safely answer."""
    normalized = (
        str(question or "").casefold()
        .replace("’", "'")
        .replace("‘", "'")
    )
    return any(term in normalized for term in _UNSUPPORTED_TERMS)


def _unsupported_response(language: str = "en") -> dict[str, Any]:
    """Return a consistent, evidence-free response for unsupported requests."""
    is_rw = str(language or "en").casefold().strip() in {
        "rw", "kin", "kinyarwanda"
    }

    if is_rw:
        answer = (
            "Sinshobora gusubiza icyo kibazo mu buryo bwizewe "
            "nkoresheje amakuru y'umusaruro yo mu bihe byashize. "
            "Iyi sisitemu ntitanga ibiciro by'ako kanya byagenzuwe, "
            "amakuru y'ikirere cyangwa imbuzi zemewe z'ibiza."
        )
        limitation = (
            "Aya ni amakuru y'umusaruro wo mu bihe byashize; "
            "ntagaragaza ibiciro biriho ubu, ububiko bw'ibiribwa, "
            "iteganyagihe cyangwa imbuzi zemewe z'ibiza."
        )
    else:
        answer = (
            "I can't reliably answer that from the available historical "
            "production data. This assistant does not provide verified "
            "market prices, live weather, forecasts, or official disaster warnings."
        )
        limitation = LIMITATION

    return {
        "status": "unsupported",
        "answer": answer,
        "evidence": [],
        "source": SOURCE,
        "limitation": limitation,
    }


_MARKET_PRICE_MARKERS = (
    "price", "prices", "cost", "costs", "igiciro", "ibiciro",
    "ikiguzi", "angahe", "ngahe", "kabura",
    "how much is", "how much was", "how much does",
)

_UNSUPPORTED_ENVIRONMENT_TERMS = (
    "weather", "rainfall", "forecast", "will it rain",
    "disaster prediction", "disaster warning", "flood risk",
    "flooding", "flood", "drought", "landslide", "storm",
    "temperature forecast", "imvura", "ikirere", "umwuzure",
    "amapfa", "iteganyagihe", "ibyago by'ibiza", "ibiza",
    "ububiko bw'ibiribwa",
)

_MARKET_MONTHS = {
    "january": 1, "jan": 1, "mutarama": 1,
    "february": 2, "feb": 2, "gashyantare": 2,
    "march": 3, "mar": 3, "werurwe": 3,
    "april": 4, "apr": 4, "mata": 4,
    "may": 5, "gicurasi": 5,
    "june": 6, "jun": 6, "kamena": 6,
    "july": 7, "jul": 7, "nyakanga": 7,
    "august": 8, "aug": 8, "kanama": 8,
    "september": 9, "sep": 9, "sept": 9, "nzeri": 9,
    "october": 10, "oct": 10, "ukwakira": 10,
    "november": 11, "nov": 11, "ugushyingo": 11,
    "december": 12, "dec": 12, "ukuboza": 12,
}
_MARKET_MONTHS_RW = {
    1: "Mutarama", 2: "Gashyantare", 3: "Werurwe",
    4: "Mata", 5: "Gicurasi", 6: "Kamena",
    7: "Nyakanga", 8: "Kanama", 9: "Nzeri",
    10: "Ukwakira", 11: "Ugushyingo", 12: "Ukuboza",
}
_MARKET_MONTHS_EN = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _market_language_rw(language: str) -> bool:
    return str(language or "en").casefold().strip() in {
        "rw", "kin", "kinyarwanda"
    }


def _market_text(question: str) -> str:
    return (
        str(question or "").casefold()
        .replace("’", "'")
        .replace("‘", "'")
    )


def _market_phrase_found(text: str, phrase: str) -> bool:
    return bool(re.search(
        r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)",
        text,
    ))


def _is_market_price_question(question: str) -> bool:
    text = _market_text(question)
    if any(marker in text for marker in _MARKET_PRICE_MARKERS):
        return True

    # Handle common price questions that omit the word "price".
    return (
        any(phrase in text for phrase in (
            "what does it cost", "what does the flour cost",
            "akawunga kangahe", "igura angahe",
        ))
    )


def _is_unsupported_environment_request(question: str) -> bool:
    text = _market_text(question)
    return any(term in text for term in _UNSUPPORTED_ENVIRONMENT_TERMS)


def _find_market_product(question: str, products: list[str]) -> str | None:
    text = _market_text(question)

    # Prefer an exact source product label when the user supplies one.
    for product in sorted(products, key=len, reverse=True):
        if _market_phrase_found(text, product):
            return product

    # Kinyarwanda and common English aliases for products in the export.
    aliases = (
        ("akawunga ka gashumba", "Maize Flour - Gashumba"),
        ("ifu y'ibigori", "Maize Flour"),
        ("ifu y'ikigori", "Maize Flour"),
        ("akawunga", "Maize Flour"),
        ("maize meal", "Maize Flour"),
        ("corn flour", "Maize Flour"),
        ("ibigori", "Maize"),
    )
    product_lookup = {item.casefold(): item for item in products}
    for alias, canonical in aliases:
        if _market_phrase_found(text, alias):
            return product_lookup.get(canonical.casefold())
    return None


def _find_market_location(question: str, locations: list[str]) -> str | None:
    text = _market_text(question)
    for location in sorted(locations, key=len, reverse=True):
        if _market_phrase_found(text, location):
            return location
    return None


def _format_market_month(month: str, language: str) -> str:
    match = re.match(r"^(20\d{2})-(\d{2})-\d{2}$", month)
    if not match:
        return month
    year, month_number = int(match.group(1)), int(match.group(2))
    names = _MARKET_MONTHS_RW if _market_language_rw(language) else _MARKET_MONTHS_EN
    return f"{names[month_number]} {year}"


def _requested_market_month(
    question: str,
    available_months: list[str],
    language: str,
) -> tuple[str | None, str | None, bool]:
    """Return (source month, display label, was a month explicitly requested)."""
    text = _market_text(question)
    iso = re.search(
        r"\b(20\d{2})[-/](0?[1-9]|1[0-2])(?:[-/]\d{1,2})?\b",
        text,
    )
    if iso:
        year, number = int(iso.group(1)), int(iso.group(2))
        date = f"{year:04d}-{number:02d}-01"
        return date, _format_market_month(date, language), True

    year_match = re.search(r"\b(20\d{2})\b", text)
    requested_year = int(year_match.group(1)) if year_match else None

    for month_name, number in sorted(
        _MARKET_MONTHS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if not _market_phrase_found(text, month_name):
            continue

        if requested_year is not None:
            date = f"{requested_year:04d}-{number:02d}-01"
            return date, _format_market_month(date, language), True

        matching = [
            value for value in available_months
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value)
            and int(value[5:7]) == number
        ]
        if matching:
            date = max(matching)
            return date, _format_market_month(date, language), True

        display = (
            _MARKET_MONTHS_RW[number]
            if _market_language_rw(language)
            else _MARKET_MONTHS_EN[number]
        )
        return None, display, True

    return None, None, False


def _market_clarification(
    message_en: str,
    message_rw: str,
    language: str,
    *,
    status: str = "needs_clarification",
) -> dict[str, Any]:
    return {
        "status": status,
        "answer": message_rw if _market_language_rw(language) else message_en,
        "evidence": [],
        "source": tangabid.SOURCE_NAME,
        "limitation": (
            "Aya ni amakuru y'ibiciro ya buri kwezi yatanzwe n'inkomoko; "
            "ibiciro biriho ubu ntibyagenzuwe. Ifaranga n'uburyo bwo "
            "gukusanya amakuru ntibyagenzuwe mu buryo bwigenga."
            if _market_language_rw(language)
            else
            "The connected data contains monthly source-provided summaries, "
            "not verified live prices. Currency and collection methodology are unverified."
        ),
    }


def _answer_market_price_question(
    question: str,
    language: str,
) -> dict[str, Any] | None:
    """Answer a local price question from the validated monthly source export."""
    if not _is_market_price_question(question):
        return None

    is_rw = _market_language_rw(language)

    try:
        catalogue = tangabid.price_trends(limit=1)
        options = catalogue.get("available_options", {})
        products = options.get("products", [])
        locations = options.get("locations", [])
        months = options.get("months", [])
    except (FileNotFoundError, ValueError):
        return _market_clarification(
            "The monthly market-price dataset is currently unavailable.",
            "Amakuru y'ibiciro bya buri kwezi ntaraboneka muri sisitemu.",
            language,
            status="no_data",
        )

    product = _find_market_product(question, products)
    location = _find_market_location(question, locations)

    live_requested = any(term in _market_text(question) for term in (
        "today", "current", "live", "right now", "now",
        "uyu munsi", "ubu", "aka kanya",
    ))

    if product is None:
        return _market_clarification(
            "Which product do you mean? Please use a product name recorded in the market dataset.",
            "Vuga igicuruzwa ushaka kumenya igiciro cyacyo, uko cyanditse mu makuru y'isoko.",
            language,
        )

    if location is None:
        return _market_clarification(
            "Which market or location should I check? Local prices can differ. I can return monthly observations, not a verified live quote.",
            "Sinshobora kwemeza igiciro cy'uyu munsi. Vuga isoko cyangwa ahantu ushaka kugenzura; nshobora kugaragaza amakuru ya buri kwezi, ariko si igiciro cy'ako kanya cyagenzuwe.",
            language,
        )

    requested_month, requested_label, month_was_requested = _requested_market_month(
        question, months, language
    )

    if month_was_requested and requested_month is None:
        return _market_clarification(
            f"No source month is available for {requested_label}.",
            f"Nta makuru y'ibiciro aboneka mu kwezi kwa {requested_label}.",
            language,
            status="no_data",
        )

    try:
        report = tangabid.price_trends(
            product=product,
            location=location,
            month=requested_month,
            limit=1000,
        )
    except (FileNotFoundError, ValueError):
        return _market_clarification(
            "The monthly market-price dataset could not be queried.",
            "Ntibyashobotse gushakisha amakuru y'ibiciro bya buri kwezi.",
            language,
            status="no_data",
        )

    records = report.get("records") or []
    if not records:
        detail = (
            f" for {requested_label}" if month_was_requested else ""
        )
        if is_rw:
            answer = (
                f"Nta nyandiko y'ibiciro yatanzwe n'inkomoko yabonetse ku "
                f"{product} i {location}{detail}. Ibi ntibihamya ko igiciro ari zeru."
            )
        else:
            answer = (
                f"No source-provided monthly observation was found for "
                f"{product} at {location}{detail}. This does not mean the price is zero."
            )
        return {
            "status": "no_data",
            "answer": answer,
            "evidence": [],
            "source": report.get("source", tangabid.SOURCE_NAME),
            "limitation": report.get("note", ""),
        }

    selected_month = (
        requested_month
        if month_was_requested
        else max(str(row.get("month", "")) for row in records)
    )
    selected = [
        row for row in records
        if str(row.get("month", "")) == selected_month
    ]

    # Do not choose silently between distinct units or duplicate market rows.
    distinct_units = {str(row.get("unit", "")) for row in selected}
    distinct_regions = {str(row.get("region", "")) for row in selected}
    if len(selected) != 1:
        return {
            "status": "needs_clarification",
            "answer": (
                "More than one source observation matches this product, location and month. "
                "Specify the unit or market detail so I do not choose one arbitrarily."
                if not is_rw else
                "Hari inyandiko nyinshi zihuye n'igicuruzwa, ahantu n'ukwezi. "
                "Sobanura igipimo cyangwa andi makuru y'isoko kugira ngo ntihitembwe umubare uko bishakiye."
            ),
            "evidence": selected[:10],
            "source": report.get("source", tangabid.SOURCE_NAME),
            "limitation": report.get("note", ""),
        }

    row = selected[0]
    month_label = _format_market_month(str(row["month"]), language)
    average = _number(row.get("avg_price"))
    minimum = _number(row.get("min_price"))
    maximum = _number(row.get("max_price"))
    unit = str(row.get("unit") or "unit not reported")
    sample_count = row.get("sample_count")
    latest_source_month = max(months) if months else None
    latest_month_may_be_incomplete = str(row.get("month")) == latest_source_month

    if is_rw:
        prefix = (
            "Nta giciro cy'ako kanya cyagenzuwe mfite. "
            "Amakuru aheruka y'ukwezi aboneka muri dataset ya TangaBid: "
            if live_requested else
            "Amakuru y'ibiciro bya buri kwezi yatanzwe na TangaBid: "
        )
        answer = (
            f"{prefix}{product} i {location}, {month_label}: "
            f"impuzandengo yatanzwe ni {average} kuri {unit}; "
            f"igiciro cyo hasi ni {minimum}, icyo hejuru ni {maximum}. "
            f"Umubare w'ibipimo watanzwe n'inkomoko ni {sample_count}. "
            "Ifaranga, ubwoko nyakuri bw'igiciro n'uburyo bwo gukusanya amakuru "
            "ntibyagenzuwe mu buryo bwigenga. "
        )
        if latest_month_may_be_incomplete:
            answer += "Ukwezi kwa nyuma gushobora kuba kutuzuye. "
        answer += "Aya ni amakuru ya buri kwezi, si igiciro cyagenzuwe cyo uyu munsi."
    else:
        prefix = (
            "I do not have a verified live price. The latest available monthly observation is: "
            if live_requested else
            "The source-provided monthly observation is: "
        )
        answer = (
            f"{prefix}{product} at {location}, {month_label}: "
            f"reported average {average} per {unit}, minimum {minimum}, "
            f"maximum {maximum}. Source-reported sample count: {sample_count}. "
            "Currency, exact price type and collection method have not been independently verified. "
        )
        if latest_month_may_be_incomplete:
            answer += "The latest calendar month may be incomplete. "
        answer += "This is a monthly summary, not a verified live quote for today."

    evidence = {
        key: row.get(key)
        for key in (
            "month", "product", "unit", "location", "region",
            "avg_price", "min_price", "max_price", "sample_count",
        )
    }
    evidence.update({
        "source": report.get("source", tangabid.SOURCE_NAME),
        "source_file": report.get("source_file"),
        "currency": report.get("currency"),
        "currency_status": report.get("currency_status"),
        "price_type": report.get("price_type"),
        "live_price_verified": False,
        "forecast_produced": False,
    })

    limitation = report.get("note", "")
    limitations = report.get("limitations")
    if isinstance(limitations, (list, tuple)):
        limitation = " ".join(str(item) for item in limitations if item) + " " + str(limitation)

    return {
        "status": "answered",
        "answer": answer,
        "evidence": [evidence],
        "source": report.get("source", tangabid.SOURCE_NAME),
        "source_note": report.get("note", ""),
        "limitation": limitation,
        "price_observation": {
            "month": row.get("month"),
            "product": product,
            "location": location,
            "unit": unit,
            "average": row.get("avg_price"),
            "minimum": row.get("min_price"),
            "maximum": row.get("max_price"),
            "sample_count": sample_count,
            "live_price_verified": False,
            "forecast_produced": False,
        },
    }


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
    """Recognize season labels and natural Kinyarwanda ordinal forms."""
    patterns = (
        r"\bseason\s*([abc])\b",
        r"\b([abc])\s*season\b",
        r"\b(?:igihembwe|gihembwe|igihembo)(?:\s+cya)?\s*([abc])\b",
        r"\b(?:igihembwe|igihembo)\s+([abc])\s+cya\b",
    )

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    ordinal_patterns = (
        r"\b(?:igihembwe|gihembwe|igihembo)\s+cya\s*(1|2|3)\b",
        r"\b(?:igihembwe|gihembwe|igihembo)\s+cya\s+(mbere|kabiri|gatatu)\b",
        r"\b(?:igihembwe|gihembwe|igihembo)\s+(mbere|kabiri|gatatu)\b",
    )
    season_map = {
        "1": "A", "mbere": "A",
        "2": "B", "kabiri": "B",
        "3": "C", "gatatu": "C",
    }

    for pattern in ordinal_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return season_map[match.group(1).casefold()]

    return None

def _find_seasons(question: str) -> list[str]:
    """Find explicitly requested seasons in their order in the question."""
    normalized = str(question or "").casefold().replace("’", "'").replace("‘", "'")
    patterns = (
        r"\bseason\s*([abc])\b",
        r"\b([abc])\s*season\b",
        r"\b(?:igihembwe|gihembwe|igihembo)(?:\s+cya)?\s*([abc])\b",
        r"\b(?:igihembwe|gihembwe|igihembo)\s+cya\s*(1|2|3|mbere|kabiri|gatatu)\b",
        r"\b(?:n'icya|icya)\s*([abc])\b",
        r"\b(?:n'icya|icya)\s*(1|2|3|mbere|kabiri|gatatu)\b",
    )
    ordinal = {
        "1": "A", "mbere": "A", "2": "B", "kabiri": "B",
        "3": "C", "gatatu": "C",
    }
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            token = next((value for value in match.groups() if value), "")
            season = ordinal.get(token.casefold(), token.upper())
            if season in {"A", "B", "C"}:
                matches.append((match.start(), season))
    return list(dict.fromkeys(
        season for _, season in sorted(matches)
    ))


def _asks_district_count(question: str) -> bool:
    """Detect questions asking how many districts reported a value."""
    text = str(question or "").casefold().replace("’", "'").replace("‘", "'")
    phrases = (
        "how many districts", "number of districts", "district count",
        "count of districts", "how many areas reported",
        "uturere tungahe", "uturere tangahe",
        "umubare w'uturere", "ni uturere tungahe",
    )
    return any(phrase in text for phrase in phrases)


def _asks_comparison(question: str) -> bool:
    text = str(question or "").casefold()
    return any(term in text for term in (
        "compare", "comparison", "between", "difference", "versus",
        " vs ", "gereranya", "ugereranyije", "itandukaniro",
    ))


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
    text = original.casefold().replace("’", "'").replace("‘", "'")

    if not original:
        return {
            "status": "needs_question",
            "answer": "Please enter a question about crop production, seasons, districts, or data quality.",
            "evidence": [],
            "source": SOURCE,
        }

    if _is_unsupported_request(text):
        return _unsupported_response(language)

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
        years_text = ", ".join(map(str, sorted(available_years))) or "none"
        language_rw = str(language or "en").casefold().strip() in {
            "rw", "kin", "kinyarwanda"
        }
        if language_rw:
            answer = (
                f"Iyi sisitemu irimo amakuru y'umusaruro yo mu mwaka wa "
                f"{years_text} gusa. Nta makuru y'umusaruro yo mu mwaka wa "
                f"{year} aboneka."
            )
            limitation = (
                "Igisubizo gishingiye ku myaka iri muri dataset gusa; "
                "ntidukwiye guhimba amakuru y'umwaka utabonetse."
            )
        else:
            answer = (
                f"The loaded dataset does not contain {year}. "
                f"Available years: {years_text}."
            )
            limitation = LIMITATION

        return {
            "status": "unsupported",
            "answer": answer,
            "evidence": [],
            "source": SOURCE,
            "limitation": limitation,
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

    # Handle explicit two-season comparisons for one district first.
    explicit_seasons = _find_seasons(text)
    if crop and district and len(explicit_seasons) >= 2 and _asks_comparison(text):
        first_season, second_season = explicit_seasons[:2]
        first_rows = agriculture.filter_production(
            district=district, crop=crop, season=first_season, year=year
        )
        second_rows = agriculture.filter_production(
            district=district, crop=crop, season=second_season, year=year
        )
        if not first_rows or not second_rows:
            return {
                "status": "no_data",
                "answer": (
                    f"A comparison for {crop} in {district}, Seasons "
                    f"{first_season} and {second_season} ({year}), is unavailable. "
                    "At least one record is missing; missing does not mean zero."
                ),
                "evidence": [],
                "source": SOURCE,
                "limitation": LIMITATION,
            }
        return compare_records(
            first_rows[0], second_rows[0],
            language=language, source=SOURCE, limitation=LIMITATION,
        )

    # Compare reported season subtotals when no district is specified.
    # This is intentionally separate from district-level record comparison.
    requested_seasons = _find_seasons(text)
    if (
        crop
        and not district
        and len(requested_seasons) >= 2
        and _asks_comparison(text)
    ):
        selected = []
        for season_code in requested_seasons[:2]:
            candidates = agriculture.production_summaries(
                season=season_code, crop=crop, year=year
            )
            summary = next(
                (item for item in candidates
                 if item.get("season") == season_code),
                candidates[0] if candidates else None,
            )
            if (
                summary is None
                or summary.get("reported_district_sum_mt") is None
            ):
                return {
                    "status": "no_data",
                    "answer": (
                        f"A reported-subtotal comparison for {crop}, Seasons "
                        f"{requested_seasons[0]} and {requested_seasons[1]} "
                        f"({year}), is unavailable because a required subtotal "
                        "is missing. Missing is not zero."
                    ),
                    "evidence": [dict(item) for item in selected],
                    "source": SOURCE,
                    "limitation": LIMITATION,
                }
            selected.append(dict(summary))

        first, second = selected
        first_total = float(first["reported_district_sum_mt"])
        second_total = float(second["reported_district_sum_mt"])
        difference = second_total - first_total
        first_season = first.get("season", requested_seasons[0])
        second_season = second.get("season", requested_seasons[1])

        first_coverage = (
            f"{first.get('reported_records', 'unknown')} of "
            f"{first.get('expected_districts_in_dataset', 'unknown')} districts"
        )
        second_coverage = (
            f"{second.get('reported_records', 'unknown')} of "
            f"{second.get('expected_districts_in_dataset', 'unknown')} districts"
        )
        language_rw = str(language or "en").casefold().strip() in {
            "rw", "kin", "kinyarwanda"
        }

        first_reported = first.get("reported_records")
        first_expected = first.get("expected_districts_in_dataset")
        second_reported = second.get("reported_records")
        second_expected = second.get("expected_districts_in_dataset")

        first_coverage_rw = (
            f"uturere {first_reported if first_reported is not None else 'ntibizwi'} "
            f"kuri {first_expected if first_expected is not None else 'ntibizwi'} "
            "twari dufite amakuru yatangajwe"
        )
        second_coverage_rw = (
            f"uturere {second_reported if second_reported is not None else 'ntibizwi'} "
            f"kuri {second_expected if second_expected is not None else 'ntibizwi'} "
            "twari dufite amakuru yatangajwe"
        )

        if difference > 0:
            direction_en = (
                f"Season {second_season} was higher than Season "
                f"{first_season} by {_number(difference)} metric tonnes."
            )
            direction_rw = (
                f"Igiteranyo cyo mu gihembwe {second_season} cyari kinini "
                f"ho toni {_number(difference)} ugereranyije n'icyo mu "
                f"gihembwe {first_season}."
            )
        elif difference < 0:
            direction_en = (
                f"Season {first_season} was higher than Season "
                f"{second_season} by {_number(abs(difference))} metric tonnes."
            )
            direction_rw = (
                f"Igiteranyo cyo mu gihembwe {first_season} cyari kinini "
                f"ho toni {_number(abs(difference))} ugereranyije n'icyo mu "
                f"gihembwe {second_season}."
            )
        else:
            direction_en = "The two reported subtotals were equal."
            direction_rw = "Ibyo biteranyo byombi byari bingana."

        if str(language or "en").casefold().strip() in {
            "rw", "kin", "kinyarwanda"
        }:
            crop_rw = {
                "maize": "ibigori", "beans": "ibishyimbo",
                "cassava": "imyumbati", "irish potatoes": "ibirayi",
                "sweet potatoes": "ibijumba", "banana": "ibitoki",
                "sorghum": "amasaka", "wheat": "ingano",
                "vegetables": "imboga",
            }.get(crop.casefold(), crop)
            answer = (
                f"Igiteranyo cy'imibare yatangajwe mu turere ku musaruro "
                f"w'{crop_rw} muri {year}: igihembwe {first_season}, toni "
                f"{_number(first_total)} ({first_coverage_rw if language_rw else first_coverage}); igihembwe "
                f"{second_season}, toni {_number(second_total)} "
                f"({second_coverage_rw if language_rw else second_coverage}).\n{direction_rw}\n"
                "Icyitonderwa: ibi ni ibiteranyo by'imibare yatangajwe "
                "n'uturere, si umusaruro wose w'igihugu wemejwe. "
                "Amakuru ashobora kutuzura cyangwa gutandukana mu bihembwe."
            )
        else:
            answer = (
                f"Reported district-value subtotals for {crop} in {year}: "
                f"Season {first_season}, {_number(first_total)} metric tonnes "
                f"({first_coverage}); Season {second_season}, "
                f"{_number(second_total)} metric tonnes ({second_coverage}).\n"
                f"{direction_en}\n"
                "These are sums of reported district values, not verified "
                "national totals. Data completeness or district coverage may "
                "differ between seasons, so interpret the comparison cautiously."
            )

        return {
            "status": "answered",
            "answer": answer,
            "evidence": selected,
            "source": SOURCE,
            "source_note": (
                "Seasonal subtotals are calculated from reported district values; "
                "they are not automatically equivalent to national totals."
            ),
            "limitation": LIMITATION,
            "comparison": {
                "crop": crop,
                "year": year,
                "previous_season": first_season,
                "previous_reported_district_sum_mt": first_total,
                "comparison_season": second_season,
                "comparison_reported_district_sum_mt": second_total,
                "difference_mt": difference,
                "absolute_difference_mt": abs(difference),
                "district_coverage_differs": (
                    first.get("reported_records")
                    != second.get("reported_records")
                    or first.get("expected_districts_in_dataset")
                    != second.get("expected_districts_in_dataset")
                ),
            },
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

    # Highest reported district, with natural Kinyarwanda wording.
    highest_terms = (
        "highest", "most", "top", "largest", "leading", "which district",
        "akahe karere", "akarere katanze", "byinshi", "umusaruro mwinshi",
        "byinshi kurusha", "ni akahe", "ku isonga", "yayoboye",
    )

    if crop and any(term in text for term in highest_terms):
        seasons_to_check = [season] if season else ["A", "B", "C"]
        leaders = []

        for season_code in seasons_to_check:
            origins = agriculture.supply_origins(
                crop=crop, season=season_code, year=year
            )
            ranked = [
                item for item in origins.get("districts", [])
                if item.get("rank") is not None
                and item.get("production_mt") is not None
            ]
            if ranked:
                leader = dict(ranked[0])
                leader.update({
                    "crop": crop,
                    "season": season_code,
                    "year": year,
                })
                leaders.append(leader)

        if not leaders:
            return {
                "status": "no_data",
                "answer": (
                    f"No reported district values were available for "
                    f"{crop}, {year}."
                ),
                "evidence": [],
                "source": SOURCE,
                "limitation": LIMITATION,
            }

        language_rw = language.casefold().strip() in {
            "rw", "kin", "kinyarwanda"
        }
        crop_rw = {
            "maize": "ibigori",
            "beans": "ibishyimbo",
            "cassava": "imyumbati",
            "irish potatoes": "ibirayi",
            "sweet potatoes": "ibijumba",
            "banana": "ibitoki",
            "sorghum": "amasaka",
            "wheat": "ingano",
            "vegetables": "imboga",
        }.get(crop.casefold(), crop)

        if season:
            leader = leaders[0]
            if language_rw:
                answer = (
                    f"Akarere ka {leader['district']} kagaragaje umusaruro "
                    f"munini kurusha utundi watangajwe w'{crop_rw} mu gihembwe "
                    f"{season} cya {year}: toni "
                    f"{_number(leader['production_mt'])}. "
                    "Ibi bigereranya imibare yatangajwe, si umusaruro w'ubu."
                )
            else:
                answer = (
                    f"{leader['district']} had the highest reported {crop} "
                    f"production in Season {season} {year}, at "
                    f"{_number(leader['production_mt'])} metric tonnes. "
                    "This ranks reported survey values, not current supply."
                )
        else:
            if language_rw:
                lines = [
                    f"Igihembwe {item['season']}: Akarere ka "
                    f"{item['district']} ni ko kagaragaje umusaruro "
                    f"munini watangajwe w'{crop_rw}, toni "
                    f"{_number(item['production_mt'])}."
                    for item in leaders
                ]
                answer = (
                    f"Uturere twagaragaje umusaruro munini w'{crop_rw} "
                    f"muri {year}, kuri buri gihembwe:\n"
                    + "\n".join(lines)
                    + "\n\nIcyitonderwa: ibi bihembwe byerekanwe ukwabyo; "
                    "ntibiteranyijwe ngo byitwe umusaruro wose w'umwaka."
                )
            else:
                lines = [
                    f"Season {item['season']}: {item['district']} had the "
                    f"highest reported value, "
                    f"{_number(item['production_mt'])} metric tonnes."
                    for item in leaders
                ]
                answer = (
                    f"Highest reported district for {crop} in {year}, "
                    "shown separately by season:\n"
                    + "\n".join(lines)
                    + "\n\nSeasons are not added together as an annual total."
                )

        return {
            "status": "answered",
            "answer": answer,
            "evidence": leaders,
            "source": SOURCE,
            "limitation": LIMITATION,
        }

    # If no season is specified, show the district's separate seasonal records.
    if crop and district and not season:
        rows = agriculture.filter_production(
            district=district, crop=crop, year=year
        )
        if rows:
            rows_by_season = {
                item.get("season"): item
                for item in rows
                if item.get("season") in {"A", "B", "C"}
            }
            evidence = [
                {
                    "district": item.get("district"),
                    "crop": item.get("crop"),
                    "season": item.get("season"),
                    "year": item.get("year"),
                    "season_period": item.get("season_period"),
                    "production_mt": item.get("production_mt"),
                    "source": item.get("source", SOURCE),
                    "source_table": item.get("source_table"),
                    "source_page": item.get("source_page"),
                    "value_status": item.get("source_value_status"),
                }
                for item in rows_by_season.values()
            ]

            language_rw = language.casefold().strip() in {
                "rw", "kin", "kinyarwanda"
            }
            crop_rw = {
                "maize": "ibigori",
                "beans": "ibishyimbo",
                "cassava": "imyumbati",
                "irish potatoes": "ibirayi",
                "sweet potatoes": "ibijumba",
                "banana": "ibitoki",
                "sorghum": "amasaka",
                "wheat": "ingano",
                "vegetables": "imboga",
            }.get(crop.casefold(), crop)

            lines = []
            for season_code in ("A", "B", "C"):
                item = rows_by_season.get(season_code)
                if item is None:
                    lines.append(
                        f"Igihembwe {season_code}: nta nyandiko iboneka."
                        if language_rw
                        else f"Season {season_code}: no record found."
                    )
                elif item.get("production_mt") is None:
                    lines.append(
                        f"Igihembwe {season_code}: umusaruro ntiwatangajwe; "
                        "kubura amakuru ntibivuze zeru."
                        if language_rw
                        else f"Season {season_code}: production was not reported; "
                        "missing does not mean zero."
                    )
                else:
                    lines.append(
                        f"Igihembwe {season_code}: toni "
                        f"{_number(item['production_mt'])}."
                        if language_rw
                        else f"Season {season_code}: "
                        f"{_number(item['production_mt'])} metric tonnes."
                    )

            if language_rw:
                answer = (
                    f"Umusaruro w'{crop_rw} mu karere ka {district} "
                    f"mu mwaka wa {year}:\n"
                    + "\n".join(lines)
                    + "\n\nIcyitonderwa: amakuru ya buri gihembwe atandukanye; "
                    "ntiyateranyijwe ngo yitwe igiteranyo cy'umwaka."
                )
            else:
                answer = (
                    f"Reported {crop} production in {district} during {year}:\n"
                    + "\n".join(lines)
                    + "\n\nSeasonal figures are listed separately, not summed "
                    "into an annual total."
                )

            return {
                "status": "answered",
                "answer": answer,
                "evidence": evidence,
                "source": SOURCE,
                "limitation": LIMITATION,
            }

    # General data-quality questions in English and Kinyarwanda.
    # Match against the original question as well as normalized text.
    # This prevents other intent processing from hiding quality keywords.
    quality_text = " ".join(
        f"{original} {text}".casefold()
        .replace("’", "'")
        .replace("‘", "'")
        .split()
    )

    quality_terms = (
        "data quality", "missing data", "missing records",
        "incomplete", "validation", "reliable", "reliability",
        "ubwiza bw'amakuru", "amakuru atuzuye", "amakuru abura",
        "imbogamizi z'ubwiza", "kwizerwa kw'amakuru",
        "ibibazo biri mu bwiza", "ibibazo by'ubwiza",
        "amakuru yizewe", "aya makuru yizewe",
        "ibura ry'amakuru", "amakuru adahagije",
    )
    is_quality_question = (
        any(term in quality_text for term in quality_terms)
        or (
            "amakuru" in quality_text
            and any(term in quality_text for term in (
                "ibibazo", "ubwiza", "kwizerwa", "atuzuye", "abura"
            ))
        )
    )
    if is_quality_question:
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

    if crop and season and _asks_district_count(text):
        summaries = agriculture.production_summaries(
            season=season, crop=crop, year=year
        )
        if not summaries:
            return {
                "status": "no_data",
                "answer": f"No reporting-district count is available for {crop}, Season {season} {year}.",
                "evidence": [],
                "source": SOURCE,
                "limitation": LIMITATION,
            }

        summary = summaries[0]
        reported = summary.get("reported_records")
        expected = summary.get("expected_districts_in_dataset")
        if reported is None or expected is None:
            status = "no_data"
            answer = f"A verified district count is unavailable for {crop}, Season {season} {year}."
        elif language.casefold().strip() in {"rw", "kin", "kinyarwanda"}:
            crop_rw = _KINYARWANDA_CROPS.get(crop.casefold(), crop)
            status = "answered"
            answer = (
                f"Mu gihembwe {season} cya {year}, uturere {reported} kuri "
                f"{expected} twari dufite amakuru yatangajwe y'umusaruro "
                f"w'{crop_rw}. Iyi ni imibare y'uturere, si igiteranyo cya toni."
            )
        else:
            status = "answered"
            answer = (
                f"For {crop}, Season {season} {year}, {reported} of {expected} "
                "districts had a reported production value. This is a reporting "
                "count, not a production total."
            )

        return {
            "status": status,
            "answer": answer,
            "evidence": [summary],
            "source": SOURCE,
            "limitation": summary.get("interpretation_note", LIMITATION),
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
    if (
        result.get("status") != "answered"
        or len(evidence) != 1
        or not isinstance(evidence[0], dict)
    ):
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

    # Safety priority: do not let previous context turn a price/weather
    # request into an answer about the last crop production record.
    # Official weather/disaster requests must never be answered with price data.
    if _is_unsupported_environment_request(original):
        return _unsupported_response(language_code)

    # Prefer a directly observed Esoko row when product and market match.
    # The handler returns None when this snapshot cannot safely answer, allowing
    # the existing TangaBid monthly-summary route to handle the question.
    esoko_result = esoko_source.answer_question(
        original,
        language_code,
        explicit_price_type_only=True,
    )
    if esoko_result is not None:
        return esoko_result

    # Existing TangaBid monthly price summaries remain a separate fallback source.
    market_result = _answer_market_price_question(original, language_code)
    if market_result is not None:
        return market_result

    if _is_unsupported_request(original):
        return _unsupported_response(language_code)

    # Early, explicit dispatch for data-quality questions.
    quality_text = " ".join(
        original.casefold().replace("’", "'").replace("‘", "'").split()
    )
    quality_words = set(
        quality_text.replace("'", " ").replace("?", " ").replace(".", " ").split()
    )
    is_quality_question = (
        {"amakuru", "bibazo", "bwiza"}.issubset(quality_words)
        or {"amakuru", "ubwiza"}.issubset(quality_words)
        or {"amakuru", "kwizerwa"}.issubset(quality_words)
        or {"amakuru", "atuzuye"}.issubset(quality_words)
        or {"amakuru", "abura"}.issubset(quality_words)
        or bool(quality_words & {
            "yizewe", "atuzuye", "abura", "kwizerwa", "adahagije"
        })
        or any(term in quality_text for term in (
            "data quality", "missing data", "missing records",
            "incomplete", "validation", "reliability",
            "amakuru yizewe", "amakuru atuzuye", "amakuru abura",
            "makuru atuzuye", "makuru abura",
            "kwizerwa kw'amakuru", "ubwiza bw'amakuru",
        ))
    )
    if is_quality_question:
        quality = agriculture.data_quality()
        counts = quality["status_counts"]
        counts_text = ", ".join(
            f"{name}: {count}" for name, count in counts.items()
        )
        if language_code in {"rw", "kin", "kinyarwanda"}:
            quality_labels_rw = {
                "INCOMPLETE_DISTRICT_DATA": "Amakuru y'uturere atuzuye",
                "SMALL_DIFFERENCE_REVIEW": "Itandukaniro rito rigomba gusuzumwa",
                "MATCH": "Imibare ihuye",
                "LARGE_DIFFERENCE_REVIEW": "Itandukaniro rinini rigomba gusuzumwa",
            }
            counts_text_rw = ", ".join(
                f"{quality_labels_rw.get(name, name)}: {count}"
                for name, count in counts.items()
            )
            answer = (
                f"Igenzura ry'ubwiza bw'amakuru ryasuzumye "
                f"inyandiko {quality['records_returned']}. "
                f"Ibyiciro byabonetse: {counts_text_rw}. "
                "Ibi ni ibyavuye mu igenzura ry'amakuru, "
                "si igipimo cy'ibyago by'ubuhinzi."
            )
        else:
            answer = (
                f"The data-quality check examined "
                f"{quality['records_returned']} validation records. "
                f"Status counts: {counts_text}. These are data-quality "
                "findings, not agricultural risk levels."
            )
        return {
            "status": "answered",
            "answer": answer,
            "evidence": [{
                "records_returned": quality["records_returned"],
                "status_counts": counts,
            }],
            "source": quality.get("source", SOURCE),
            "limitation": quality.get("note"),
        }


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

    # Prefer rule-based intent handling and verified local data first.
    # The question bank is a fallback, not an override for supported intents.
    result = _rule_based_answer_question(original, language_code)

    if stored and result.get("status") in {
        "no_data", "needs_clarification"
    }:
        stored_response = stored.get("response")
        if (
            isinstance(stored_response, dict)
            and stored_response.get("status") == "answered"
        ):
            result = stored_response

    if language_code in {"rw", "kin", "kinyarwanda"}:
        result = _localize_district_production(result)

    return result
