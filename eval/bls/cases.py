"""The eval cases: an opening request, a scripted user, and the graders."""

from __future__ import annotations

from dataclasses import dataclass

from eval.bls import graders as g
from eval.bls import world
from eval.bls.simulated_user import Fact, SimulatedUser

#: How an agent asks for a go-ahead. Lead-ins such as "To proceed, I need ..."
#: are read too, so a bare "proceed" would answer questions nobody asked.
CONFIRMATION_KEYWORDS = (
    "confirm",
    "approve",
    "look right",
    "looks right",
    "sound right",
    "sounds right",
    "look good",
    "looks good",
    "like me to proceed",
    "shall i proceed",
    "should i proceed",
    "ok to proceed",
    "okay to proceed",
    "go ahead",
    "use these",
    "satisfied with",
    "happy with",
    "agree with",
    "acceptable",
    "work for you",
    "works for you",
)
#: The user does not know BLS series IDs; the agent must find them.
SERIES_IDS = Fact(
    "series_ids",
    ("series id", "exact series", "specific series", "which series", "series code"),
    "I don't know the BLS series IDs. Please find them with the catalog search.",
)
#: A go-ahead for the deterministic cases, whose user has nothing to change.
GO_AHEAD = Fact("confirmation", CONFIRMATION_KEYWORDS, "Yes, go ahead.")


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    user: SimulatedUser
    graders: tuple[g.Grader, ...]
    max_turns: int = 8


# --------------------------------------------------------------------------
# Case 1 — deterministic: known commodity percentages, target year missing
# --------------------------------------------------------------------------

KNOWN_BASKET = {
    world.READY_MIX: 0.45,
    world.STEEL_MILLS: 0.35,
    world.SAWMILLS: 0.20,
}
KNOWN_BASKET_FACTOR = world.composite(KNOWN_BASKET, 2014, 2026)

known_basket = Case(
    id="known-basket-missing-target-year",
    title="Vertical construction, 2014 estimate, known commodity percentages",
    user=SimulatedUser(
        opening=(
            "I have a 2014 materials estimate for a vertical construction project, "
            "a mid-rise building. The materials cost is 45% ready-mix concrete, "
            "35% steel from iron and steel mills, and 20% sawmill lumber. "
            "Please normalize it using annual-average PPI industry indexes."
        ),
        facts=(
            Fact(
                "target_year",
                ("year", "period", "target", "what date", "when"),
                "The estimate is in 2014 dollars. Bring it to 2026, annual averages.",
            ),
            GO_AHEAD,
            SERIES_IDS,
        ),
    ),
    graders=(
        g.asked_before_calculating("target_year", "the target year"),
        g.periods(2014, 2026),
        g.exact_basket(KNOWN_BASKET),
        g.expected_factor(KNOWN_BASKET_FACTOR),
        g.validated_before_calculating,
        *g.COMMON,
    ),
)


# --------------------------------------------------------------------------
# Case 3 — open-ended: vague project, indexes and percentages negotiated
# --------------------------------------------------------------------------

vague_project = Case(
    id="vague-project-negotiated-basket",
    title="Vague project: indexes and percentages agreed in conversation",
    user=SimulatedUser(
        opening=(
            "We're budgeting a new building and our cost estimate is old. "
            "Can you bring it up to today's dollars?"
        ),
        facts=(
            Fact(
                "project_type",
                ("what kind", "what type", "kind of", "type of", "describe"),
                "It's a five-story steel-framed office building.",
            ),
            Fact(
                "estimate_year",
                ("estimate from", "when was", "base year", "base period", "how old"),
                "The estimate is in 2014 dollars.",
            ),
            Fact(
                "target_year",
                (
                    "target",
                    "escalate to",
                    "bring it to",
                    "to which year",
                    "to what year",
                ),
                "Bring it to 2026, using annual averages.",
            ),
            Fact(
                "scope",
                ("labor", "scope", "include", "cover", "materials only"),
                "Materials only. Labor is escalated separately by another team.",
            ),
            Fact(
                "weights",
                ("weight", "percent", "share", "breakdown", "split", "proportion"),
                "I only know structural steel is about half of the materials cost. "
                "Please propose the rest.",
            ),
            Fact(
                "confirmation",
                CONFIRMATION_KEYWORDS,
                "Yes, that works. Go ahead.",
            ),
            SERIES_IDS,
        ),
    ),
    graders=(
        g.elicited(
            required=("estimate_year", "target_year", "weights"),
            any_of=("project_type", "scope"),
        ),
        g.confirmed_proposal,
        g.validated_before_calculating,
        g.periods(2014, 2026),
        g.family_share(world.STEEL_FAMILY, 0.5, "steel"),
        g.minimum_components(3),
        *g.COMMON,
    ),
    max_turns=10,
)

