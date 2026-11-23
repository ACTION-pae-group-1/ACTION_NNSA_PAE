# BLS escalation conversation evals

These evals measure what unit tests cannot: how an agent behaves when it
drives the BLS MCP tools through a conversation with a user. Each episode
runs the real server (in-process, through a real MCP client) against a
deterministic snapshot, with a scripted user on the other side.

## Run

From the repository root:

```cmd
uv run --locked poe eval-selftest
```

No model, key or network is needed. It runs scripted agents and exits
non-zero unless the reference ("oracle") agents pass every check **and** each
deliberately flawed agent fails exactly the checks it should. Run it first:
it proves the graders work before you spend anything on a model.

To evaluate a real model, put the `LLM_*` variables used by
`src/portable_llm_mcp` in `src/portable_llm_mcp/.env` (copy
`src/portable_llm_mcp/.env.example`; never put keys in chat or Git). The eval
does **not** read that file by itself, so point uv at it in every new
terminal, then run:

```cmd
set "UV_ENV_FILE=src/portable_llm_mcp/.env"
uv run --locked python -m eval.bls.runner --agent model --case known-basket-missing-target-year
uv run --locked poe eval
uv run --locked python -m eval.bls.runner --agent model --repetitions 3
```

Run one case first to check the setup and the cost before a full run. (On
macOS or Linux, use `export UV_ENV_FILE=src/portable_llm_mcp/.env`.) The root
`.env` is not needed: the eval builds its own snapshot.

**Approved endpoints only.** Model runs use Ask Sage `-gov` models or local
Ollama (see `docs/DATA_HANDLING.md`). The client rejects any other provider,
any `LLM_BASE_URL` host outside the approved list, and any Ask Sage model whose
name does not end in `-gov`.

**AskSage.** In AskSage, open **Settings > API Keys** and create a key (the
`query` scope is enough; keys unused for 30 days are revoked). Confirm the API
host for your AskSage instance with your AskSage administrator; the public
docs only document `api.asksage.ai`, and the client only accepts
`api.nnsa.asksage.ai`. Then set:

```dotenv
LLM_PROVIDER=asksage
LLM_BASE_URL=https://api.nnsa.asksage.ai/server/openai/v1
LLM_API_KEY=...                  # or ASKSAGE_API_KEY
LLM_CHAT_MODEL=gpt-5.4-gov       # the default; must end in -gov
LLM_TIMEOUT_SECONDS=120
```

Leave `LLM_AUTH_HEADER` unset: the OpenAI-compatible endpoint takes the API key
as `Authorization: Bearer <key>`, the default. To list the models your key can
use (with `UV_ENV_FILE` set as above):

```cmd
uv run python -c "import httpx,os; r=httpx.get(os.environ['LLM_BASE_URL']+'/models', headers={'Authorization':'Bearer '+os.environ['LLM_API_KEY']}); print(r.status_code); print(r.text[:3000])"
```

Pick a model that supports tool calling and is marked CUI-compliant in
AskSage. Model IDs change, so list them rather than copying one.

| You see | Likely cause |
| --- | --- |
| `LLM_API_KEY is required` | `UV_ENV_FILE` is not set in this terminal |
| HTTP 401 or 403 | Wrong key or host, or `LLM_AUTH_HEADER` is set |
| HTTP 404, or the model is rejected | The model ID is not available to your key |
| `Ask Sage models must end in -gov` | The model ID does not follow the `-gov` rule |
| HTTP 429 | AskSage token quota used up (it resets on the 1st of the month) |

Every turn resends the whole conversation, so a run uses more AskSage tokens
than the messages alone suggest. A refused or truncated response is scored as
an agent error; an API outage or HTTP error is excluded as infrastructure.

The committed [results/SELFTEST.md](results/SELFTEST.md) is the last
self-test summary.

## Recorded results

Every agent run (`--agent oracle`, a flawed agent, or `--agent model`) is
recorded in its own directory, `eval/bls/results/runs/<run_id>/`. The run ID
is the UTC start time plus the agent name. The self-test is a check of the
harness, not a result, so it is not recorded. Pass `--no-record` to skip
recording.

| File | Contents | In Git? |
| --- | --- | --- |
| `run.json` | What was run, every check for every episode, and the roll-up | Yes, commit it to keep the result |
| `summary.md` | The roll-up as readable tables | Yes |
| `episodes.jsonl` | Full transcripts: every message and tool call, one episode per line | Ignored |
| `errors.jsonl` | Episodes that failed for infrastructure reasons | Ignored |

