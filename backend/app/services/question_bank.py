"""Persistent, evidence-backed question bank for MENYA NEZA AI."""

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BANK_FILE = PROJECT_ROOT / "data" / "knowledge" / "nisr_sas_2025_question_bank.jsonl"

SOURCE = "NISR Seasonal Agricultural Survey 2025"
LIMITATION = (
    "These are historical survey records, not live market prices, "
    "current production estimates, weather forecasts, or official disaster warnings."
)


def normalize_question(value: str) -> str:
    """Normalize case and punctuation for exact question matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", value.casefold())).strip()


def _language_code(language: str | None) -> str | None:
    if not language:
        return None
    language = language.casefold().strip()
    if language in {"rw", "kin", "kinyarwanda"}:
        return "rw"
    if language in {"en", "eng", "english"}:
        return "en"
    return language


@lru_cache(maxsize=1)
def load_question_bank() -> tuple[dict[str, Any], ...]:
    """Load generated question-and-answer entries from persistent JSONL."""
    if not BANK_FILE.is_file():
        return ()

    entries: list[dict[str, Any]] = []
    with BANK_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid question-bank JSON at line {line_number}: {exc}"
                ) from exc

            if (
                isinstance(entry, dict)
                and isinstance(entry.get("question"), str)
                and isinstance(entry.get("response"), dict)
            ):
                entries.append(entry)

    return tuple(entries)


@lru_cache(maxsize=1)
def _question_index() -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in load_question_bank():
        key = (
            entry.get("language", "en"),
            normalize_question(entry["question"]),
        )
        index.setdefault(key, entry)
    return index


def lookup_question(
    question: str,
    language: str | None = None,
) -> dict[str, Any] | None:
    """Retrieve an exact stored question and its evidence-backed answer."""
    normalized = normalize_question(question)
    if not normalized:
        return None

    code = _language_code(language)
    index = _question_index()

    if code:
        entry = index.get((code, normalized))
        if entry:
            return entry

    # Language-neutral lookup is useful for the API and internal tooling.
    for candidate in ("en", "rw"):
        entry = index.get((candidate, normalized))
        if entry:
            return entry

    return None


def search_questions(
    query: str = "",
    language: str = "en",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find stored question entries by query words and language."""
    code = _language_code(language) or "en"
    tokens = normalize_question(query).split()
    limit = max(1, min(int(limit), 100))

    matches = []
    for entry in load_question_bank():
        if entry.get("language") != code:
            continue

        normalized = normalize_question(entry["question"])
        if tokens and not all(token in normalized for token in tokens):
            continue

        matches.append({
            "id": entry.get("id"),
            "question": entry["question"],
            "language": entry.get("language"),
            "intent": entry.get("intent"),
            "answer": entry["response"].get("answer"),
            "response": entry["response"],
        })

        if len(matches) >= limit:
            break

    return matches


def question_bank_stats() -> dict[str, Any]:
    entries = load_question_bank()
    languages = Counter(
        entry.get("language", "unknown") for entry in entries
    )
    source_records = {
        entry.get("record_key")
        for entry in entries
        if entry.get("record_key")
    }

    return {
        "status": "ready" if entries else "not_built",
        "source": SOURCE,
        "total_questions": len(entries),
        "source_records": len(source_records),
        "by_language": dict(sorted(languages.items())),
        "storage_format": "JSONL",
        "last_generated": (
            __import__("datetime").datetime.fromtimestamp(
                BANK_FILE.stat().st_mtime
            ).astimezone().isoformat(timespec="seconds")
            if BANK_FILE.is_file() else None
        ),
        "limitation": LIMITATION,
    }
