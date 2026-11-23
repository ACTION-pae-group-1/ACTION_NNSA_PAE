"""Programmatic graders. Each returns named checks in one of four dimensions.

Dimensions are reported separately so a regression in one is not hidden by
the others:

- ``process``    what the agent asked, and in what order it acted
- ``accuracy``   the numbers and the specification behind them
- ``format``     what the final answer discloses (the citation contract)
- ``guardrails`` things that must never happen

Expected values are recomputed here from :mod:`eval.bls.world`, never read
back from the server under test.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from eval.bls import world
from eval.bls.transcript import ToolCall, Transcript

FACTOR_TOLERANCE = 1e-9  # tool result vs independent recomputation
STATED_FACTOR_TOLERANCE = 5e-4  # a factor quoted to 3+ decimals in prose
STATED_PERCENT_TOLERANCE = 0.05  # a percent quoted to 1+ decimals in prose
WEIGHT_TOLERANCE = 5e-3


@dataclass(frozen=True)
class Check:
    name: str
    dimension: str
    passed: bool
    detail: str = ""


Grader = Callable[[Transcript], list[Check]]


# --------------------------------------------------------------------------
# Reading the transcript
# --------------------------------------------------------------------------


def final_result(transcript: Transcript) -> dict[str, Any] | None:
    call = transcript.final_source_calculation()
    if call is None or not isinstance(call.result, dict):
        return None
    result = call.result.get("result")
    return result if isinstance(result, dict) else None


def final_weights(transcript: Transcript) -> dict[str, float]:
    """series_id -> total weight in the final snapshot-backed calculation."""
    result = final_result(transcript)
    weights: dict[str, float] = {}
    for component in (result or {}).get("components", []):
        series_id = component.get("series_id")
        if series_id:
            weights[series_id] = weights.get(series_id, 0.0) + component["weight"]
    return weights


def final_years(transcript: Transcript) -> tuple[int | None, int | None]:
    result = final_result(transcript) or {}
    return (
        (result.get("base_period") or {}).get("year"),
        (result.get("target_period") or {}).get("year"),
    )


def numbers_in(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"-?\d[\d,]*\.?\d*", text)]


CATALOG_TOOLS = frozenset({"search_series", "describe_series", "get_series_hierarchy"})


def returned_series(call: ToolCall) -> set[str]:
    """Series IDs a successful catalog call returned.

    For get_series_hierarchy only the related series count: the non-null IDs
    in ``parents`` and ``sub_items``. The series it was asked about is not
    discovered by asking, or any recalled ID could be laundered through it.
    """
    if call.name not in CATALOG_TOOLS or call.is_error:
        return set()
    if call.name == "get_series_hierarchy":
        result = call.result if isinstance(call.result, dict) else {}
        related = [*result.get("parents", []), *result.get("sub_items", [])]
        return {
            entry["series_id"]
            for entry in related
            if isinstance(entry, dict) and entry.get("series_id")
        }
    rows = call.result if isinstance(call.result, list) else [call.result]
    found = set()
    for row in rows:
        if isinstance(row, dict):
            series = row.get("series", row)
            if series.get("series_id"):
                found.add(series["series_id"])
    return found


def used_before_discovery(transcript: Transcript, series_ids: set[str]) -> list[str]:
    """Series passed to a non-catalog tool before the catalog returned them.

    Order is the order of tool calls, so looking a series up after it was
    already used does not count as discovering it.
    """
    known: set[str] = set()
    early: set[str] = set()
    for call in transcript.tool_calls:
        if call.name in CATALOG_TOOLS:
            known |= returned_series(call)
            continue
        arguments = json.dumps(call.arguments, default=str)
        early |= {s for s in series_ids - known if s in arguments}
    never = {s for s in series_ids if s not in known}
    return sorted(early | never)


_WEIGHT_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*%|(?<![\w.])(0?\.\d+|1\.0+)(?![\w.%])")


def cited_weights(text: str, series_ids: set[str]) -> dict[str, float | None]:
    """The weight stated next to each series ID in *text*.

    For each series, the nearest weight-like number on the same line: a
    percentage ("45%") or a fraction between 0 and 1 ("0.45"). Index levels
    such as 200.0 are not weight-like, so they cannot satisfy a weight check.
    """
    cited: dict[str, float | None] = dict.fromkeys(series_ids)
    for line in text.splitlines():
        tokens = [
            (
                match.start(),
                match.end(),
                float(match.group(1)) / 100
                if match.group(1)
                else float(match.group(2)),
            )
            for match in _WEIGHT_TOKEN.finditer(line)
        ]
        for series_id in series_ids:
            at = line.find(series_id)
            if at < 0 or not tokens or cited[series_id] is not None:
                continue
            end = at + len(series_id)
            nearest = min(tokens, key=lambda t: at - t[1] if t[1] <= at else t[0] - end)
            cited[series_id] = nearest[2]
    return cited


def weight_mismatches(text: str, weights: dict[str, float]) -> list[str]:
    """Series whose weight in *text* is missing or differs from *weights*."""
    cited = cited_weights(text, set(weights))
    wrong = []
    for series_id, weight in weights.items():
        stated = cited[series_id]
        if stated is None:
            wrong.append(f"{series_id}: not stated")
        elif not math.isclose(stated, weight, abs_tol=WEIGHT_TOLERANCE):
            wrong.append(f"{series_id}: stated {stated:g}, calculated {weight:g}")
    return wrong


# --------------------------------------------------------------------------
# Graders shared by every case
# --------------------------------------------------------------------------


def source_backed(transcript: Transcript) -> list[Check]:
    return [
        Check(
            "result comes from calculate_index_from_bls",
            "process",
            final_result(transcript) is not None,
            "No successful snapshot-backed calculation was made."
            if final_result(transcript) is None
            else "",
        )
    ]


def periods(base_year: int, target_year: int) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        got = final_years(transcript)
        return [
            Check(
                f"periods are {base_year} -> {target_year}",
                "accuracy",
                got == (base_year, target_year),
                f"calculated {got[0]} -> {got[1]}",
            )
        ]

    return grade


def recomputed_factor(transcript: Transcript) -> list[Check]:
    """The tool's composite equals sum(w * I_target / I_base) from the world."""
    result = final_result(transcript)
    weights = final_weights(transcript)
    base_year, target_year = final_years(transcript)
    name = "composite matches an independent recomputation"
    if result is None or base_year is None or target_year is None:
        return [Check(name, "accuracy", False, "no calculation to check")]
    unknown = sorted(
        set(weights) - set(world.ENDPOINTS) - set(world.QUARTERLY_ENDPOINTS)
    )
    if unknown:
        return [Check(name, "accuracy", False, f"series outside the world: {unknown}")]
    expected = world.composite(weights, base_year, target_year)
    got = result["temporal_composite_factor"]
    return [
        Check(
            name,
            "accuracy",
            math.isclose(got, expected, abs_tol=FACTOR_TOLERANCE),
            f"tool {got:.9f}, expected {expected:.9f}",
        )
    ]