Read results back with:

```cmd
uv run --locked poe eval-report
uv run --locked poe eval-report --run latest
uv run --locked poe eval-report --compare 20261115T1749 latest
```

- With no arguments it lists every run: episodes, how many passed every
  check, and the pass rate in each dimension.
- `--run` shows one run by case and by check.
- `--compare BEFORE AFTER` shows each check's pass rate in both runs, with
  the checks that changed first.

Run IDs can be shortened to any unique prefix; `latest` is the newest run.

**What a run records, so results stay comparable:**

- the agent, and for a model run the provider and model name (never a key);
- the commit, and whether there were uncommitted changes;
- three fingerprints: the eval itself (cases, graders, world, scripted user),
  the server's tool definitions, and the system prompt. Scores from runs with
  different eval fingerprints measure different things; `--compare` says so,
  and also warns when the two runs covered different cases;
- per episode: every check, duration, turns and tool-call count.

**Infrastructure failures are not scored.** If the model endpoint is down or
times out, the episode is listed in `errors.jsonl` and left out of every pass
rate, so an outage cannot look like bad agent behaviour. An agent that runs
out of tool-call rounds *is* scored, because that is its behaviour.

Token usage and cost are not recorded: the model client does not report them.

## The three cases

### 1. Known basket, missing target year (deterministic)

> I have a 2014 materials estimate for a vertical construction project, a
> mid-rise building. The materials cost is 45% ready-mix concrete, 35% steel
> from iron and steel mills, and 20% sawmill lumber. Please normalize it
> using annual-average PPI industry indexes.

The user does not say which year to normalize **to**. The agent must ask; the
user then answers 2026. There is exactly one right answer:

| Component | Weight | 2014 | 2026 | Relative |
| --- | --- | --- | --- | --- |
| Ready-mix concrete `PCU327320327320` | 0.45 | 200.0 | 310.0 | 1.5500 |
| Iron and steel mills `PCU331110331110` | 0.35 | 180.0 | 252.0 | 1.4000 |
| Sawmills `PCU321113321113` | 0.20 | 150.0 | 195.0 | 1.3000 |

Composite = 0.45 × 1.55 + 0.35 × 1.40 + 0.20 × 1.30 = **1.4475** (+44.75%).

### 2. Mixed materials and labor, one annual basis (deterministic)

> I have a 2014 cost estimate for an office building renovation: 60%
> materials cost, which I index with PPI ready-mix concrete, and 40% labor
> cost, which I index with a labor cost index. Please normalize it using
> annual indexes.

Again the target year is missing and must be asked for (the user answers
2026). The materials series is PPI with annual averages; the labor series
lives in the CI program and publishes **quarterly** observations only, like
the real Employment Cost Index. The server aligns a quarterly-only series to
the spec's annual periods by resolving it from its fourth-quarter observation
and disclosing that in the result, the ledger and the provenance:

`0.60 × 310/200 + 0.40 × 224/140 = 0.93 + 0.64 = 1.5700` (+57.00%)

with the labor relative `224/140` taken from its 2014-Q04 and 2026-Q04 rows.
The citation contract here includes the quarter: the answer must say
`2014-Q04` and `2026-Q04` for the labor series, not imply an annual average
the program never published.

### 3. Vague project, negotiated basket (open-ended)

> We're budgeting a new building and our cost estimate is old. Can you bring
> it up to today's dollars?

The user knows more but only says it when asked: a five-story steel-framed
office building, estimate in 2014 dollars, escalate to 2026, materials only,
structural steel is about half of the materials cost and the agent should
propose the rest. The user says yes when shown a proposal.

There is no single right basket, so this case is graded on behaviour and
internal consistency rather than one number.

## What is graded

Results are reported in four separate dimensions, so a regression in one is
not hidden by the others. All grading is programmatic, from the recorded tool
calls and messages.

| Dimension | Deterministic cases (1, 2) | Negotiated case (3) |
| --- | --- | --- |
| **process** | Asked for the target year before calculating; validated the exact spec it then calculated; result came from `calculate_index_from_bls` | Drew out periods, weights and project type or scope before calculating; showed the proposed series and weights, got a yes, and calculated that same basket; validated the exact spec it then calculated |
| **accuracy** | Basket equals the stated commodities and percentages; periods are 2014 → 2026; factor equals the known answer (1.4475 in case 1, 1.57 in case 2) | Periods are 2014 → 2026; steel series carry the stated 0.5; at least three components; weights sum to 1; factor equals an independent recomputation for the basket the agent chose |
| **format** | Final answer states the factor and percent change, cites every series ID with its own weight next to it, both periods, and the snapshot ID; case 2 additionally requires each quarterly-sourced series' year-quarter (e.g. `2014-Q04`) | Same as the deterministic cases, without the quarter requirement (annual series only) |
| **guardrails** | No live BLS API call; no calculation from index values the agent typed in; every series was returned by the catalog tools before it was used | Same |

