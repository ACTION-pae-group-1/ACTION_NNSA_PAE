"""Optional local, read-only MCP chat using the existing portable_llm_mcp agent."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from dotenv import dotenv_values

from portable_llm_mcp import MCPAgent, MCPHub, load_mcp_servers
from portable_llm_mcp.agent import ToolLoopError
from portable_llm_mcp.config import LLMConfigError, LLMProvider, load_llm_settings
from portable_llm_mcp.llm_client import (
    LLMResponseError,
    LLMUnavailableError,
    create_llm_client,
)
from portable_llm_mcp.mcp_client import (
    MCPConfigurationError,
    MCPServerStartError,
    ServerConfig,
)

_LOG = logging.getLogger(__name__)
# Chat's own read-only manifest. The shared host manifest (MCP_SERVERS_FILE) also
# lists write and network tools, so chat does not use it by default.
CHAT_MANIFEST = Path(__file__).with_name("chat_mcp_servers.json")
# The PARS server gets a fresh database for every chat call (see _isolate_pars).
PARS_SERVER = "pars_mcp"
# Bounds so a stalled local service produces a message instead of a hang.
CHAT_TOTAL_TIMEOUT_SECONDS = 240.0
TOOL_TIMEOUT_SECONDS = 60.0
# Per-result size the model sees. A full BLS catalog search is about 13k-18k
# characters; the earlier 4000 cap hid most matches (for example, steel series
# past the cap were never shown). Results longer than this are cut and marked.
CHAT_RESULT_CHARS = 20000

# Chat is deliberately limited to read-only discovery and evidence. Basket
# mutation and model inference remain explicit UI actions. PARS names match the
# canonical read list in tests/pars_read_tools.json. BLS names read only the local
# snapshot; none of them call the live BLS API or write.
READ_ONLY_TOOLS = frozenset(
    {
        "get_project_info",
        "get_wbs_by_level",
        "get_wbs_hierarchy",
        "get_wbs_lineage",
        "get_leaf_nodes",
        "get_wbs_project_descriptions",
        "get_wbs_rows",
        "get_wbs_run_status",
        "list_projects",
        "search_wbs",
        "validate_wbs_inputs",
        "search_series",
        "describe_series",
        "get_series_hierarchy",
        "get_cached_series_data",
    }
)
_DEFAULT_MESSAGE = (
    "Search could not complete. Check the configured model, "
    "LLM provider, model endpoint, and MCP server configuration."
)
# Fixed answers for requests no permitted tool answered. They replace any model
# text written without a successful tool result, so general knowledge is never
# presented as a project fact.
UNSUPPORTED_MESSAGE = (
    "I'm sorry, that information isn't available through the connected project "
    "and cost-data sources. I can help with available PARS project information, "
    "WBS details, and BLS price-index data."
)
READ_ONLY_MESSAGE = (
    "Search is read-only. It cannot modify PARS records, WBS data, machine learning "
    "labels, basket weights, or approvals. I can help with available PARS project "
    "information, WBS details, and BLS price-index data."
)
# Shown when a figure in the model's answer does not appear in any tool result.
FIGURE_MISMATCH_MESSAGE = (
    "I could not match a figure in the answer to the connected source's results, "
    "so the answer is withheld. Please ask again or check the source directly."
)
# Figures that must appear verbatim in tool evidence: decimals and numbers of three
# or more digits. Short integers (counts, WBS levels) are not checked.
_CHECKED_FIGURE = re.compile(
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b|\b\d{3,}\b"
)
# Identifiers that must also appear in evidence: project IDs and series IDs.
_IDENTIFIER = re.compile(r"\bproj_\d+\b|\b[A-Za-z]{2,}\d{3,}\b", re.IGNORECASE)
# A project reference in a follow-up, for example "proj_002", "proj 2", "project two".
_PROJECT_REF = re.compile(
    r"\bproj(?:ect)?s?[\s_-]*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.IGNORECASE,
)
# Words that tie a follow-up to the previous answer. A grounded prior answer may be
# reused only for such a question; anything else needs a tool result.
_REFERS_TO_PREVIOUS = re.compile(
    r"\b(you|your|just|that|those|these|it|its|previous|above|again|same|earlier|"
    r"last|they|them)\b",
    re.IGNORECASE,
)
_SWITCH_CUE = re.compile(
    r"\b(switch|other|another|next|second|different)\b", re.IGNORECASE
)
_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}
# A small guard for the read-only explanation only. It is not a routing table:
# it applies only when no permitted tool ran, and it never selects a tool.
_WRITE_REQUEST = re.compile(
    r"\b(update|edit|modify|delete|remove|overwrite|reset|approve|write[ _-]?back\w*|"
    r"save|submit|change the|change my|set the)\b",
    re.IGNORECASE,
)


class ChatPolicyError(ValueError):
    """Manifest or provider violates the read-only chat policy."""


class ToolTimeoutError(TimeoutError):
    """An MCP tool call did not finish within TOOL_TIMEOUT_SECONDS."""


SYSTEM_PROMPT = (
    "You assist with NNSA cost-intelligence demonstration data, using only the "
    "permitted read-only MCP tools. Choose a tool from its name and description; "
    "call a tool when it can answer the question. "
    "Answer only from tool results in this conversation. Only state data attributes "
    "explicitly supported by successful MCP tool results or verified conversation "
    "context. Preserve official series identifiers and titles exactly as returned. Do "
    "not infer frequency, units, coverage, dates, or other metadata from a series name "
    "or from general model knowledge. If an attribute is unavailable, say it was not "
    "provided. Never use general "
    "knowledge for project facts, costs, WBS descriptions, schedules, or machine "
    "learning labels. If the tools return no matching records, say that no matching "
    "records were found. If a tool result ends with '[tool result truncated]', say "
    "that the list is incomplete and do not conclude that unseen items are absent. "
    "When a search returns related matches but not the exact "
    "name asked for, report the related matches and say which exact name was not "
    "found. If only part of a question is supported, answer that part "
    "and state which part is unavailable. Search every catalog program: do not set a "
    "program filter such as commodity-based or industry-based unless the user names "
    "one. Build search queries from the core terms "
    "only; leave out generic words such as price, series, index, and data. If a search "
    "returns no results, retry once with fewer core terms, and without any program "
    "filter, before reporting that no "
    "match was found. Before saying that nothing matched, read every result returned "
    "in this turn. If any series or project title contains a core term, list those "
    "titles as related matches and state that they are related, not exact. Never say "
    "no match exists when a returned title contains the core term. "
    "Do not keep calling tools for a detail that no tool provides; "
    "after that, answer with what you have. If the tools cannot provide the "
    "information, say that the connected project and cost-data sources do not "
    "provide it. If the user asks to change data, weights, or approvals, say that "
    "Search is read-only. Cite project and series identifiers from the results, and "
    "say that the data is synthetic. Do not claim a tool ran unless its result is "
    "present. PARS project descriptions exist, but WBS element descriptions are future "
    "scope. CAEF model classifications are candidates, not approved allocations. "
    "Never claim PARS cost baselines, verified cost weights, or PARS write-back. "
    "BLS candidate selection is optional; the analyst controls basket weights."
)


class _TracedHub:
    def __init__(self, hub: MCPHub):
        self.hub = hub
        self.calls: list[dict[str, str]] = []
        # Text of successful tool results in this turn, for the no-match check.
        self.results: list[str] = []
        # True when a tool call raised, as opposed to returning an error result.
        self.raised = False

    def tool_definitions(self) -> list[dict[str, Any]]:
        return self.hub.tool_definitions()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            result = await asyncio.wait_for(
                self.hub.call_tool(name, arguments), timeout=TOOL_TIMEOUT_SECONDS
            )
        except TimeoutError as exc:
            self.raised = True
            self.calls.append({"tool": name, "status": "timeout"})
            raise ToolTimeoutError(name) from exc
        except Exception:
            self.raised = True
            self.calls.append({"tool": name, "status": "error"})
            raise
        status = "error" if result.startswith("MCP tool reported an error:") else "ok"
        self.calls.append({"tool": name, "status": status})
        if status == "ok":
            self.results.append(result)
        return result


def _validate_local_servers(servers: dict[str, Any]) -> None:
    if not servers:
        raise ChatPolicyError("No MCP servers configured for chat")
    for server in servers.values():
        if not server.allowed_tools or "*" in server.allowed_tools:
            raise ChatPolicyError("Chat requires an explicit MCP tool allowlist")
        if not set(server.allowed_tools).issubset(READ_ONLY_TOOLS):
            raise ChatPolicyError(
                "Chat manifest includes a tool outside the read-only list"
            )
        if server.transport == "streamable_http":
            url = urlsplit(server.url or "")
            if url.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ChatPolicyError("Chat MCP servers must use loopback addresses")
        elif server.transport != "stdio":
            raise ChatPolicyError("Unsupported chat MCP transport")


@contextmanager
def _pars_workdir() -> Iterator[Path]:
    """A new temporary directory for one chat call's PARS database.

    It lives in the system temp area, never in the repository, and is removed
    when the call ends. Concurrent calls each get their own directory.
    """
    workdir = Path(tempfile.mkdtemp(prefix="nnsa-chat-pars-"))
    try:
        yield workdir
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _isolate_pars(
    servers: dict[str, ServerConfig], workdir: Path
) -> dict[str, ServerConfig]:
    """Point the PARS server at this call's own database file.

    Setting DATABASE_PATH makes the PARS server build and read a fresh synthetic
    database at this path, so no call touches the checkout's database or
    another call's database.
    """
    if PARS_SERVER not in servers:
        return servers
    pars = servers[PARS_SERVER]
    env = {**(pars.env or {}), "DATABASE_PATH": str(workdir / "pars.duckdb")}
    return {**servers, PARS_SERVER: replace(pars, env=env)}


def _chat_environment() -> dict[str, str]:
    """Reuse portable LLM .env, with explicit process settings taking precedence."""
    repo = Path(__file__).resolve().parents[2]
    env_file = repo / "src" / "portable_llm_mcp" / ".env"
    values = dotenv_values(env_file) if env_file.is_file() else {}
    return {**{k: v for k, v in values.items() if v is not None}, **os.environ}


def _manifest_path(value: str) -> Path:
    """Resolve repository-relative manifests independently of launch directory."""
    path = Path(value)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


def _source_location(exc: BaseException) -> str:
    """File and line of the innermost frame; safe to log, unlike exception text."""
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return "unknown"
    frame = frames[-1]
    return f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"


# Claims that nothing matched, and the titles a catalog search returns.
_NO_MATCH = re.compile(
    r"\b(no|not)\b[^.]{0,40}\b(found|match|matches|matching|exist)\b", re.IGNORECASE
)
_TITLE = re.compile(r'"title":\s*"((?:[^"\\]|\\.)*)"')
# Generic words that do not identify a series. Only the remaining words are used
# to decide whether a returned title is related to the question.
_GENERIC_TERMS = frozenset(
    {
        "search",
        "for",
        "the",
        "and",
        "with",
        "about",
        "what",
        "which",
        "find",
        "show",
        "list",
        "are",
        "there",
        "any",
        "price",
        "prices",
        "series",
        "index",
        "indexes",
        "data",
        "catalog",
        "products",
        "product",
        "bls",
        "pars",
        "available",
        "tell",
        "give",
        "how",
        "many",
        "does",
        "have",
        "this",
        "that",
        "from",
        "project",
        "projects",
        "wbs",
        "elements",
        "element",
        "level",
        "codes",
        "code",
    }
)


def _related_titles(question: str, results: list[str], limit: int = 5) -> list[str]:
    """Titles returned in this turn that share a term with the question.

    Titles matching more distinct question terms come first (so a title with every
    term outranks one with a single shared word); ties keep the tool's order.
    """
    terms = {
        word
        for word in re.findall(r"[a-z]{3,}", question.lower())
        if word not in _GENERIC_TERMS
    }
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for text in results:
        for match in _TITLE.finditer(text):
            title = match.group(1)
            if title in seen:
                continue
            seen.add(title)
            lowered = title.lower()
            score = sum(1 for term in terms if term in lowered)
            if score:
                scored.append((-score, len(scored), title))
    scored.sort()
    return [title for _, _, title in scored[:limit]]


def _reconcile_no_match(question: str, answer: str, results: list[str]) -> str:
    """Never report "no match" when a title returned in this turn is related.

    The model can summarize a search as empty even when its results hold related
    titles. Those titles are listed instead, labelled as related, not exact.
    """
    if not results or not _NO_MATCH.search(answer):
        return answer
    related = _related_titles(question, results)
    if not related:
        return answer
    return (
        "No exact match was returned for this search. The connected catalog returned "
        "related titles, which are not exact matches: " + "; ".join(related) + "."
    )


def _grounded_answer(
    question: str,
    answer: str,
    tools: list[dict[str, str]],
    *,
    previous_grounded: bool = False,
) -> str:
    """Return the model's answer only when a permitted tool actually answered.

    With no successful tool result, the model's text is not a grounded fact, so it
    is replaced by a fixed message. Matching no records is different: a tool that
    ran and returned nothing still counts, and the model reports that from its result.
    """
    if any(call.get("status") == "ok" for call in tools):
        return answer
    if previous_grounded and _REFERS_TO_PREVIOUS.search(question):
        # A follow-up about the previous, tool-backed answer; the prompt limits the
        # model to that context and forbids new facts. Any other question with no
        # tool result is general knowledge and is not shown.
        return answer
    if _WRITE_REQUEST.search(question):
        return READ_ONLY_MESSAGE
    return UNSUPPORTED_MESSAGE


def _figures(text: str) -> set[str]:
    """Checked numbers as whole tokens, with thousands separators removed."""
    return {match.replace(",", "") for match in _CHECKED_FIGURE.findall(text)}


def _identifiers(text: str) -> set[str]:
    return {match.lower() for match in _IDENTIFIER.findall(text)}


def _unmatched_figure(answer: str, evidence_texts: list[str]) -> bool:
    """True when a checked figure or identifier in the answer lacks evidence.

    ``evidence_texts`` holds the tool results, plus the question (so a figure the user
    typed may be repeated) and, for a follow-up, the earlier answer.
    """
    evidence = "\n".join(evidence_texts)
    if _figures(answer) - _figures(evidence):
        return True
    return bool(_identifiers(answer) - _identifiers(evidence))


def _project_refs(text: str) -> set[str]:
    refs = set()
    for raw in _PROJECT_REF.findall(text):
        value = _NUMBER_WORDS.get(raw.lower(), raw.lower())
        refs.add(str(int(value)) if value.isdigit() else value)
    return refs


def _names_other_project(
    question: str, previous_question: str, previous_answer: str
) -> bool:
    """True when a follow-up asks to switch or names a new project."""
    if _SWITCH_CUE.search(question):
        return True
    return bool(
        _project_refs(question)
        - _project_refs(previous_question + " " + previous_answer)
    )


def _failure_message(exc: BaseException, *, tool_raised: bool) -> str:
    """Actionable guidance for a failed Search, without secrets or payloads.

    Only static text, HTTP status codes, configured server names, and exception
    class names reach the UI or the local log. Provider response bodies, tool
    arguments, and tool results are never shown or logged.
    """
    if isinstance(exc, MCPServerStartError):
        message = (
            f"The MCP server '{exc.server}' did not start or is not reachable. "
            "Check that its service is running and its local data is available. "
            "For BLS over localhost HTTP, see the chat quickstart."
        )
        detail = f"server={exc.server} error={exc.error_type}"
    elif isinstance(exc, ToolTimeoutError):
        message = (
            "A permitted MCP tool did not respond in time. Check that its local "
            "service is running, then try again."
        )
        detail = f"tool timeout={exc}"
    elif isinstance(exc, TimeoutError):
        message = (
            "Search did not finish in time. Check the local MCP services and the "
            "model endpoint, then try again."
        )
        detail = "chat timeout"
    elif isinstance(exc, ChatPolicyError):
        message = f"Chat is limited to read-only tools: {exc}."
        detail = "policy"
    elif isinstance(exc, LLMConfigError):
        message = f"Model configuration is not valid: {exc}"
        detail = "config"
    elif isinstance(exc, MCPConfigurationError):
        message = (
            "The MCP server configuration is not valid. Check the chat manifest "
            "and its environment variables."
        )
        detail = "mcp-config"
    elif isinstance(exc, LLMUnavailableError):
        status = exc.status_code
        error_type = exc.error_type or ""
        if status in (401, 403):
            message = (
                "Ask Sage authentication failed. Check LLM_API_KEY and LLM_AUTH_HEADER."
            )
        elif status == 404:
            message = (
                "The configured model or endpoint was not found. Check "
                "LLM_CHAT_MODEL and LLM_BASE_URL."
            )
        elif "redirected" in str(exc):
            message = "The model endpoint redirected the request, which is not allowed."
        elif "Timeout" in error_type:
            message = (
                "The model request timed out. Try again, or raise LLM_TIMEOUT_SECONDS."
            )
        elif error_type in {"ConnectError", "NetworkError", "ProxyError"}:
            message = (
                "The model endpoint is unreachable. Check the network route to the "
                "configured endpoint."
            )
        else:
            message = "The model endpoint returned an error. See the local log."
        detail = f"status={status} error={error_type or 'none'}"
    elif isinstance(exc, LLMResponseError):
        message = "The model returned an unexpected response."
        detail = "response"
    elif isinstance(exc, ToolLoopError):
        message = (
            "The model did not finish within the tool-call limit. Try a narrower "
            "question."
        )
        detail = "tool-loop"
    elif tool_raised:
        message = (
            "A permitted MCP tool failed, so the answer may be incomplete. "
            "See the local log."
        )
        detail = f"tool error={type(exc).__name__}"
    else:
        message = _DEFAULT_MESSAGE
        detail = f"error={type(exc).__name__}"
    _LOG.warning("Search failed (%s) at %s", detail, _source_location(exc))
    return message


class _CallState:
    """What a failed call still knows, for the failure message."""

    def __init__(self) -> None:
        self.traced: _TracedHub | None = None

    @property
    def tool_raised(self) -> bool:
        return bool(self.traced is not None and self.traced.raised)


async def _answer(
    question: str,
    *,
    previous_question: str,
    previous_answer: str,
    previous_grounded: bool,
    manifest_path: Path,
    environment: dict[str, str],
    state: _CallState,
) -> dict[str, Any]:
    settings = load_llm_settings(environment)
    if settings.provider not in (
        LLMProvider.OLLAMA,
        LLMProvider.ASKSAGE,
        LLMProvider.OPENAI,
    ):
        raise ChatPolicyError("Chat supports local Ollama or approved NNSA Ask Sage")
    servers = load_mcp_servers(manifest_path, environment=environment)
    _validate_local_servers(servers)
    prompt = question
    if previous_question.strip() and previous_answer.strip():
        prompt = (
            f"Previous user question: {previous_question[:1000]}\n"
            f"Previous assistant answer: {previous_answer[:2000]}\n"
            f"Current user question: {question}"
        )
    llm = create_llm_client(settings)
    try:
        with _pars_workdir() as workdir:
            async with MCPHub(
                _isolate_pars(servers, workdir), max_result_chars=CHAT_RESULT_CHARS
            ) as hub:
                traced = _TracedHub(hub)
                state.traced = traced
                answer = await MCPAgent(
                    llm=llm, hub=traced, model=settings.chat_model, max_round_trips=4
                ).ask(prompt, system_prompt=SYSTEM_PROMPT)
                tools = traced.calls
                grounded = _grounded_answer(
                    question,
                    answer,
                    tools,
                    previous_grounded=previous_grounded,
                )
                verified = any(c.get("status") == "ok" for c in tools)
                evidence = [*traced.results, question]
                if previous_grounded:
                    evidence.append(previous_answer)
                if (verified or previous_grounded) and _unmatched_figure(
                    grounded, evidence
                ):
                    return {
                        "state": "loaded",
                        "message": "",
                        "answer": FIGURE_MISMATCH_MESSAGE,
                        "tools": tools,
                        "grounded": False,
                    }
                return {
                    "state": "loaded",
                    "message": "",
                    "answer": _reconcile_no_match(question, grounded, traced.results),
                    "tools": tools,
                    "grounded": verified,
                }
    finally:
        await llm.aclose()


async def ask_readonly_chat(
    question: str,
    *,
    previous_question: str = "",
    previous_answer: str = "",
    previous_grounded: bool = False,
) -> dict[str, Any]:
    """Call authorized local MCP tools; return answer and actual tool trace.

    ``previous_grounded`` says the previous answer came from a successful tool
    result, so a follow-up may be answered from that answer.
    """
    question = question.strip()
    if not question or len(question) > 2000:
        return {
            "state": "error",
            "message": "Enter a question (up to 2,000 characters).",
            "answer": "",
            "tools": [],
        }
    environment = _chat_environment()
    # Chat uses CHAT_MANIFEST unless COST_INTEL_CHAT_MCP_MANIFEST names another
    # file. MCP_SERVERS_FILE is the host manifest, so it is not read here.
    manifest = environment.get("COST_INTEL_CHAT_MCP_MANIFEST") or ""
    manifest_path = _manifest_path(manifest) if manifest else CHAT_MANIFEST
    if not manifest_path.is_file():
        return {
            "state": "unavailable",
            "message": (
                "Local chat MCP configuration is not available; "
                "basket analysis still works."
            ),
            "answer": "",
            "tools": [],
        }
    # Caller-supplied grounding state is untrusted: any MCP caller can send
    # previous_grounded=True with arbitrary previous_answer text. Reuse of a prior
    # grounded answer is disabled until the grounding state is held server-side, so
    # every answer here must come from a tool result of this call.
    previous_grounded = False
    state = _CallState()
    try:
        return await asyncio.wait_for(
            _answer(
                question,
                previous_question=previous_question,
                previous_answer=previous_answer,
                previous_grounded=previous_grounded,
                manifest_path=manifest_path,
                environment=environment,
                state=state,
            ),
            timeout=CHAT_TOTAL_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        # Never return tool arguments, provider response bodies, or secrets.
        return {
            "state": "error",
            "message": _failure_message(exc, tool_raised=state.tool_raised),
            "answer": "",
            "tools": [],
        }
