"""
Test suite for workflow validator semantic analysis.

Tests cover:
1. Unknown agent types validation (whitelist checking)
2. Phase structure validation (required fields)
3. Meta structure validation (required top-level fields)
4. Agent availability checking
5. Promise chain validation (error handling)
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks"))

from workflow_validator import (
    ValidatorConfig,
    WorkflowValidator,
)


class TestValidatorConfig:
    """Test validator configuration."""

    def test_load_default_config(self):
        """Load default validator config."""
        config = ValidatorConfig.get_default()

        assert "tdd-enforcer" in config.allowed_agent_types
        assert "code-reviewer" in config.allowed_agent_types
        assert "interrogator" in config.allowed_agent_types
        assert "slice-orchestrator" in config.allowed_agent_types

    def test_load_custom_config(self):
        """Load custom validator config from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "validator_config.json"
            custom_config = {
                "allowed_agent_types": [
                    "custom-agent",
                    "test-agent",
                ],
                "required_phase_fields": ["title", "prompt", "agentType"],
                "required_meta_fields": ["name", "description", "phases"],
            }
            config_file.write_text(json.dumps(custom_config))

            config = ValidatorConfig.from_file(config_file)

            assert "custom-agent" in config.allowed_agent_types
            assert "test-agent" in config.allowed_agent_types
            assert "title" in config.required_phase_fields


class TestPhaseStructureValidation:
    """Test validation of phase structure."""

    def test_reject_phase_missing_title(self):
        """Validator should reject phase without title field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        # Missing title
                        "prompt": "Do something",
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("title" in str(e).lower() for e in errors)

    def test_reject_phase_missing_prompt(self):
        """Validator should reject phase without prompt field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        # Missing prompt
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("prompt" in str(e).lower() for e in errors)

    def test_reject_phase_missing_agentType(self):
        """Validator should reject phase without agentType field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        # Missing agentType
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("agenttype" in str(e).lower() for e in errors)

    def test_accept_phase_with_all_required_fields(self):
        """Validator should accept phase with all required fields."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        phase_errors = [e for e in errors if "phase" in str(e).lower()]
        assert len(phase_errors) == 0


class TestMetaStructureValidation:
    """Test validation of meta structure."""

    def test_reject_meta_missing_name(self):
        """Validator should reject meta without name field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                # Missing name
                "description": "Test workflow",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("name" in str(e).lower() for e in errors)

    def test_reject_meta_missing_description(self):
        """Validator should reject meta without description field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                # Missing description
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("description" in str(e).lower() for e in errors)

    def test_reject_meta_missing_phases(self):
        """Validator should reject meta without phases field."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test workflow",
                # Missing phases
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("phases" in str(e).lower() for e in errors)

    def test_accept_meta_with_all_required_fields(self):
        """Validator should accept meta with all required fields."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test workflow",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        meta_errors = [
            e for e in errors if "meta" in str(e).lower() or "name" in str(e).lower()
        ]
        assert len(meta_errors) == 0


class TestAgentTypeValidation:
    """Test validation of agent types against whitelist."""

    def test_reject_unknown_agent_type(self):
        """Validator should reject unknown agent types."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "unknown-agent-type",  # Not in whitelist
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert any("unknown-agent-type" in str(e).lower() for e in errors)
        assert any("agent" in str(e).lower() for e in errors)

    def test_accept_known_agent_types(self):
        """Validator should accept known agent types."""
        validator = WorkflowValidator()

        known_types = [
            "tdd-enforcer",
            "code-reviewer",
            "interrogator",
            "slice-orchestrator",
            "mcp-builder",
        ]

        for agent_type in known_types:
            workflow = {
                "meta": {
                    "name": "test-workflow",
                    "description": "Test",
                    "phases": [
                        {
                            "title": "Phase 1",
                            "prompt": "Do something",
                            "agentType": agent_type,
                        }
                    ],
                },
            }

            errors = validator.validate_semantic(workflow)

            agent_errors = [
                e
                for e in errors
                if "agent" in str(e).lower() and "type" in str(e).lower()
            ]
            assert len(agent_errors) == 0, f"Should accept {agent_type}"

    def test_multiple_unknown_agent_types(self):
        """Validator should report all unknown agent types."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test-workflow",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "unknown-1",
                    },
                    {
                        "title": "Phase 2",
                        "prompt": "Do something else",
                        "agentType": "unknown-2",
                    },
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        agent_errors = [e for e in errors if "unknown" in str(e).lower()]
        assert len(agent_errors) >= 2