The **format** row is the citation contract. An answer that is numerically
right but does not say where the numbers came from fails it.

## The world

`world.py` builds a published DuckDB snapshot from the real PPI industry
catalog checked into `src/bls_mcp/docs/sample_data` (4,510 series, so series
discovery is realistic) plus **synthetic** observations: annual averages for
seven construction-material series, 2014 through 2026, and one ECI-like
labor series (`CIU1010000000000I`) with quarterly rows only, ingested
through the real CI pipeline from a minimal synthetic input set. The
snapshot ID is `eval_synthetic_world`. **The values are invented for the
evals and are not BLS data**; they exist so every expected answer can be
computed by hand.

Because the world's labor series is quarterly-only, case 2 exercises the
server's quarterly-to-annual alignment (`QUARTERLY_ANNUAL_ANCHOR`): the
labor component resolves from its Q04 rows, and the alignment is disclosed
in the component result, the ledger warnings and the provenance.

## Layout

| File | Purpose |
| --- | --- |
| `world.py` | Builds the snapshot; holds the values graders recompute from |
| `cases.py` | The three cases: opening request, scripted user facts, graders |
| `simulated_user.py` | Scripted user: discloses a fact only when asked about it |
| `agents.py` | Scripted oracle and flawed agents; `ModelAgent` for a real model |
| `graders.py` | The checks, one function per behaviour |
| `transcript.py` | Records messages and every tool call |
| `runner.py` | Runs episodes, grades them, prints results |
| `recording.py` | Writes and reads run records; computes the roll-up |
| `report.py` | Lists, shows and compares recorded runs |

## Limits to keep in mind

- **The scripted user matches keywords.** It reads only the parts of a message
  that ask something (questions, requests such as "Please confirm ...", and
  list items a request introduces or points back to; see `simulated_user.py`)
  and answers a fact whose keywords appear there. A message that asks nothing
  it can answer ends the conversation. It was widened after the first model
  runs, where 23 of 25 episodes ended on requests it did not recognise; runs
  before and after that change have different eval fingerprints and are not
  comparable. A request that points back at a list several paragraphs earlier
  is still missed. Read the transcript before trusting a failed process
  check, and widen the keywords when a real phrasing is missed.
- **Three cases is a smoke signal, not a benchmark.** With so few cases, only
  large differences between models or prompts are meaningful. Use
  `--repetitions` and compare per-check results.
- **Weights are read from the line a series ID is on.** The citation and
  confirmation checks take the nearest percentage or 0–1 fraction on the same
  line as each series ID. An answer that puts series and weights in separate
  lists will be marked as not stating them.
- **Open-ended quality is not judged.** Case 3 checks that the basket is
  valid, honours what the user said and was confirmed. It does not judge
  whether flat glass was a sensible choice for an office building. That needs
  a human or a calibrated LLM judge.
- **Model runs are untested here.** `ModelAgent` is covered by a test with a
  scripted stand-in for the model; it has not been run against a real model
  in this repository's CI.

## Adding a case

1. Add any series values you need to `ENDPOINTS` in `world.py`.
2. Define a `Case` in `cases.py`: the opening message, the facts the user
   holds with the keywords that unlock them, and the graders.
3. Add an oracle agent and at least one flawed agent to `agents.py`, register
   them in `SCRIPTED`, and list the flawed agent's expected failures in
   `EXPECTED_FAILURES` in `runner.py`.
4. Run `poe eval-selftest`.

## Longitudinal tracking and lessons

The existing `run.json` files remain the only source of score data. To see a
chronological suite-level and per-case history:

```cmd
uv run --locked poe eval-history
uv run --locked python -m eval.bls.history --format csv --output eval/bls/results/score_history.csv
```

The CSV is a **derived export**, not a second ledger; regenerate it when
needed. It includes run IDs, commits, model names, fingerprints, denominators,
success rates, and per-dimension rates. Infrastructure errors are excluded
from scoring. Never compare changed eval fingerprints as if they were the
same measurement instrument.

