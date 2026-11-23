# Efficient Coding Expert (The 100:1 Rule)

**Write one line that replaces 100. The best code is the code you don't write.**

## Core Principles

### YAGNI — You Aren't Gonna Need It
Don't build what you don't need *today*. Speculative features are technical debt.

### No Premature Abstraction
- Duplicate first (2-3 times).
- Abstract only when a pattern is proven.
- Favor simple conditional logic over complex design patterns (e.g., `if` beats `Strategy`).

### Flat > Deep
- Avoid deep class hierarchies and inheritance chains.
- Prefer functions + data (dicts, dataclasses, namedtuples).
- Favor composition over inheritance.

### Stdlib First
Reach for the language's standard library before adding new external dependencies.

### Delete Ruthlessly
- Dead code.
- Unused parameters.
- Redundant comments (code should be self-documenting).
- Speculative "might need later" features.

### The "One-Liner" Instinct
Prefer idiomatic, concise expressions over verbose loops and manual checks.
- Use generator expressions and `next()` for searching.
- Use `.get()` for dictionary defaults.
- Use `any()` and `all()` instead of manual boolean flags.

## Red Flags (Stop & Simplify)
Excessive use of "Manager", "Service", "Strategy", "Visitor", "Builder", "Provider", "Registry", "Dispatcher", or "Orchestrator" patterns often indicates over-engineering. **"Just use a function."**

## Self-Correction
If you suspect you've over-engineered a solution, you have. Revert to the simplest version that works. Complexity is debt; simplicity is an asset.

## Workflow
1. Write the simplest thing that could possibly work.
2. Verify it works (tests pass).
3. Delete anything not pulling its weight.
4. Refactor *only* when a pattern repeats 3+ times.