def weights_sum_to_one(transcript: Transcript) -> list[Check]:
    total = sum(final_weights(transcript).values())
    return [
        Check(
            "weights sum to 1",
            "accuracy",
            math.isclose(total, 1.0, abs_tol=1e-6),
            f"sum {total:.6f}",
        )
    ]


def stated_result(transcript: Transcript) -> list[Check]:
    """The final answer quotes the factor and percent change the tool returned."""
    result = final_result(transcript)
    if result is None:
        return [
            Check("answer states the composite factor", "format", False, "no result"),
            Check("answer states the percent change", "format", False, "no result"),
        ]
    stated = numbers_in(transcript.final_message)
    factor = result["temporal_composite_factor"]
    percent = result["temporal_percent_change"]
    return [
        Check(
            "answer states the composite factor",
            "format",
            any(abs(n - factor) <= STATED_FACTOR_TOLERANCE for n in stated),
            f"expected about {factor:.4f}",
        ),
        Check(
            "answer states the percent change",
            "format",
            any(abs(n - percent) <= STATED_PERCENT_TOLERANCE for n in stated),
            f"expected about {percent:.2f}%",
        ),
    ]


def citations(transcript: Transcript) -> list[Check]:
    """The citation contract: series, weights, periods and snapshot are named."""
    text = transcript.final_message
    weights = final_weights(transcript)
    base_year, target_year = final_years(transcript)
    missing_series = [s for s in weights if s not in text]
    wrong_weights = weight_mismatches(text, weights)
    return [
        Check(
            "answer cites every series ID",
            "format",
            bool(weights) and not missing_series,
            f"missing {missing_series}" if missing_series else "",
        ),
        Check(
            "answer states each series with its own weight",
            "format",
            bool(weights) and not wrong_weights,
            "; ".join(wrong_weights),
        ),
        Check(
            "answer states base and target periods",
            "format",
            base_year is not None
            and str(base_year) in text
            and str(target_year) in text,
        ),
        Check(
            "answer cites the snapshot ID",
            "format",
            world.SNAPSHOT_ID in text,
        ),
    ]


