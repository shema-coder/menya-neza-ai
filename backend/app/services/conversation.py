"""Conversation context helpers for evidence-grounded agricultural answers."""

import re
from typing import Any


def latest_record_context(
    conversation: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Find the latest previous answer containing a district crop record."""
    if not isinstance(conversation, list):
        return None

    for turn in reversed(conversation[-6:]):
        if not isinstance(turn, dict):
            continue

        result = turn.get("result")
        if not isinstance(result, dict):
            continue

        evidence = result.get("evidence", [])
        if not isinstance(evidence, list):
            continue

        for row in evidence:
            if not isinstance(row, dict):
                continue

            required = ("district", "crop", "season", "year")
            if all(row.get(key) is not None for key in required):
                return row

    return None


def comparison_requested(question: str) -> bool:
    """Recognize common comparison and difference follow-ups."""
    text = re.sub(r"\s+", " ", question.casefold())

    phrases = (
        "compare that",
        "compare with",
        "compared with",
        "higher than",
        "lower than",
        "more than",
        "less than",
        "greater than",
        "difference",
        "was that higher",
        "was that lower",
        "gereranya",
        "ugereranyije",
        "kurusha",
        "itandukaniro",
        "byinshi ugereranyije",
    )
    return any(phrase in text for phrase in phrases)


def is_contextual_follow_up(
    question: str,
    *,
    crop: str | None,
    district: str | None,
    season: str | None,
) -> bool:
    """Avoid rewriting complete questions or broad seasonal comparisons."""
    text = re.sub(r"\s+", " ", question.casefold()).strip()

    if not text:
        return False

    # A complete district/crop/season question already contains its entities.
    if crop and district and season and not comparison_requested(text):
        return False

    # Preserve full requests to compare a crop across all seasons.
    broad_comparison_phrases = (
        "across seasons",
        "between seasons",
        "all seasons",
        "seasonal comparison",
        "mu bihembwe bya",
        "mu bihembwe bitandukanye",
    )
    if crop and any(
        phrase in text for phrase in broad_comparison_phrases
    ):
        return False

    follow_up_phrases = (
        "what about",
        "how about",
        "and season",
        "and in season",
        "compare that",
        "compare with",
        "was that",
        "higher than",
        "lower than",
        "more than",
        "less than",
        "what about that",
        "none se",
        "bimeze bite",
        "gereranya",
        "ugereranyije",
        "kurusha",
        "igihembwe",
        "gihembwe",
    )

    if any(phrase in text for phrase in follow_up_phrases):
        return True

    # A short message such as "Season A?" is also a likely follow-up.
    words = text.split()
    return bool(
        season
        and not crop
        and not district
        and len(words) <= 6
    )


def _format_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def _evidence_record(row: dict[str, Any], source: str) -> dict[str, Any]:
    """Keep only the source-backed fields used in a comparison."""
    return {
        "district": row.get("district"),
        "crop": row.get("crop"),
        "season": row.get("season"),
        "year": row.get("year"),
        "season_period": row.get("season_period"),
        "production_mt": row.get("production_mt"),
        "source": row.get("source") or source,
        "source_table": row.get("source_table"),
        "source_page": row.get("source_page"),
        "value_status": row.get("source_value_status")
        or row.get("value_status"),
    }


def compare_records(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    language: str = "en",
    source: str,
    limitation: str,
) -> dict[str, Any]:
    """Compare two verified district crop records."""
    previous_value = previous.get("production_mt")
    current_value = current.get("production_mt")
    previous_season = previous.get("season")
    current_season = current.get("season")
    district = previous.get("district")
    crop = previous.get("crop")
    year = previous.get("year")

    evidence = [
        _evidence_record(previous, source),
        _evidence_record(current, source),
    ]

    if previous_value is None or current_value is None:
        answer = (
            f"One of the reported values for {district}'s {crop} production "
            f"in Seasons {previous_season} and {current_season} was missing. "
            "The comparison cannot be calculated reliably; missing is not zero."
        )
        if language.casefold() in {"rw", "kin", "kinyarwanda"}:
            answer = (
                f"Umubare w'umusaruro w'{crop} mu karere ka {district} "
                f"ntiwuzuye mu bihembwe {previous_season} na {current_season}. "
                "Ntabwo bishoboka kubara itandukaniro ryizewe; kubura "
                "kw'umubare ntibisobanura ko umusaruro wari zeru."
            )

        return {
            "status": "no_data",
            "answer": answer,
            "evidence": evidence,
            "source": source,
            "limitation": limitation,
        }

    previous_number = float(previous_value)
    current_number = float(current_value)
    difference = previous_number - current_number
    amount = _format_number(abs(difference))

    if difference > 0:
        en_answer = (
            f"For {district}, reported {crop} production in Season "
            f"{previous_season} was higher than Season {current_season} "
            f"by {amount} metric tonnes "
            f"({ _format_number(previous_number) } versus "
            f"{ _format_number(current_number) })."
        )
        rw_answer = (
            f"Mu karere ka {district}, umusaruro w' {crop} watangajwe "
            f"mu gihembwe {previous_season} warenze uw'igihembwe "
            f"{current_season}ho toni {amount} "
            f"({_format_number(previous_number)} ugereranyije na "
            f"{_format_number(current_number)})."
        )
    elif difference < 0:
        en_answer = (
            f"For {district}, reported {crop} production in Season "
            f"{current_season} was higher than Season {previous_season} "
            f"by {amount} metric tonnes "
            f"({ _format_number(current_number) } versus "
            f"{ _format_number(previous_number) })."
        )
        rw_answer = (
            f"Mu karere ka {district}, umusaruro w' {crop} watangajwe "
            f"mu gihembwe {current_season} warenze uw'igihembwe "
            f"{previous_season}ho toni {amount} "
            f"({_format_number(current_number)} ugereranyije na "
            f"{_format_number(previous_number)})."
        )
    else:
        en_answer = (
            f"For {district}, reported {crop} production was the same "
            f"in Seasons {previous_season} and {current_season}: "
            f"{_format_number(previous_number)} metric tonnes in each."
        )
        rw_answer = (
            f"Mu karere ka {district}, umusaruro w' {crop} watangajwe "
            f"wari ungana mu bihembwe {previous_season} na {current_season}: "
            f"toni {_format_number(previous_number)} muri buri gihembwe."
        )

    language_code = language.casefold().strip()
    answer = (
        rw_answer
        if language_code in {"rw", "kin", "kinyarwanda"}
        else en_answer
    )

    return {
        "status": "answered",
        "answer": answer,
        "evidence": evidence,
        "source": source,
        "source_note": (
            "Calculated from the two reported district-level survey records. "
            "This is a historical comparison, not a live production estimate."
        ),
        "limitation": limitation,
        "comparison": {
            "district": district,
            "crop": crop,
            "year": year,
            "previous_season": previous_season,
            "previous_production_mt": previous_number,
            "comparison_season": current_season,
            "comparison_production_mt": current_number,
            "difference_mt": difference,
        },
    }
