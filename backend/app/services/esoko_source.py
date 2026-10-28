"""Esoko Rwanda price observations from an explicitly dated CSV export.

This is a source-observation service, not a live scraping client. The source export
does not contain product units; answers must keep that limitation visible.
"""
from __future__ import annotations

import csv
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

SOURCE_NAME = "Esoko Rwanda eSoko Price Trends"
SOURCE_URL = "https://esoko.rw/price-trends"
DATASET_RELATIVE_PATH = Path("data/processed/esoko_market_price_observations.csv")
_PRICE_INTENT = (
    "price", "prices", "cost", "costs", "igiciro", "ibiciro", "ikiguzi",
    "kabura", "how much is", "how much was", "how much does",
    "farmgate", "farm gate", "wholesale", "retail",
)
_PRICE_COLUMNS = {
    "farmgate": "farmgate_price_rwf",
    "wholesale": "wholesale_price_rwf",
    "retail": "retail_price_rwf",
}
_ALIASES = {
    "maize flour": "maize_flour",
    "corn flour": "maize_flour",
    "akawunga": "maize_flour",
    "ifu y ibigori": "maize_flour",
    "maize": "maize",
    "corn": "maize",
    "ibigori": "maize",
    "cassava flour": "cassava_flour",
    "ifu yimyumbati": "cassava_flour",
    "rice": "rice",
    "umuceri": "rice",
    "umuceli": "rice",
    "beans": "beans",
    "ibishyimbo": "beans",
    "tomato": "tomato",
    "tomatoes": "tomato",
    "inyanya": "tomato",
    "banana": "banana",
    "bananas": "banana",
    "avocado": "avocado",
    "avocados": "avocado",
    "avoka": "avocado",
    "potato": "potato",
    "potatoes": "potato",
    "ibirayi": "potato",
    "cassava": "cassava",
    "imyumbati": "cassava",
    "sugar": "sugar",
    "isukari": "sugar",
    "onion": "onion",
    "onions": "onion",
    "ibitunguru": "onion",
    "carrot": "carrot",
    "carrots": "carrot",
    "karoti": "carrot",
}
_ALIAS_MATCH = {
    "maize_flour": lambda p: "ifu" in _norm(p) and "ibigori" in _norm(p),
    "maize": lambda p: _norm(p) == "ibigori",
    "cassava_flour": lambda p: "ifu" in _norm(p) and "imyumbati" in _norm(p),
    "rice": lambda p: any(t in _norm(p).split() for t in ("umuceri", "umuceli", "rice")),
    "beans": lambda p: "ibishyimbo" in _norm(p) or "bean" in _norm(p).split(),
    "tomato": lambda p: "inyanya" in _norm(p).split() or "tomato" in _norm(p).split(),
    "banana": lambda p: any(t in _norm(p).split() for t in ("banana", "imineke", "igitoki")),
    "avocado": lambda p: any(t in _norm(p).split() for t in ("avoka", "avocado")),
    "potato": lambda p: "ibirayi" in _norm(p).split() or "potato" in _norm(p).split(),
    "cassava": lambda p: "imyumbati" in _norm(p).split(),
    "sugar": lambda p: "isukari" in _norm(p).split() or "sugar" in _norm(p).split(),
    "onion": lambda p: "ibitunguru" in _norm(p).split() or "onion" in _norm(p).split(),
    "carrot": lambda p: "karoti" in _norm(p).split() or "carrot" in _norm(p).split(),
}
_MONTHS = {
    "jan": 1, "january": 1, "mutarama": 1,
    "feb": 2, "february": 2, "gashyantare": 2,
    "mar": 3, "march": 3, "werurwe": 3,
    "apr": 4, "april": 4, "mata": 4,
    "may": 5, "gicurasi": 5,
    "jun": 6, "june": 6, "kamena": 6,
    "jul": 7, "july": 7, "nyakanga": 7,
    "aug": 8, "august": 8, "kanama": 8,
    "sep": 9, "sept": 9, "september": 9, "nzeri": 9,
    "oct": 10, "october": 10, "ukwakira": 10,
    "nov": 11, "november": 11, "ugushyingo": 11,
    "dec": 12, "december": 12, "ukuboza": 12,
}