Record investigated failure patterns and interventions using
[`lessons/TEMPLATE.md`](lessons/TEMPLATE.md). Include baseline and follow-up
run IDs, a hypothesis, the exact code change, and the observed score delta.
Review generated CSVs before committing; transcripts remain ignored.

## Optional local Phoenix tracing

Phoenix is **not** required for grading, `poe check`, or `eval-selftest`.
The dev dependency group already includes OpenTelemetry SDK and OTLP HTTP exporter;
no `phoenix` package is needed in the BLS environment. Run Phoenix separately:

```powershell
uvx --from arize-phoenix phoenix serve
Copy-Item eval/bls/.env.example eval/bls/.env
# Edit eval/bls/.env and set BLS_EVAL_PHOENIX_ENABLED=true
$env:UV_ENV_FILE = "src/portable_llm_mcp/.env"
uv run --locked --env-file eval/bls/.env python -m eval.bls.runner --agent model --case known-basket-missing-target-year
```

Keep `src/portable_llm_mcp/.env` for provider/model credentials (Ask Sage),
`eval/bls/.env` for local tracing switches, and the root `.env` for BLS server
settings. **Do not add Phoenix settings or secrets to the root `.env`.**
`eval/bls/.env` is ignored by Git. Environment variables set in the shell
take precedence over `--env-file`; unset stale overrides when debugging.

Open http://localhost:6006 and choose project `bls-mcp-evals`. Each episode
produces a root span with child `agent.turn` and `mcp.tool` spans. Spans contain
only case/model identifiers, tool names, turn numbers, outcome flags and counts;
no user messages, model outputs, arguments, or result bodies are exported.
Recorded `run.json` episodes include a `trace_id` when tracing is enabled.
Trace IDs can be matched to Phoenix traces; they are null when disabled.
The exporter is best effort: if Phoenix is offline, evaluation scoring continues.
Only enable tracing where local trace storage is authorized.

## Expanded scenario coverage

The suite includes nine cases (the original three plus six additions):

| Case | Main behavior | Oracle factor |
| --- | --- | --- |
| `ambiguous-escalation-request` | Elicit scope, periods, weights; confirm basket | 1.5050 |
| `commodity-series-selection` | Discover correct PPI industry series | 1.5650 |
| `mixed-labor-materials-alignment` | Disclose Q04 labor alignment with annual PPI | 1.5700 |
| `unavailable-target-period` | Explain absent 2030 observations without calculating | No factor |
| `invalid-weighted-basket` | Reject 115% total, obtain 45/35/20 correction | 1.4475 |
| `source-provenance-audit` | Report series, weights, observations, method, synthetic source | 1.4475 |

The negative-outcome case uses dedicated graders because a correct refusal
must **not** be penalized for omitting a successful calculation. Every new
case has a scripted reference agent and a deliberately flawed counterpart.
The self-test requires each new flawed agent to fail its targeted checks;
other downstream failures are permitted. Existing flawed agents retain their
strict exact-failure assertions.

The synthetic world uses real-looking series identifiers but invented index
levels. Never describe these levels as published BLS observations.

Run the self-test before live model evaluation:

```powershell
uv run --locked poe eval-selftest
uv run --locked python -m eval.bls.runner --agent oracle --no-record
```

Run one new case with the approved model configuration and optional local
Phoenix tracing (with `eval/bls/.env` configured):

```powershell
uv run --locked --env-file src/portable_llm_mcp/.env `
  --env-file eval/bls/.env `
  python -m eval.bls.runner --agent model `
  --case commodity-series-selection
```

On Windows, initialize `truststore` before the runner when required by your
approved enterprise CA setup; see the existing Ask Sage TLS guidance. Do not
disable certificate verification. Model results are recorded in the existing
run history and are not committed to Git. Share sanitized `run.json` and
`summary.md` artifacts from selected runs for failure triage; remove prompts,
responses, internal metadata, and any credentials not approved for sharing.

When comparing scores across suite versions, compare only runs with compatible
evaluation fingerprints. Adding cases changes the aggregate denominator; keep
per-case comparisons separate from whole-suite trend lines.

### Commodity basket confirmation

The `commodity-series-selection` simulated user approves a proposed basket
only when the agent explicitly pairs all three expected series IDs with their
60/25/15 weights. Otherwise it asks for the mapping instead of approving
blindly. Agents can also validate and calculate directly without confirmation.
The case allows 14 turns for the additional exchange. This changes the eval
fingerprint, so do not interpret comparisons with older runs as controlled
MCP-tooling improvements.
