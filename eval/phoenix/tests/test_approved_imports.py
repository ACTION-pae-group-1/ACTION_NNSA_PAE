"""Guard: no eval module may reach a public LLM endpoint or SDK.

Only the portable client (Ask Sage -gov models and local Ollama) is approved.
Tests are excluded because they name public hosts to prove they are refused.
"""

from __future__ import annotations

import ast
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
BANNED_IMPORT_ROOTS = {"langchain", "anthropic", "openai"}
BANNED_NAMES = {"ChatAnthropic", "ChatOpenAI", "AzureChatOpenAI"}
BANNED_HOSTS = ("api.anthropic.com", "api.openai.com")


def _eval_sources() -> list[Path]:
    return [
        path
        for path in EVAL_DIR.rglob("*.py")
        if "tests" not in path.relative_to(EVAL_DIR).parts
        and "__pycache__" not in path.parts
    ]


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    return roots


def test_sources_exist() -> None:
    assert _eval_sources(), "no eval sources found; the guard would pass vacuously"


def test_no_langchain_anthropic_or_openai_imports() -> None:
    offenders = {}
    for path in _eval_sources():
        roots = _import_roots(ast.parse(path.read_text(encoding="utf-8")))
        bad = {r for r in roots if any(r.startswith(b) for b in BANNED_IMPORT_ROOTS)}
        if bad:
            offenders[path.name] = sorted(bad)
    assert offenders == {}


def test_no_public_chat_classes_or_hosts() -> None:
    offenders = []
    for path in _eval_sources():
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.name}: {token}"
            for token in (*BANNED_NAMES, *BANNED_HOSTS)
            if token in text
        ]
    assert offenders == []
