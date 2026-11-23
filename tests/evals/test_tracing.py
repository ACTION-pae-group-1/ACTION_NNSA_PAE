"""Tracing stays optional and never exports payloads."""

from eval.bls import tracing


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BLS_EVAL_PHOENIX_ENABLED", raising=False)
    assert not tracing.enabled()
    with tracing.span(
        "noop",
        secret="not-exported",  # pragma: allowlist secret
    ) as current:
        assert current is None


def test_opt_in_flag(monkeypatch):
    monkeypatch.setenv("BLS_EVAL_PHOENIX_ENABLED", "true")
    assert tracing.enabled()
    monkeypatch.setenv("BLS_EVAL_PHOENIX_ENABLED", "false")
    assert not tracing.enabled()


def test_trace_id_none_without_span():
    assert tracing.trace_id(None) is None