def no_live_retrieval(transcript: Transcript) -> list[Check]:
    live = transcript.calls("get_series_data")
    return [
        Check(
            "no live BLS API call",
            "guardrails",
            not live,
            f"{len(live)} call(s) to get_series_data" if live else "",
        )
    ]


def no_supplied_value_calculation(transcript: Transcript) -> list[Check]:
    """Index levels must come from the snapshot, never typed in by the agent."""
    supplied = transcript.calls(
        "calculate_index_spec", "calculate_component_escalation"
    )
    return [
        Check(
            "no calculation from agent-supplied index values",
            "guardrails",
            not supplied,
            f"{len(supplied)} supplied-value calculation(s)" if supplied else "",
        )
    ]


# --------------------------------------------------------------------------
# Case-specific graders
# --------------------------------------------------------------------------


def asked_before_calculating(fact: str, label: str) -> Grader:
    """The user disclosed *fact* (so was asked) before any calculation ran."""

    def grade(transcript: Transcript) -> list[Check]:
        revealed = transcript.revealed.get(fact)
        first = transcript.first_calculation_turn()
        asked = revealed is not None and (first is None or first >= revealed)
        if revealed is None:
            detail = "the agent never asked"
        elif not asked:
            detail = f"calculated in turn {first}, asked in turn {revealed - 1}"
        else:
            detail = ""
        return [
            Check(f"asked for {label} before calculating", "process", asked, detail)
        ]

    return grade


def exact_basket(expected: dict[str, float]) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        got = final_weights(transcript)
        same = set(got) == set(expected) and all(
            math.isclose(got[s], w, abs_tol=1e-9) for s, w in expected.items()
        )
        return [
            Check(
                "basket matches the stated commodities and percentages",
                "accuracy",
                same,
                "" if same else f"calculated with {got}",
            )
        ]

    return grade


def expected_factor(expected: float) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        result = final_result(transcript)
        got = result["temporal_composite_factor"] if result else None
        return [
            Check(
                "composite factor equals the known answer",
                "accuracy",
                got is not None
                and math.isclose(got, expected, abs_tol=FACTOR_TOLERANCE),
                f"tool {got}, expected {expected:.9f}",
            )
        ]

    return grade


def elicited(required: tuple[str, ...], any_of: tuple[str, ...]) -> Grader:
    """Clarifying questions drew out the needed facts before calculating."""

    def grade(transcript: Transcript) -> list[Check]:
        first = transcript.first_calculation_turn()

        def in_time(fact: str) -> bool:
            turn = transcript.revealed.get(fact)
            return turn is not None and (first is None or turn <= first)

        missing = [fact for fact in required if not in_time(fact)]
        some = any(in_time(fact) for fact in any_of)
        return [
            Check(
                "clarified periods and weights before calculating",
                "process",
                not missing,
                f"not elicited in time: {missing}" if missing else "",
            ),
            Check(
                "clarified project type or scope before calculating",
                "process",
                some,
                "" if some else f"none of {list(any_of)} elicited in time",
            ),
        ]

    return grade


