"""Which BLS codes sit directly above and beneath a series' code.

Two encodings are used by BLS:

- **PPI industry (``pc``)** nests by code prefix. Industry ``3211--`` contains
  ``32111-``, which contains ``321113``; within industry ``321113`` the product
  ``3211133`` (softwood lumber) contains ``32111333`` (dressed 2-inch lumber).
  Trailing dashes pad shorter industry codes and are not part of the prefix.
- **CPI (``cu``) and ECI (``ci``)** publish a ``display_level`` and a
  ``sort_sequence`` for every code. In sort order, a code's parent is the
  nearest earlier code with a lower display level. Codes need not share a
  prefix: ECI "Financial activities" contains both Finance and Real estate.

Display order is only trusted when it forms a single hierarchy: one code at
the shallowest level, as "All items" or "All industries" is. BLS's ECI
occupation table fails this (eight codes share level 0, and "Sales and office"
sorts after "Office and administrative support", which it contains), so
following its display order would invert real parents and children.

These functions are pure so the rules can be tested without a database.
"""

from __future__ import annotations

from collections.abc import Iterable


def level_parents(
    rows: Iterable[tuple[str, int, int]],
    headings: frozenset[str] = frozenset(),
) -> dict[str, str | None]:
    """Map each code to its parent from ``(code, display_level, sort_sequence)``.

    The parent is the nearest earlier code, in sort order, with a lower display
    level. A missing intermediate level does not orphan a code: it attaches to
    the nearest shallower ancestor that is present.

    *headings* are display rows that group codes without being codes (BLS marks
    them not selectable). They still bound the tree, so codes under a heading
    are not mistaken for children of the code before it, but no code is given
    a heading as its parent: it gets the heading's own parent instead.
    """
    raw: dict[str, str | None] = {}
    stack: list[tuple[int, str]] = []
    for code, level, _sort in sorted(rows, key=lambda row: (row[2], row[0])):
        while stack and stack[-1][0] >= level:
            stack.pop()
        raw[code] = stack[-1][1] if stack else None
        stack.append((level, code))

    def resolve(code: str) -> str | None:
        parent = raw[code]
        while parent is not None and parent in headings:
            parent = raw[parent]
        return parent

    return {code: resolve(code) for code in raw}


def display_order_problem(
    rows: Iterable[tuple[str, int, int]],
    headings: frozenset[str] = frozenset(),
) -> str | None:
    """Why display order cannot be trusted as a hierarchy, or None if it can.

    It can when exactly one code (headings aside) sits at the shallowest
    display level. Several top-level codes mean the table lists parallel or
    reordered groupings, so nearest-shallower-code would mis-assign parents.
    """
    codes = [(code, level) for code, level, _sort in rows if code not in headings]
    if not codes:
        return "the table has no codes"
    top = min(level for _code, level in codes)
    roots = sorted(code for code, level in codes if level == top)
    if len(roots) == 1:
        return None
    shown = ", ".join(roots[:4]) + (", ..." if len(roots) > 4 else "")
    return (
        f"BLS's display order is not a single hierarchy ({len(roots)} codes at "
        f"the top level: {shown})"
    )


def _longest_proper_prefix(code: str, candidates: dict[str, str]) -> str | None:
    """The candidate whose key is the longest proper prefix of *code*."""
    for length in range(len(code) - 1, 0, -1):
        found = candidates.get(code[:length])
        if found is not None:
            return found
    return None


def industry_parents(codes: Iterable[str]) -> dict[str, str | None]:
    """Parent of each PPI industry code by prefix, ignoring dash padding."""
    codes = list(codes)
    by_stripped = {code.rstrip("-"): code for code in codes if code.rstrip("-")}
    return {
        code: _longest_proper_prefix(code.rstrip("-"), by_stripped) for code in codes
    }


def product_parents(industry_code: str, products: Iterable[str]) -> dict[str, str]:
    """Parent of each PPI product code within one industry.

    The industry total (product code equal to the industry code) is the root;
    every other product's parent is the longest other product code that is a
    proper prefix of it, or the industry total when there is none.
    """
    products = [code for code in products if code != industry_code]
    by_code = {code: code for code in products}
    return {
        code: _longest_proper_prefix(code, by_code) or industry_code
        for code in products
    }