def _norm(value: Any) -> str:
    value = str(value or "").casefold().replace("’", "'").replace("‘", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _data_path() -> Path:
    override = os.environ.get("MENYA_NEZA_ESOKO_DATA_PATH")
    if override:
        return Path(override).expanduser()
    # services/esoko_source.py -> services -> app -> backend -> repository root
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / DATASET_RELATIVE_PATH


def _to_number(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return int(number) if number.is_integer() else number


@lru_cache(maxsize=4)
def _load_cached(path_text: str, mtime_ns: int) -> tuple[dict[str, Any], ...]:
    path = Path(path_text)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = dict(raw)
            for field in _PRICE_COLUMNS.values():
                row[field] = _to_number(row.get(field))
            row["market"] = str(row.get("market") or "").strip()
            row["product_name"] = str(row.get("product_name") or "").strip()
            row["product_name_en"] = str(row.get("product_name_en") or "").strip()
            rows.append(row)
    return tuple(rows)


def load_observations() -> list[dict[str, Any]]:
    """Load the normalized export, refreshing the cache when the file changes."""
    path = _data_path()
    if not path.is_file():
        raise FileNotFoundError(f"Esoko source dataset not found: {path}")
    return [dict(row) for row in _load_cached(str(path), path.stat().st_mtime_ns)]


def source_status() -> dict[str, Any]:
    """Return source coverage and quality notes for the Market Intelligence UI."""
    try:
        rows = load_observations()
    except (OSError, csv.Error) as exc:
        return {
            "available": False,
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "error": str(exc),
            "records": 0,
        }

    dates = sorted(str(row.get("observed_at") or "") for row in rows if row.get("observed_at"))
    products = sorted({str(row.get("product_name_en") or row.get("product_name")) for row in rows})
    markets = sorted({str(row.get("market")) for row in rows if row.get("market")})
    missing = {
        field: sum(row.get(field) in (None, "") for row in rows)
        for field in (
            "farmgate_price_rwf", "wholesale_price_rwf", "retail_price_rwf",
            "unit", "province", "district",
        )
    }
    return {
        "available": True,
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dataset_file": str(DATASET_RELATIVE_PATH),
        "snapshot_observation_start": dates[0] if dates else None,
        "snapshot_observation_end": dates[-1] if dates else None,
        "records": len(rows),
        "distinct_products": len(products),
        "distinct_markets": len(markets),
        "products": products,
        "markets": markets,
        "missing_values": missing,
        "currency": "RWF",
        "currency_basis": (
            "Published descriptions of Esoko price data use Rwandan francs; "
            "currency is not a column in this particular export."
        ),
        "unit_status": "NOT_PROVIDED_IN_EXPORT",
        "limitations": [
            "This is a downloaded CSV snapshot, not a live connection to Esoko.",
            "The CSV has no product unit field; do not assume per kg, litre, piece, or other unit.",
            "Province and district are blank in the supplied export.",
            "A dash or blank price is missing information, not zero.",
            "Repeated identical source rows are retained for traceability.",
        ],
    }


def search_observations(
    product: str | None = None,
    location: str | None = None,
    price_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Filter source observations while retaining their timestamps and provenance."""
    rows = load_observations()
    if price_type:
        price_type = _norm(price_type).replace(" ", "")
        if price_type not in _PRICE_COLUMNS:
            raise ValueError("price_type must be farmgate, wholesale, or retail")
    pnorm, lnorm = _norm(product), _norm(location)
    product_labels = {
        _norm(row.get("product_name_en") or row.get("product_name"))
        for row in rows
    }
    exact_product_query = bool(pnorm and pnorm in product_labels)
    filtered = []
    for row in rows:
        row_product = _norm(row.get("product_name_en") or row.get("product_name"))
        row_native = _norm(row.get("product_name"))
        if pnorm:
            if exact_product_query:
                if row_product != pnorm and row_native != pnorm:
                    continue
            elif pnorm not in row_product and pnorm not in row_native:
                continue
        if lnorm and lnorm not in _norm(row.get("market")):
            continue
        result = dict(row)
        if price_type:
            result["selected_price_type"] = price_type
            result["selected_price_rwf"] = row.get(_PRICE_COLUMNS[price_type])
        filtered.append(result)

    filtered.sort(key=lambda row: str(row.get("observed_at") or ""), reverse=True)
    safe_limit = max(1, min(int(limit), 1000))
    safe_offset = max(0, int(offset))
    status = source_status()
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "snapshot": True,
        "live_feed": False,
        "currency": "RWF",
        "unit_status": "NOT_PROVIDED_IN_EXPORT",
        "filters": {"product": product, "location": location, "price_type": price_type},
        "total_source_records": len(rows),
        "total_matching_records": len(filtered),
        "limit": safe_limit,
        "offset": safe_offset,
        "coverage": {
            "observation_start": status.get("snapshot_observation_start"),
            "observation_end": status.get("snapshot_observation_end"),
            "distinct_products": status.get("distinct_products"),
            "distinct_markets": status.get("distinct_markets"),
        },
        "limitations": status.get("limitations", []),
        "records": filtered[safe_offset:safe_offset + safe_limit],
    }


def _phrase_in_question(phrase: str, question_normalized: str) -> bool:
    phrase_normalized = _norm(phrase)
    return bool(phrase_normalized and re.search(
        r"(?<![a-z0-9])" + re.escape(phrase_normalized) + r"(?![a-z0-9])",
        question_normalized,
    ))


def _market_price_intent(question: str) -> bool:
    q = _norm(question)
    return any(_phrase_in_question(marker, q) for marker in _PRICE_INTENT)


def _find_date(question: str) -> str | None:
    q = _norm(question)
    iso = re.search(r"\b(20\d{2}) (\d{1,2}) (\d{1,2})\b", q)
    if iso:
        year, month, day = map(int, iso.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    for month_name, month in _MONTHS.items():
        match = re.search(rf"\b{re.escape(month_name)} (\d{{1,2}})(?: (20\d{{2}}))?\b", q)
        if match:
            day = int(match.group(1))
            year = int(match.group(2) or 2026)
            if 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
        match = re.search(rf"\b(\d{{1,2}}) {re.escape(month_name)} (20\d{{2}})\b", q)
        if match:
            day, year = map(int, match.groups())
            if 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _price_kind(question: str) -> str | None:
    q = _norm(question)
    if _phrase_in_question("farmgate", q) or _phrase_in_question("farm gate", q):
        return "farmgate"
    if _phrase_in_question("wholesale", q):
        return "wholesale"
    if _phrase_in_question("retail", q):
        return "retail"
    return None


def _resolve_product(question: str, market_rows: list[dict[str, Any]]) -> tuple[list[str], bool]:
    q = _norm(question)
    options = sorted({
        str(row.get("product_name_en") or row.get("product_name"))
        for row in market_rows
        if row.get("product_name_en") or row.get("product_name")
    })
    # Exact source names win. Require the complete name, so "Ibigori" does not
    # silently match a particular maize-flour variety as well.
    exact = [name for name in options if _phrase_in_question(name, q)]
    if exact:
        exact.sort(key=lambda name: len(_norm(name)), reverse=True)
        longest = len(_norm(exact[0]))
        return [name for name in exact if len(_norm(name)) == longest], False

    alias_key = None
    for alias, key in sorted(_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _phrase_in_question(alias, q):
            alias_key = key
            break
    if not alias_key:
        return [], False
    matcher = _ALIAS_MATCH.get(alias_key)
    if matcher is None:
        return [], False
    matches = [name for name in options if matcher(name)]
    return matches, len(matches) > 1


def _human_time(value: str) -> str:
    # Source timestamps are ISO strings with their original +02:00 offset.
    try:
        from datetime import datetime
        return datetime.fromisoformat(value).strftime("%d %b %Y %H:%M %z")
    except (TypeError, ValueError):
        return value


def answer_question(
    question: str,
    language: str = "en",
    *,
    explicit_price_type_only: bool = False,
) -> dict[str, Any] | None:
    """Answer when this snapshot has a precise product+market observation.

    Return None for questions better handled by other available sources or routes.
    Environmental safety routing is performed by the main Ask AI service before
    this function is called.
    """
    q = str(question or "").strip()
    if not _market_price_intent(q):
        return None

    # Direct callers may query a local product without naming the price tier.
    # The main Ask AI route can require an explicit Esoko price tier so generic
    # historical-price questions continue to use TangaBid.
    if explicit_price_type_only and _price_kind(q) is None:
        return None

    # A month/year historical request must not receive the latest Esoko
    # snapshot as if it were an observation from the requested month.
    normalized_question = _norm(q)
    month_names = "|".join(
        re.escape(name) for name in sorted(_MONTHS, key=len, reverse=True)
    )
    month_year_pattern = (
        rf"\b(?:{month_names})\s+20\d{{2}}\b"
        rf"|\b20\d{{2}}\s+(?:{month_names})\b"
    )
    if re.search(month_year_pattern, normalized_question):
        return None

    is_rw = str(language or "en").casefold().strip() in {"rw", "kin", "kinyarwanda"}

    try:
        rows = load_observations()
    except (OSError, csv.Error):
        return None

    qnorm = _norm(q)
    market_names = sorted(
        {str(row.get("market") or "") for row in rows if row.get("market")},
        key=lambda value: len(_norm(value)),
        reverse=True,
    )
    matched_markets = [m for m in market_names if _phrase_in_question(m, qnorm)]
    if len(matched_markets) != 1:
        return None
    market = matched_markets[0]
    market_rows = [row for row in rows if _norm(row.get("market")) == _norm(market)]

    product_names, alias_ambiguous = _resolve_product(q, market_rows)
    if not product_names:
        return None
    requested_date = _find_date(q)
    if requested_date:
        market_rows = [
            row for row in market_rows
            if str(row.get("observed_date") or "") == requested_date
        ]
    matched_rows = [
        row for row in market_rows
        if str(row.get("product_name_en") or row.get("product_name")) in product_names
    ]
    if not matched_rows:
        return None

    # When a generic name resolves to several variants at this market, do not
    # silently pick one. Return real candidate rows and ask for the exact variety.
    unique_products = sorted({str(row.get("product_name_en") or row.get("product_name")) for row in matched_rows})
    if len(unique_products) > 1:
        candidates = []
        for name in unique_products[:8]:
            product_rows = [r for r in matched_rows if str(r.get("product_name_en") or r.get("product_name")) == name]
            latest = max(product_rows, key=lambda row: str(row.get("observed_at") or ""))
            candidates.append({
                "product_name": name,
                "market": market,
                "observed_at": latest.get("observed_at"),
                "farmgate_price_rwf": latest.get("farmgate_price_rwf"),
                "wholesale_price_rwf": latest.get("wholesale_price_rwf"),
                "retail_price_rwf": latest.get("retail_price_rwf"),
                "currency": "RWF",
                "unit": None,
                "unit_status": "NOT_PROVIDED_IN_EXPORT",
            })
        answer = (
            "This market lists several varieties matching that product. Please specify one: "
            + ", ".join(unique_products[:8]) + "."
        )
        if is_rw:
            answer = (
                "Iri soko rifite ubwoko bwinshi buhuye n'icyo gicuruzwa. Sobanura ubwoko ushaka: "
                + ", ".join(unique_products[:8]) + "."
            )
        return {
            "status": "needs_clarification",
            "answer": answer,
            "evidence": candidates,
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "limitation": "The export omits product units and is a dated snapshot, not a live feed.",
        }

    matched_rows.sort(key=lambda row: str(row.get("observed_at") or ""), reverse=True)
    latest_time = str(matched_rows[0].get("observed_at") or "")
    at_latest = [r for r in matched_rows if str(r.get("observed_at") or "") == latest_time]

    # Collapse identical repeated rows but flag conflicting rows at the same time.
    fingerprint = lambda r: tuple(r.get(field) for field in (
        "farmgate_price_rwf", "wholesale_price_rwf", "retail_price_rwf", "unit"
    ))
    distinct_latest = {fingerprint(r) for r in at_latest}
    if len(distinct_latest) > 1:
        return {
            "status": "needs_clarification",
            "answer": (
                "The export contains different values for the same product, market, and timestamp. "
                "I won't choose one arbitrarily."
                if not is_rw else
                "Iyi CSV ifite imibare itandukanye y'igicuruzwa kimwe, isoko n'igihe kimwe. "
                "Sinahitamo umubare umwe uko bishakiye."
            ),
            "evidence": at_latest[:8],
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "limitation": "Conflicting duplicate timestamp observations require source review.",
        }
    row = at_latest[0]
    product = str(row.get("product_name_en") or row.get("product_name"))
    kind = _price_kind(q)
    observed = _human_time(latest_time)
    prices = {name: row.get(field) for name, field in _PRICE_COLUMNS.items()}
    value = prices.get(kind) if kind else None
    if kind and value is None:
        return {
            "status": "no_data",
            "answer": (
                f"The export has no {kind} price recorded for {product} at {market} "
                f"at {observed}; a missing value does not mean zero."
                if not is_rw else
                f"Nta giciro cya {kind} cyanditswe kuri {product} i {market} "
                f"ku {observed}; kubura k'umubare ntibivuga ko ari zeru."
            ),
            "evidence": [{
                "product_name": product,
                "market": market,
                "observed_at": latest_time,
                "requested_price_type": kind,
                "currency": "RWF",
                "unit": None,
                "unit_status": "NOT_PROVIDED_IN_EXPORT",
                "source_record_id": row.get("source_record_id"),
            }],
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "limitation": "This export does not provide a unit and the price requested is missing.",
        }

    def show_price(v: Any) -> str:
        return "not reported" if v is None else f"RWF {v}"

    if kind:
        answer = (
            f"The latest matching Esoko export observation for {product} at {market} "
            f"was recorded {observed}: {kind} price {show_price(value)}."
        )
        if is_rw:
            answer = (
                f'Amakuru ya Esoko ahuye n’iki kibazo kuri {product} i {market} '
                f'yanditswe ku {observed}: igiciro cya {kind} ni {show_price(value)}.'
            )
    else:
        answer = (
            f"The latest matching Esoko export observation for {product} at {market} "
            f"was recorded {observed}: farmgate {show_price(prices['farmgate'])}, "
            f"wholesale {show_price(prices['wholesale'])}, and retail {show_price(prices['retail'])}."
        )
        if is_rw:
            answer = (
                f'Amakuru ya Esoko aheruka ahuye n’iki kibazo kuri {product} i {market} '
                f'yanditswe ku {observed}: ku muhinzi {show_price(prices["farmgate"])}, '
                f'ku mucuruzi ucuruza byinshi {show_price(prices["wholesale"])}, '
                f'no ku baguzi {show_price(prices["retail"])}.'
            )

    answer += (
        " The downloaded export does not report the product unit, so do not assume per kg, litre, piece, or another unit. "
        "This is a dated source observation, not a guaranteed live price."
    )
    # Kinyarwanda caveat appended explicitly for the localized response as well.
    if is_rw:
        answer = answer.split(" The downloaded export does not report")[0] + (
            " Iyi CSV ntiyerekana igipimo cy'igicuruzwa; ntitwemeza ko ari kuri kg, litiro, igice cyangwa ikindi gipimo. "
            "Ni amakuru yanditswe mu gihe cyashize, si igiciro cy'ako kanya cyemejwe."
        )

    evidence = {
        "source_record_id": row.get("source_record_id"),
        "product_name": product,
        "product_name_native": row.get("product_name"),
        "market": market,
        "observed_at": latest_time,
        "observed_date": row.get("observed_date"),
        "farmgate_price_rwf": prices["farmgate"],
        "wholesale_price_rwf": prices["wholesale"],
        "retail_price_rwf": prices["retail"],
        "requested_price_type": kind,
        "requested_price_rwf": value if kind else None,
        "currency": "RWF",
        "currency_basis": row.get("currency_basis"),
        "unit": None,
        "unit_status": "NOT_PROVIDED_IN_EXPORT",
        "province": row.get("province") or None,
        "district": row.get("district") or None,
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_file": str(DATASET_RELATIVE_PATH),
        "live_price_verified": False,
        "forecast_produced": False,
    }
    return {
        "status": "answered",
        "answer": answer,
        "evidence": [evidence],
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_note": (
            "Esoko CSV export snapshot; observation timestamp is retained per row. "
            "This is not a live API connection."
        ),
        "limitation": (
            "Product units, province and district are not provided in the supplied export. "
            "Currency is based on public descriptions of Esoko data, not an explicit column in this CSV."
        ),
        "price_observation": {
            "product": product,
            "market": market,
            "observed_at": latest_time,
            "observed_date": row.get("observed_date"),
            "farmgate_price_rwf": prices["farmgate"],
            "wholesale_price_rwf": prices["wholesale"],
            "retail_price_rwf": prices["retail"],
            "requested_price_type": kind,
            "requested_price_rwf": value if kind else None,
            "currency": "RWF",
            "unit": None,
            "unit_status": "NOT_PROVIDED_IN_EXPORT",
            "live_price_verified": False,
        },
    }