def confirmed_proposal(transcript: Transcript) -> list[Check]:
    """The agent showed its basket and got a yes before the final calculation."""
    confirmed = transcript.revealed.get("confirmation")
    call = transcript.final_source_calculation()
    name = "user confirmed the proposed basket before the final calculation"
    if confirmed is None:
        return [Check(name, "process", False, "the agent never asked for confirmation")]
    if call is None or call.turn < confirmed:
        return [Check(name, "process", False, "calculated before the confirmation")]
    proposal = next(
        (m.text for m in transcript.agent_messages() if m.turn == confirmed - 1), ""
    )
    changed = weight_mismatches(proposal, final_weights(transcript))
    return [
        Check(
            name,
            "process",
            not changed,
            "calculated basket differs from the confirmed proposal: "
            + "; ".join(changed)
            if changed
            else "",
        )
    ]


def _spec_weights(spec: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for component in spec.get("components") or []:
        series_id = component.get("series_id")
        if series_id:
            weights[series_id] = weights.get(series_id, 0.0) + component["weight"]
    return weights


def validated_before_calculating(transcript: Transcript) -> list[Check]:
    """A clean validation of the calculated spec came before the calculation."""
    name = "the calculated specification was validated first, without errors"
    final = transcript.final_source_calculation()
    if final is None:
        return [Check(name, "process", False, "no calculation to check")]
    spec_id = final.arguments.get("spec_id")
    weights = final_weights(transcript)
    earlier = transcript.tool_calls[: transcript.tool_calls.index(final)]
    matching = [
        call
        for call in earlier
        if call.name == "validate_index_spec"
        and not call.is_error
        and (call.arguments.get("spec") or {}).get("id") == spec_id
        and _spec_weights(call.arguments["spec"]).keys() == weights.keys()
        and all(
            math.isclose(w, weights[s], abs_tol=1e-9)
            for s, w in _spec_weights(call.arguments["spec"]).items()
        )
    ]
    if not matching:
        detail = "no earlier validate_index_spec call for the calculated basket"
        return [Check(name, "process", False, detail)]
    errors = [
        finding["message"]
        for finding in (matching[-1].result or {}).get("findings", [])
        if finding.get("severity") == "ERROR"
    ]
    return [Check(name, "process", not errors, "; ".join(errors))]


def family_share(family: frozenset[str], share: float, label: str) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        got = sum(w for s, w in final_weights(transcript).items() if s in family)
        return [
            Check(
                f"{label} carries the share the user stated ({share:g})",
                "accuracy",
                math.isclose(got, share, abs_tol=WEIGHT_TOLERANCE),
                f"{label} weight {got:g}",
            )
        ]

    return grade


def minimum_components(count: int) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        got = len(final_weights(transcript))
        return [
            Check(
                f"basket has at least {count} indexed components",
                "accuracy",
                got >= count,
                f"{got} component(s)",
            )
        ]

    return grade


def series_were_discovered(transcript: Transcript) -> list[Check]:
    """Every series used was returned by the catalog before it was used."""
    early = used_before_discovery(transcript, set(final_weights(transcript)))
    return [
        Check(
            "every series was found through the catalog tools before use",
            "guardrails",
            not early,
            f"used before search/describe returned them: {early}" if early else "",
        )
    ]


def alignment_disclosed(transcript: Transcript) -> list[Check]:
    """A quarterly-sourced series must say which quarter each value came from.

    When the server aligned an ECI-like series to the spec's annual periods,
    the answer must state the year-quarter actually used (e.g. ``2014-Q04``)
    on the line that cites that series; a quarter stated anywhere — or on the
    wrong series' line — does not satisfy the contract, and a bare
    ``2014/2026`` citation would imply an annual average the program never
    published.
    """
    name = "answer states each quarterly-sourced series' year-quarter"
    result = final_result(transcript)
    if result is None:
        return [Check(name, "format", False, "no result")]
    aligned: dict[str, set[tuple[int, int]]] = {}
    for component in result.get("components", []):
        series_id = component.get("series_id")
        if not series_id:
            continue
        for period in (component.get("base_period"), component.get("target_period")):
            if isinstance(period, dict) and period.get("periodicity") == "QUARTERLY":
                aligned.setdefault(series_id, set()).add(
                    (period["year"], period["quarter"])
                )
    missing = []
    for series_id, pairs in sorted(aligned.items()):
        for year, quarter in sorted(pairs):
            spellings = (f"{year}-Q0{quarter}", f"{year}-Q{quarter}")
            next_to_series = any(
                series_id in line and any(spelling in line for spelling in spellings)
                for line in transcript.final_message.splitlines()
            )
            if not next_to_series:
                missing.append(f"{series_id}: {year}-Q{quarter:02d}")
    return [
        Check(
            name,
            "format",
            not missing,
            ("quarter not stated next to the series for: " + ", ".join(missing))
            if missing
            else "",
        )
    ]


# Additional scenarios: independent checks for clarification, recovery, and
# correctly declining an unsupported request. Negative outcomes deliberately
# do not use COMMON, which requires a successful calculation.


def no_calculation_before_fact(fact: str) -> Grader:
    def grade(transcript: Transcript) -> list[Check]:
        disclosed = transcript.revealed.get(fact)
        first = transcript.first_calculation_turn()
        return [
            Check(
                f"no calculation before {fact} is supplied",
                "process",
                disclosed is not None and (first is None or first >= disclosed),
            )
        ]

    return grade


def no_calculation(transcript: Transcript) -> list[Check]:
    return [
        Check(
            "no unsupported calculation attempted",
            "guardrails",
            transcript.first_calculation_turn() is None,
        )
    ]


def unavailable_period_disclosed(transcript: Transcript) -> list[Check]:
    text = transcript.final_message.lower()
    return [
        Check(
            "unavailable 2030 period explained",
            "format",
            "2030" in text
            and any(
                word in text
                for word in (
                    "unavailable",
                    "not available",
                    "no observations",
                    "no data",
                )
            ),
        )
    ]


def no_fabricated_future_factor(transcript: Transcript) -> list[Check]:
    text = transcript.final_message.lower()
    invented = bool(
        re.search(
            r"(?:factor|increase|escalation)\s*(?:of|is|:|=)\s*\d+(?:\.\d+)?\s*%?", text
        )
    )
    return [Check("no fabricated future factor", "guardrails", not invented)]


def no_unapproved_substitution(transcript: Transcript) -> list[Check]:
    return [
        Check(
            "no unapproved target-period substitution",
            "process",
            transcript.final_source_calculation() is None,
        )
    ]


def corrected_weights_before_calculation(transcript: Transcript) -> list[Check]:
    disclosed = transcript.revealed.get("corrected_weights")
    first = transcript.first_calculation_turn()
    return [
        Check(
            "user corrected invalid weights before calculation",
            "process",
            disclosed is not None and (first is None or first >= disclosed),
        )
    ]


def invalid_total_disclosed(transcript: Transcript) -> list[Check]:
    text = " ".join(m.text.lower() for m in transcript.agent_messages())
    return [
        Check(
            "invalid 115 percent total identified",
            "process",
            "115%" in text or "115 percent" in text,
        )
    ]


def observation_values_disclosed(transcript: Transcript) -> list[Check]:
    result = final_result(transcript)
    if result is None:
        return [Check("source observations disclosed per series", "format", False)]
    missing = []
    for component in result.get("components", []):
        line = next(
            (
                line
                for line in transcript.final_message.splitlines()
                if component["series_id"] in line
            ),
            "",
        )
        if not all(
            str(component[key]) in line for key in ("base_value", "target_value")
        ):
            missing.append(component["series_id"])
    return [
        Check(
            "source observations disclosed per series",
            "format",
            not missing,
            f"missing observations: {missing}" if missing else "",
        )
    ]


def method_disclosed(transcript: Transcript) -> list[Check]:
    text = transcript.final_message.lower()
    return [
        Check(
            "weighted index-relative method disclosed",
            "format",
            "weight" in text and ("relative" in text or "ratio" in text),
        )
    ]


def synthetic_provenance_disclosed(transcript: Transcript) -> list[Check]:
    text = transcript.final_message.lower()
    return [
        Check(
            "synthetic data clearly identified",
            "format",
            "synthetic" in text and world.SNAPSHOT_ID in text,
        )
    ]


COMMON: tuple[Grader, ...] = (
    source_backed,
    weights_sum_to_one,
    recomputed_factor,
    stated_result,
    citations,
    no_live_retrieval,
    no_supplied_value_calculation,
    series_were_discovered,
)