# --------------------------------------------------------------------------
# Case 2 — deterministic: PPI materials + ECI-like labor, one annual basis
# --------------------------------------------------------------------------

MIXED_BASKET = {world.READY_MIX: 0.60, world.LABOR_COST: 0.40}
MIXED_BASKET_FACTOR = world.composite(MIXED_BASKET, 2014, 2026)

mixed_materials_and_labor = Case(
    id="mixed-materials-and-labor",
    title="Materials (PPI annual) plus labor (quarterly ECI-like), 2014 base",
    user=SimulatedUser(
        opening=(
            "I have a 2014 cost estimate for an office building renovation: "
            "60% materials cost, which I index with PPI ready-mix concrete, "
            "and 40% labor cost, which I index with a labor cost index. "
            "Please normalize it using annual indexes."
        ),
        facts=(
            Fact(
                "target_year",
                ("year", "period", "target", "what date", "when"),
                "The estimate is in 2014 dollars. Bring it to 2026, annual averages.",
            ),
            GO_AHEAD,
            SERIES_IDS,
        ),
    ),
    graders=(
        g.asked_before_calculating("target_year", "the target year"),
        g.periods(2014, 2026),
        g.exact_basket(MIXED_BASKET),
        g.expected_factor(MIXED_BASKET_FACTOR),
        g.alignment_disclosed,
        g.validated_before_calculating,
        *g.COMMON,
    ),
)


# Additional independent scenarios. Existing cases remain unchanged so their
# longitudinal scores and fingerprints can be compared with earlier runs.
AMBIGUOUS_BASKET = {
    world.STRUCTURAL_METAL: 0.50,
    world.READY_MIX: 0.35,
    world.FLAT_GLASS: 0.15,
}
COMMODITY_BASKET = {
    world.STRUCTURAL_METAL: 0.60,
    world.READY_MIX: 0.25,
    world.GYPSUM: 0.15,
}

ambiguous_escalation = Case(
    id="ambiguous-escalation-request",
    title="Clarify scope and periods before proposing a materials basket",
    user=SimulatedUser(
        opening=(
            "Can you escalate an old five-story office building estimate "
            "to current dollars using BLS?"
        ),
        facts=(
            Fact(
                "project_type",
                ("what kind", "what type", "kind of", "type of", "describe"),
                "It's a five-story steel-framed office building.",
            ),
            Fact(
                "estimate_year",
                ("base year", "base period", "estimate from", "when was", "how old"),
                "The base estimate is in 2014 dollars.",
            ),
            Fact(
                "target_year",
                (
                    "target",
                    "to which year",
                    "to what year",
                    "bring it to",
                    "escalate to",
                ),
                "Use 2026 annual averages.",
            ),
            Fact(
                "scope",
                ("scope", "labor", "materials only", "include"),
                "Materials only, no labor.",
            ),
            Fact(
                "weights",
                ("weight", "percent", "share", "breakdown", "split"),
                (
                    "Use 50% fabricated structural metal, "
                    "35% ready-mix concrete, "
                    "and 15% flat glass."
                ),
            ),
            GO_AHEAD,
            SERIES_IDS,
        ),
    ),
    graders=(
        g.elicited(
            ("estimate_year", "target_year", "weights", "scope"),
            ("project_type", "scope"),
        ),
        g.confirmed_proposal,
        g.no_calculation_before_fact("weights"),
        g.periods(2014, 2026),
        g.exact_basket(AMBIGUOUS_BASKET),
        g.expected_factor(world.composite(AMBIGUOUS_BASKET, 2014, 2026)),
        g.validated_before_calculating,
        *g.COMMON,
    ),
    max_turns=12,
)


class CommodityConfirmationUser(SimulatedUser):
    """Confirm only a correctly paired series-and-weight proposal."""

    def reply(
        self, agent_message: str, already: frozenset[str] = frozenset()
    ) -> tuple[str, list[str]] | None:
        from eval.bls.simulated_user import asking_parts

        requested = " ".join(asking_parts(agent_message)).lower()
        if any(word in requested for word in CONFIRMATION_KEYWORDS):
            if not g.weight_mismatches(agent_message, COMMODITY_BASKET):
                return (
                    "Confirmed. Use those three series and weights with "
                    "2014 and 2026 annual-average periods. "
                    "Please validate and calculate.",
                    ["confirmation"],
                )
            return (
                "Please show each proposed series ID with its 60%, 25%, "
                "or 15% weight before I approve the mapping. "
                "Do not substitute another commodity.",
                ["proposal_needs_review"],
            )
        return super().reply(agent_message, already)


