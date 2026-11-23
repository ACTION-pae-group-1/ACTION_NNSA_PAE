"""A scripted user: discloses a fact only when the agent asks about it.

Deterministic on purpose, so the same agent behaviour always yields the same
conversation. A reply is built from the parts of the agent's message that ask
the user something; a message that asks nothing a fact can answer ends the
conversation.

What counts as asking (``asking_parts``):

- a sentence or list item ending in a question mark;
- a request phrased as a statement: "Please confirm ...", "I'll need the
  base year.", "Let me know the target period." A conditional offer whose
  only cue is "let me know" ("Let me know if you'd like a different year.")
  is not a request;
- the items of a list the agent introduces as a request ("I'll need a few
  details:") or refers back to afterwards ("Could you provide these
  details?").

Results, proposals and tables are never read for keywords unless the agent
asks about them in one of these ways, so an agent cannot obtain a fact by
merely mentioning it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Fact:
    name: str
    keywords: tuple[str, ...]
    answer: str


_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_REQUEST = re.compile(
    r"\b(?:please|could you|can you|would you|will you|tell me|let me know"
    r"|need to know|i need|i'll need|i will need|i would need|i'd need"
    r"|confirm)\b"
)
#: A sentence whose only request cue is "let me know" and which is
#: conditional ("... if you'd like ...") is an offer, not a request.
_CONDITIONAL = re.compile(r"\bif\b|\bfeel free\b")
#: Words a follow-up request uses to point back at a list above it.
_REFERS_BACK = re.compile(
    r"\b(?:these|those|the above|above|following)\b.*"
    r"\b(?:details|information|questions|points|items)\b"
    r"|\bthe (?:above|following)\b"
)


def _plain(text: str) -> str:
    """*text* without markdown emphasis, so "**Ready?**" ends in "?"."""
    return re.sub(r"\*\*|__|`", "", text).strip()


def _is_asking(sentence: str) -> bool:
    text = _plain(sentence)
    if text.endswith("?"):
        return True
    lowered = text.lower()
    cues = {match.group(0) for match in _REQUEST.finditer(lowered)}
    if not cues:
        return False
    return not (cues == {"let me know"} and _CONDITIONAL.search(lowered))


def question_sentences(text: str) -> list[str]:
    """Sentences (or list items) of *text* that end in a question mark."""
    parts = re.split(r"(?<=[.?!])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip().endswith("?")]


def asking_parts(text: str) -> list[str]:
    """The sentences and list items of *text* that ask the user something."""
    lines = [_plain(line) for line in text.splitlines()]
    kinds: list[str] = []  # "item", "text" or "blank", one per line
    for line in lines:
        if not line.strip():
            kinds.append("blank")
        elif _LIST_ITEM.match(line):
            kinds.append("item")
        else:
            kinds.append("text")

    def sentences(line: str) -> list[str]:
        return [s.strip() for s in _SENTENCE_END.split(line) if s.strip()]

    def neighbour(start: int, step: int) -> str | None:
        """The nearest non-blank, non-item line from *start* in *step* direction."""
        index = start
        while 0 <= index < len(lines):
            if kinds[index] == "text":
                return lines[index]
            if kinds[index] == "item" or kinds[index] == "blank":
                index += step
                continue
        return None

    asked: list[str] = []
    index = 0
    while index < len(lines):
        kind = kinds[index]
        if kind == "text":
            asked += [s for s in sentences(lines[index]) if _is_asking(s)]
            index += 1
            continue
        if kind == "blank":
            index += 1
            continue
        # A run of list items, allowing blank lines between items.
        end = index
        items: list[int] = []
        while end < len(lines) and kinds[end] in ("item", "blank"):
            if kinds[end] == "item":
                items.append(end)
            end += 1
        before = neighbour(index - 1, -1)
        after = neighbour(end, 1)
        lead_in = sentences(before)[-1] if before else ""
        follow_up = sentences(after)[0] if after else ""
        introduced = bool(lead_in) and _is_asking(lead_in)
        referred = (
            bool(follow_up)
            and _is_asking(follow_up)
            and bool(_REFERS_BACK.search(follow_up.lower()))
        )
        for item in items:
            if introduced or referred:
                asked.append(lines[item].strip())
            else:
                asked += [s for s in sentences(lines[item]) if _is_asking(s)]
        index = end
    return asked


class SimulatedUser:
    def __init__(self, opening: str, facts: tuple[Fact, ...]) -> None:
        self.opening = opening
        self.facts = facts

    def reply(
        self, agent_message: str, already: frozenset[str] = frozenset()
    ) -> tuple[str, list[str]] | None:
        """Return (reply text, fact names disclosed), or None to stop.

        Facts in *already* were disclosed earlier; they are repeated only when
        the agent asks about nothing new.
        """
        asked = " ".join(asking_parts(agent_message)).lower()
        if not asked:
            return None
        matched = [
            fact
            for fact in self.facts
            if any(keyword in asked for keyword in fact.keywords)
        ]
        matched = [f for f in matched if f.name not in already] or matched
        if not matched:
            return None
        return " ".join(fact.answer for fact in matched), [f.name for f in matched]
