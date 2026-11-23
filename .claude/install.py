#!/usr/bin/env python3
"""Install and validate the small repository-scoped .claude package."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import stat
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

JsonObject = dict[str, Any]
RUNTIME_NAMES = {
    ".read_state.json",
    ".read_state.json.lock",
    ".tdd_state.json",
    ".tdd_state.json.lock",
    ".test_baseline.json",
    ".test_baseline.json.lock",
    ".test_hook.lock",
    ".tool_failure_state.json",
    ".tool_failure_state.json.lock",
    ".tool_capability_state.json",
    ".tool_capability_state.json.lock",
}
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
COPY_FILES = {
    "README.md",
    "HOOK_AUDIT.md",
    "install.py",
    "settings_hooks_template.json",
    "settings.local.example.json",
    ".gitignore",
}
PLACEHOLDERS = (Path(".gitkeep"), Path("plans/TEMPLATE.md"))
HOOK_RE = re.compile(r"\.claude/hooks/([A-Za-z0-9_.-]+)")
MANAGED_HOOK_NAMES = {
    "hook_common.py",
    "tool_call_context.py",
    "tool_input_preflight.py",
    "tool_failure_recovery.py",
}
DEPRECATED_ENV_KEYS = {
    "CLAUDE_TDD_MODE",
    "CLAUDE_READ_TTL_SECONDS",
    "CLAUDE_TDD_RESULT_TTL_SECONDS",
    "CLAUDE_TEST_HOOK_TIMEOUT_SECONDS",
    "CLAUDE_AUTO_READ_BEFORE_WRITE",
    "CLAUDE_POST_SYNTAX_STRICT",
    "CLAUDE_PYTHON_TEST_RUNNER",
    "CLAUDE_PREFLIGHT_AUTO_APPROVE",
    "CLAUDE_EXPLORE_POLICY",
    "CLAUDE_EXPLORE_CAPABILITY_TTL_SECONDS",
    "CLAUDE_EXPLORE_SUCCESS_TTL_SECONDS",
    "CLAUDE_LOCAL_MODEL_AVAILABLE_TOOLS",
}


class InstallError(RuntimeError):
    pass


def load_json(path: Path) -> JsonObject:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallError(f"Required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InstallError(
            f"Malformed JSON in {path} at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise InstallError(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def hook_script(command: Any) -> str | None:
    if not isinstance(command, str):
        return None
    match = HOOK_RE.search(command.replace("${CLAUDE_PROJECT_DIR}/", ""))
    return match.group(1) if match else None


def hook_groups(hooks: Any):
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if isinstance(group, dict):
                yield event, group


def referenced_hooks(hooks: Any) -> set[str]:
    names: set[str] = set()
    for _event, group in hook_groups(hooks) or ():
        for hook in group.get("hooks", []):
            if isinstance(hook, dict):
                name = hook_script(hook.get("command"))
                if name:
                    names.add(name)
    return names


def validate_hook_map(hooks: Any, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(hooks, dict):
        return [f"{label}: hooks must be an object"]
    for event, groups in hooks.items():
        if not isinstance(event, str) or not event:
            errors.append(f"{label}: event names must be non-empty strings")
            continue
        if not isinstance(groups, list):
            errors.append(f"{label}.{event}: must be a list")
            continue
        for index, group in enumerate(groups):
            where = f"{label}.{event}[{index}]"
            if not isinstance(group, dict):
                errors.append(f"{where}: group must be an object")
                continue
            matcher = group.get("matcher")
            if event != "UserPromptSubmit" and (
                not isinstance(matcher, str) or not matcher.strip()
            ):
                errors.append(f"{where}: matcher must be a non-empty string")
            if (
                event == "UserPromptSubmit"
                and matcher is not None
                and not isinstance(matcher, str)
            ):
                errors.append(f"{where}: matcher must be omitted or a string")
            items = group.get("hooks")
            if not isinstance(items, list) or not items:
                errors.append(f"{where}: hooks must be a non-empty list")
                continue
            for hook_index, hook in enumerate(items):
                location = f"{where}.hooks[{hook_index}]"
                if not isinstance(hook, dict) or hook.get("type") != "command":
                    errors.append(f"{location}: hook type must be command")
                    continue
                command = hook.get("command")
                if not isinstance(command, str) or not command.strip():
                    errors.append(f"{location}: command must be a non-empty string")
                if any(key in hook for key in ("args", "if")):
                    errors.append(
                        f"{location}: args/if inline expressions are not supported"
                    )
                timeout = hook.get("timeout")
                if timeout is not None and (
                    isinstance(timeout, bool)
                    or not isinstance(timeout, int)
                    or timeout <= 0
                ):
                    errors.append(f"{location}: timeout must be a positive integer")
    return errors


def group_key(event: str, group: JsonObject) -> tuple[str, str]:
    matcher = group.get("matcher")
    return event, matcher if isinstance(matcher, str) else ""


def hook_key(hook: JsonObject) -> tuple[str, str]:
    return str(hook.get("type", "")), str(hook.get("command", ""))


def custom_hooks(existing: Any) -> JsonObject:
    """Keep only target hooks not owned by this package."""
    result: JsonObject = {}
    for event, group in hook_groups(existing) or ():
        kept: list[JsonObject] = []
        for hook in group.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            name = hook_script(hook.get("command"))
            if name in MANAGED_HOOK_NAMES:
                continue
            kept.append(deepcopy(hook))
        if kept:
            copy = deepcopy(group)
            copy["hooks"] = kept
            result.setdefault(event, []).append(copy)
    return result


def merge_hook_maps(canonical: JsonObject, existing: Any) -> JsonObject:
    result = deepcopy(canonical)
    custom = custom_hooks(existing)
    locations: dict[tuple[str, str], JsonObject] = {}
    for event, group in hook_groups(result) or ():
        locations[group_key(event, group)] = group
    for event, group in hook_groups(custom) or ():
        key = group_key(event, group)
        if key not in locations:
            result.setdefault(event, []).append(deepcopy(group))
            locations[key] = result[event][-1]
            continue
        current = locations[key].setdefault("hooks", [])
        seen = {hook_key(item) for item in current if isinstance(item, dict)}
        for hook in group.get("hooks", []):
            if isinstance(hook, dict) and hook_key(hook) not in seen:
                current.append(deepcopy(hook))
                seen.add(hook_key(hook))
    return result


def canonical_present(installed: Any, canonical: Any) -> bool:
    if not isinstance(installed, dict) or not isinstance(canonical, dict):
        return False
    installed_locations: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for event, group in hook_groups(installed) or ():
        installed_locations[group_key(event, group)] = {
            hook_key(hook) for hook in group.get("hooks", []) if isinstance(hook, dict)
        }
    for event, group in hook_groups(canonical) or ():
        expected = {
            hook_key(hook) for hook in group.get("hooks", []) if isinstance(hook, dict)
        }
        if not expected.issubset(
            installed_locations.get(group_key(event, group), set())
        ):
            return False
    return True


def validate_settings(
    settings: JsonObject, label: str, *, require_hooks: bool
) -> list[str]:
    errors: list[str] = []
    env = settings.get("env")
    if env is not None:
        if not isinstance(env, dict):
            errors.append(f"{label}: env must be an object")
        else:
            for key, value in env.items():
                if not isinstance(value, str):
                    errors.append(f"{label}: env value {key!r} must be a string")
    permissions = settings.get("permissions")
    if permissions is not None and not isinstance(permissions, dict):
        errors.append(f"{label}: permissions must be an object")
    if "hooks" in settings:
        errors.extend(validate_hook_map(settings["hooks"], label))
    elif require_hooks:
        errors.append(f"{label}: hooks must be an object")
    return errors


def validate_tree(
    claude_dir: Path, *, strict: bool = False
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    settings = load_json(claude_dir / "settings.json")
    template = load_json(claude_dir / "settings_hooks_template.json")
    errors.extend(validate_settings(settings, "settings.json", require_hooks=True))
    if set(template) != {"hooks"}:
        errors.append("settings_hooks_template.json must contain only hooks")
    errors.extend(
        validate_hook_map(template.get("hooks"), "settings_hooks_template.json")
    )
    if not canonical_present(settings.get("hooks"), template.get("hooks")):
        errors.append("settings.json is missing one or more canonical hooks")

    local = claude_dir / "settings.local.json"
    if local.exists():
        errors.extend(
            validate_settings(
                load_json(local), "settings.local.json", require_hooks=False
            )
        )

    for relative in PLACEHOLDERS:
        path = claude_dir / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"{relative.as_posix()} must be a regular file")

    active = referenced_hooks(settings.get("hooks"))
    for name in sorted(active):
        path = claude_dir / "hooks" / name
        if not path.is_file():
            errors.append(f"Active hook implementation is missing: {name}")
    if strict:
        for path in sorted((claude_dir / "hooks").glob("*.py")):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"{path}: {exc}")
    return errors, warnings


def should_copy(relative: Path) -> bool:
    if relative.name in RUNTIME_NAMES:
        return False
    if any(part in CACHE_PARTS for part in relative.parts):
        return False
    return relative.suffix not in {".pyc", ".pyo"}


def same_file(source: Path, target: Path) -> bool:
    return (
        target.is_file()
        and source.stat().st_size == target.stat().st_size
        and filecmp.cmp(source, target, shallow=False)
    )


def copy_tree(source: Path, target: Path) -> int:
    if not source.is_dir() or source.resolve() == target.resolve():
        return 0
    changed = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if not should_copy(relative):
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not same_file(path, destination):
                shutil.copy2(path, destination)
                changed += 1
    return changed


def copy_file(source: Path, target: Path) -> bool:
    if (
        not source.is_file()
        or (target.exists() and source.resolve() == target.resolve())
        or same_file(source, target)
    ):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def ensure_empty(path: Path) -> bool:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise InstallError(f"Managed placeholder must be a regular file: {path}")
    if path.is_file() and path.stat().st_size == 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return True


def merge_unique(first: Any, second: Any) -> list[Any]:
    result: list[Any] = []
    for value in [
        *(first if isinstance(first, list) else []),
        *(second if isinstance(second, list) else []),
    ]:
        if value not in result:
            result.append(value)
    return result


def merged_settings(
    source: JsonObject, target: JsonObject, canonical_hooks: JsonObject
) -> JsonObject:
    result = deepcopy(target) if target else {}
    existing_env = result.get("env") if isinstance(result.get("env"), dict) else {}
    existing_env = {
        key: value
        for key, value in existing_env.items()
        if key not in DEPRECATED_ENV_KEYS
    }
    result["env"] = {**source.get("env", {}), **existing_env}

    source_permissions = (
        source.get("permissions", {})
        if isinstance(source.get("permissions"), dict)
        else {}
    )
    target_permissions = (
        result.get("permissions", {})
        if isinstance(result.get("permissions"), dict)
        else {}
    )
    old_invalid = {"WebFetch(*)", "WebSearch(*)"}
    target_allow = [
        value
        for value in target_permissions.get("allow", [])
        if value not in old_invalid
    ]
    target_deny = [
        value
        for value in target_permissions.get("deny", [])
        if value not in old_invalid
    ]
    result["permissions"] = {
        "allow": merge_unique(source_permissions.get("allow"), target_allow),
        "deny": merge_unique(source_permissions.get("deny"), target_deny),
    }
    result["hooks"] = merge_hook_maps(canonical_hooks, result.get("hooks"))
    for key, value in source.items():
        if key not in {"env", "permissions", "hooks"}:
            result.setdefault(key, deepcopy(value))
    return result


def prune_obsolete_managed_hooks(directory: Path, keep: set[str]) -> int:
    """Remove only known package-owned legacy hooks; preserve custom files."""
    removed = 0
    if not directory.is_dir():
        return removed
    for name in sorted(MANAGED_HOOK_NAMES.difference(keep)):
        path = directory / name
        if path.is_file() or path.is_symlink():
            path.unlink()
            removed += 1
    return removed


def make_executable(directory: Path) -> int:
    changed = 0
    for path in directory.glob("*") if directory.is_dir() else ():
        if not path.is_file() or path.suffix not in {".py", ".sh"}:
            continue
        mode = path.stat().st_mode
        wanted = mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if mode != wanted:
            path.chmod(wanted)
            changed += 1
    return changed


def install(source: Path, project: Path, *, strict: bool) -> tuple[int, int]:
    errors, warnings = validate_tree(source, strict=True)
    if errors:
        raise InstallError(
            "Source package validation failed:\n- " + "\n- ".join(errors)
        )
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    target = project / ".claude"
    target.mkdir(parents=True, exist_ok=True)
    source_settings = load_json(source / "settings.json")
    canonical_hooks = load_json(source / "settings_hooks_template.json")["hooks"]
    target_settings_path = target / "settings.json"
    target_settings = (
        load_json(target_settings_path) if target_settings_path.exists() else {}
    )
    settings = merged_settings(source_settings, target_settings, canonical_hooks)
    setting_errors = validate_settings(
        settings, str(target_settings_path), require_hooks=True
    )
    if setting_errors:
        raise InstallError(
            "Refusing to write invalid settings:\n- " + "\n- ".join(setting_errors)
        )

    copied = 0
    copied += copy_tree(source / "hooks", target / "hooks")
    active_hook_files = referenced_hooks(canonical_hooks) | {"hook_common.py"}
    copied += prune_obsolete_managed_hooks(target / "hooks", active_hook_files)
    copied += copy_tree(source / "tests", target / "tests")
    for name in COPY_FILES:
        copied += int(copy_file(source / name, target / name))
    for relative in PLACEHOLDERS:
        copied += int(ensure_empty(target / relative))
    before = (
        target_settings_path.read_bytes() if target_settings_path.exists() else None
    )
    rendered = (json.dumps(settings, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    if before != rendered:
        write_json(target_settings_path, settings)
        copied += 1
    executable = make_executable(target / "hooks")

    target_errors, target_warnings = validate_tree(target, strict=strict)
    for warning in target_warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if target_errors:
        raise InstallError(
            "Installed package validation failed:\n- " + "\n- ".join(target_errors)
        )
    return copied, executable


def source_dir(script: Path) -> Path:
    return (
        script.parent if script.parent.name == ".claude" else script.parent / ".claude"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    source = source_dir(Path(__file__).resolve())
    try:
        if args.check:
            errors, warnings = validate_tree(source, strict=args.strict)
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
            for error in errors:
                print(f"Error: {error}", file=sys.stderr)
            if errors:
                return 1
            print("Configuration structure is valid and internally consistent.")
            return 0
        raw = (
            Path(args.project_root).expanduser().resolve()
            if args.project_root
            else source.parent
        )
        project = raw.parent if raw.name == ".claude" else raw
        copied, executable = install(source, project, strict=args.strict)
        print(f"Synchronized Claude configuration: {project / '.claude/settings.json'}")
        print(
            f"Copied or updated {copied} file(s); changed executable bits "
            f"on {executable} hook(s)."
        )
        return 0
    except (InstallError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