commodity_selection = Case(
    id="commodity-series-selection",
    title="Discover fabricated metal, concrete, and gypsum catalog series",
    user=CommodityConfirmationUser(
        opening=(
            "Escalate my 2014 materials estimate to 2026 annual-average dollars: "
            "60% fabricated structural metal, 25% ready-mix concrete, "
            "15% gypsum products. Identify the appropriate PPI series first."
        ),
        facts=(SERIES_IDS,),
    ),
    graders=(
        g.periods(2014, 2026),
        g.exact_basket(COMMODITY_BASKET),
        g.expected_factor(world.composite(COMMODITY_BASKET, 2014, 2026)),
        g.validated_before_calculating,
        *g.COMMON,
    ),
    max_turns=14,
)

mixed_alignment = Case(
    id="mixed-labor-materials-alignment",
    title="Explicit Q04 alignment of quarterly labor with annual PPI",
    user=SimulatedUser(
        opening=(
            "Escalate a 2014 office renovation estimate to 2026: "
            "60% ready-mix concrete PPI materials and 40% construction labor ECI. "
            "Explain how annual PPI and quarterly labor observations align."
        ),
        facts=(SERIES_IDS,),
    ),
    graders=(
        g.periods(2014, 2026),
        g.exact_basket(MIXED_BASKET),
        g.expected_factor(MIXED_BASKET_FACTOR),
        g.alignment_disclosed,
        g.validated_before_calculating,
        *g.COMMON,
    ),
)

unavailable_period = Case(
    id="unavailable-target-period",
    title="Reject 2030 request outside the synthetic snapshot",
    user=SimulatedUser(
        opening=(
            "Escalate a 2014 materials estimate to 2030 annual averages "
            "using 60% ready-mix concrete and 40% steel mills. "
            "Use only the active snapshot."
        ),
        facts=(SERIES_IDS,),
    ),
    graders=(
        g.unavailable_period_disclosed,
        g.no_calculation,
        g.no_fabricated_future_factor,
        g.no_unapproved_substitution,
        g.no_live_retrieval,
        g.no_supplied_value_calculation,
    ),
)

invalid_basket = Case(
    id="invalid-weighted-basket",
    title="Detect 115 percent weights and obtain user correction",
    user=SimulatedUser(
        opening=(
            "Escalate 2014 to 2026 annual-average PPI: "
            "50% ready-mix concrete, 40% steel mills, 25% sawmill lumber."
        ),
        facts=(
            Fact(
                "corrected_weights",
                ("correct", "revise", "total", "115", "add up", "sum", "weight"),
                "You're right. Use 45% concrete, 35% steel mills, and 20% lumber.",
            ),
            SERIES_IDS,
        ),
    ),
    graders=(
        g.invalid_total_disclosed,
        g.corrected_weights_before_calculation,
        g.periods(2014, 2026),
        g.exact_basket(KNOWN_BASKET),
        g.expected_factor(KNOWN_BASKET_FACTOR),
        g.validated_before_calculating,
        *g.COMMON,
    ),
    max_turns=10,
)

source_provenance = Case(
    id="source-provenance-audit",
    title="Auditable source observations and synthetic provenance",
    user=SimulatedUser(
        opening=(
            "Prepare an auditable 2014-to-2026 annual-average PPI escalation: "
            "45% ready-mix concrete, 35% steel mills, 20% sawmill lumber. "
            "Show series IDs, weights, index observations, method, and snapshot."
        ),
        facts=(SERIES_IDS,),
    ),
    graders=(
        g.periods(2014, 2026),
        g.exact_basket(KNOWN_BASKET),
        g.expected_factor(KNOWN_BASKET_FACTOR),
        g.observation_values_disclosed,
        g.method_disclosed,
        g.synthetic_provenance_disclosed,
        g.validated_before_calculating,
        *g.COMMON,
    ),
)

CASES: dict[str, Case] = {
    case.id: case
    for case in (
        known_basket,
        mixed_materials_and_labor,
        vague_project,
        ambiguous_escalation,
        commodity_selection,
        mixed_alignment,
        unavailable_period,
        invalid_basket,
        source_provenance,
    )
}
