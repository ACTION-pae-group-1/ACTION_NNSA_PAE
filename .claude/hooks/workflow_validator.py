"""
Workflow validator with semantic analysis.

Validates workflows beyond AST parsing:
1. Agent type whitelist checking
2. Phase structure validation (required fields)
3. Meta structure validation (required fields)
4. Promise chain error handling
5. Circular dependency detection

This prevents invalid workflows from executing.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Base class for validation errors."""

    pass


class ValidationWarning(Exception):
    """Base class for validation warnings."""

    pass


@dataclass
class ValidatorConfig:
    """Configuration for workflow validator."""

    allowed_agent_types: List[str]
    required_phase_fields: List[str]
    required_meta_fields: List[str]

    @classmethod
    def get_default(cls) -> "ValidatorConfig":
        """
        Get default validator configuration.

        Default whitelist of allowed agent types based on available agents.
        """
        return cls(
            allowed_agent_types=[
                "tdd-enforcer",
                "code-reviewer",
                "interrogator",
                "slice-orchestrator",
                "mcp-builder",
                "mcp-eval",
                "mcp-workflow",
                "feature-builder",
                "minimumcd-agent",
                "ontologist",
                "plan",
                "explore",
                "general-purpose",
                "claude-code-guide",
                "data-governance-advisor",
                "token-minimizer",
                "git-safety-constraint-agent",
            ],
            required_phase_fields=[
                "title",
                "prompt",
                "agentType",
            ],
            required_meta_fields=[
                "name",
                "description",
                "phases",
            ],
        )

    @classmethod
    def from_file(cls, config_file: Path) -> "ValidatorConfig":
        """
        Load validator configuration from JSON file.

        Args:
            config_file: Path to VALIDATOR_CONFIG.json

        Returns:
            ValidatorConfig instance
        """
        try:
            content = config_file.read_text(encoding="utf-8")
            data = json.loads(content)

            return cls(
                allowed_agent_types=data.get(
                    "allowed_agent_types",
                    cls.get_default().allowed_agent_types,
                ),
                required_phase_fields=data.get(
                    "required_phase_fields",
                    cls.get_default().required_phase_fields,
                ),
                required_meta_fields=data.get(
                    "required_meta_fields",
                    cls.get_default().required_meta_fields,
                ),
            )
        except (json.JSONDecodeError, IOError) as e:
            raise ValidationError(f"Failed to load config: {e}") from e