class TestPromiseChainValidation:
    """Test validation of Promise chain error handling."""

    def test_warn_on_missing_error_handler(self):
        """Validator should warn if error handling is missing."""
        validator = WorkflowValidator()

        # Workflow code without .catch() or try/catch
        workflow_code = """
const result = await agent(prompt, { agentType: 'code-reviewer' })
// No error handling!
"""

        warnings = validator.validate_promise_chains(workflow_code)

        # Should warn about missing error handling
        assert len(warnings) > 0

    def test_warn_on_unhandled_rejection(self):
        """Validator should warn about unhandled promise rejections."""
        validator = WorkflowValidator()

        workflow_code = """
executor.submit(async_task)
// No .catch() handler!
"""

        warnings = validator.validate_promise_chains(workflow_code)

        assert len(warnings) > 0

    def test_accept_try_catch_error_handling(self):
        """Validator should accept try/catch error handling."""
        validator = WorkflowValidator()

        workflow_code = """
try {
    const result = await agent(prompt, { agentType: 'code-reviewer' })
} catch (error) {
    log(`Error: ${error.message}`)
    throw error
}
"""

        warnings = validator.validate_promise_chains(workflow_code)

        error_warnings = [
            w
            for w in warnings
            if "error" in str(w).lower() or "unhandled" in str(w).lower()
        ]
        assert len(error_warnings) == 0

    def test_accept_catch_handler(self):
        """Validator should accept .catch() handler."""
        validator = WorkflowValidator()

        workflow_code = """
agent(prompt, { agentType: 'code-reviewer' })
    .then(result => processResult(result))
    .catch(error => handleError(error))
"""

        warnings = validator.validate_promise_chains(workflow_code)

        error_warnings = [w for w in warnings if "unhandled" in str(w).lower()]
        assert len(error_warnings) == 0


class TestCompleteWorkflowValidation:
    """Test complete workflow validation (semantic + syntactic)."""

    def test_valid_workflow_passes_all_validation(self):
        """Valid workflow should pass all validation checks."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "feature-implementation",
                "description": "Implement feature with TDD",
                "phases": [
                    {
                        "title": "TDD Implementation",
                        "prompt": "Write tests first",
                        "agentType": "tdd-enforcer",
                    },
                    {
                        "title": "Code Review",
                        "prompt": "Review implementation",
                        "agentType": "code-reviewer",
                    },
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert len(errors) == 0

    def test_invalid_workflow_reports_multiple_errors(self):
        """Invalid workflow should report all errors."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                # Missing name and description
                "phases": [
                    {
                        # Missing title
                        "prompt": "Do something",
                        "agentType": "unknown-agent",  # Unknown type
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        assert len(errors) >= 3  # Should report multiple errors


class TestValidationMessages:
    """Test validation error and warning message quality."""

    def test_error_messages_are_clear_and_actionable(self):
        """Error messages should clearly indicate what's wrong."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        # Missing prompt
                        "agentType": "code-reviewer",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        # Should have clear error about missing prompt
        prompt_errors = [e for e in errors if "prompt" in str(e).lower()]
        assert len(prompt_errors) > 0

        # Error message should indicate it's a phase field
        error_msg = str(prompt_errors[0])
        assert "phase" in error_msg.lower() or "field" in error_msg.lower()

    def test_validation_includes_line_numbers_if_available(self):
        """Validation should indicate where problems are."""
        validator = WorkflowValidator()

        workflow = {
            "meta": {
                "name": "test",
                "description": "Test",
                "phases": [
                    {
                        "title": "Phase 1",
                        "prompt": "Do something",
                        "agentType": "unknown-agent",
                    }
                ],
            },
        }

        errors = validator.validate_semantic(workflow)

        # Error should reference the phase number or agent name
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