class WorkflowValidator:
    """
    Workflow validator with semantic analysis.

    Validates:
    - Workflow structure (meta, phases, fields)
    - Agent type whitelist
    - Promise chain error handling
    - Required fields presence
    """

    def __init__(self, config: Optional[ValidatorConfig] = None):
        """
        Initialize validator with configuration.

        Args:
            config: ValidatorConfig (uses default if None)
        """
        self.config = config or ValidatorConfig.get_default()

    def validate_semantic(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Perform semantic validation of workflow.

        Args:
            workflow: Parsed workflow object

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate meta structure
        errors.extend(self._validate_meta_structure(workflow))

        # Validate phases structure and contents
        if "meta" in workflow and "phases" in workflow["meta"]:
            errors.extend(self._validate_phases_structure(workflow["meta"]["phases"]))

        return errors

    def _validate_meta_structure(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Validate meta object structure.

        Args:
            workflow: Workflow object

        Returns:
            List of error messages
        """
        errors = []

        if "meta" not in workflow:
            errors.append("Workflow must have 'meta' object")
            return errors

        meta = workflow["meta"]

        # Check required meta fields
        for field in self.config.required_meta_fields:
            if field not in meta:
                errors.append(f"Meta missing required field: '{field}'")
            elif not meta[field]:
                errors.append(f"Meta field '{field}' cannot be empty")

        return errors

    def _validate_phases_structure(self, phases: List[Dict[str, Any]]) -> List[str]:
        """
        Validate phases structure and contents.

        Args:
            phases: List of phase objects

        Returns:
            List of error messages
        """
        errors = []

        if not isinstance(phases, list):
            errors.append("Phases must be an array")
            return errors

        if len(phases) == 0:
            errors.append("Phases array cannot be empty")
            return errors

        # Validate each phase
        for idx, phase in enumerate(phases):
            phase_errors = self._validate_phase(phase, idx)
            errors.extend(phase_errors)

        return errors

    def _validate_phase(self, phase: Dict[str, Any], index: int) -> List[str]:
        """
        Validate a single phase object.

        Args:
            phase: Phase object
            index: Phase index (for error messages)

        Returns:
            List of error messages
        """
        errors = []

        if not isinstance(phase, dict):
            errors.append(f"Phase {index} must be an object")
            return errors

        # Check required phase fields
        for field in self.config.required_phase_fields:
            if field not in phase:
                errors.append(f"Phase {index} missing required field: '{field}'")
            elif not phase[field]:
                errors.append(f"Phase {index} field '{field}' cannot be empty")

        # Validate agent type if present
        if "agentType" in phase:
            agent_type = phase["agentType"]
            if agent_type not in self.config.allowed_agent_types:
                errors.append(
                    f"Phase {index} has unknown agent type: '{agent_type}'. "
                    f"Allowed types: {', '.join(self.config.allowed_agent_types)}"
                )

        return errors

    def validate_promise_chains(self, workflow_code: str) -> List[str]:
        """
        Validate Promise chains for error handling.

        Checks for:
        - Unhandled promise rejections
        - Missing .catch() handlers
        - Missing try/catch blocks

        Args:
            workflow_code: JavaScript/TypeScript workflow code

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for unhandled await without try/catch
        await_pattern = r"await\s+(?![\s\(]*try)"
        await_matches = re.findall(await_pattern, workflow_code)

        if await_matches:
            # Check if there's a surrounding try block
            if "try {" not in workflow_code:
                warnings.append(
                    "Workflow has await expressions without try/catch error handling"
                )

        # Check for unhandled executor submissions without .catch()
        executor_pattern = r"executor\.submit\([^)]+\)(?!\s*\.catch)"
        executor_matches = re.findall(executor_pattern, workflow_code)

        if executor_matches:
            warnings.append(
                "Workflow has executor.submit() without .catch() error handler"
            )

        # Check for promise chains without .catch()
        promise_pattern = r"\.then\([^)]+\)(?!\s*\.catch)"
        promise_matches = re.findall(promise_pattern, workflow_code)

        if promise_matches:
            warnings.append(
                "Workflow has .then() chains without .catch() error handlers"
            )

        return warnings

    def validate_circular_dependencies(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Detect circular dependencies between phases.

        Args:
            workflow: Workflow object

        Returns:
            List of error messages
        """
        errors = []

        # This is a simplified check - a full implementation would parse
        # phase inputs/outputs and build a dependency graph
        # For now, we just check if phases reference each other in problematic ways

        if "meta" not in workflow or "phases" not in workflow["meta"]:
            return errors

        phases = workflow["meta"]["phases"]

        # Check for self-references
        for idx, phase in enumerate(phases):
            phase_name = phase.get("title", f"Phase {idx}")
            prompt = phase.get("prompt", "")

            # Simple heuristic: if phase references its own name in output
            if phase_name.lower() in prompt.lower():
                errors.append(
                    f"Phase '{phase_name}' may have circular reference to itself"
                )

        return errors


def validate_workflow_file(
    workflow_file: Path,
    config: Optional[ValidatorConfig] = None,
) -> tuple[List[str], List[str]]:
    """
    Validate a complete workflow file.

    Args:
        workflow_file: Path to workflow JavaScript file
        config: Optional ValidatorConfig

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    validator = WorkflowValidator(config or ValidatorConfig.get_default())

    try:
        # Read workflow file
        content = workflow_file.read_text(encoding="utf-8")

        # Parse meta object from exports
        # This is a simplified extraction - a full implementation would use
        # a proper JavaScript parser
        meta_match = re.search(
            r"export\s+const\s+meta\s*=\s*(\{[^}]+\})", content, re.DOTALL
        )

        if meta_match:
            try:
                # Convert JavaScript object to JSON
                meta_str = meta_match.group(1)
                # Very simplified conversion - proper implementation would need
                # a JavaScript parser
                workflow = {"meta": json.loads(meta_str)}

                errors.extend(validator.validate_semantic(workflow))
            except json.JSONDecodeError:
                errors.append("Failed to parse workflow meta object")

        # Validate promise chains
        warnings.extend(validator.validate_promise_chains(content))

    except IOError as e:
        errors.append(f"Failed to read workflow file: {e}")

    return errors, warnings


# Create default validator instance
_default_validator = WorkflowValidator()


def get_default_validator() -> WorkflowValidator:
    """Get default workflow validator instance."""
    return _default_validator
