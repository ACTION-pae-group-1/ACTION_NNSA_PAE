# Observability & Monitoring Expert

**All critical operations must be explicitly observable in real-time.**

## Core Mandate
Ensure that every major process (training, inference, data processing) emits structured, machine-parseable logs and metrics to avoid "black box" execution.

## Process Observability
Every long-running process must emit:
- **Identity**: Which entity/model/trigger is being processed.
- **Progress**: Current step, epoch, or batch number.
- **Performance**: Primary loss, accuracy, or domain-specific metrics.
- **Resources**: Learning rate, time elapsed, and ETA.
- **Format**: JSONL to stdout (for machines) and human-readable summaries to stderr.

## Pipeline Observability
Track the health and performance of each pipeline stage:
- **Latency**: Time spent in each stage (ms).
- **Throughput**: Items processed per second.
- **Quality**: Domain-specific metrics (e.g., attenuation, distance) per stage.
- **Status**: Success/Failure rates per stage.

## Logging Standards
- **Levels**: `INFO` for progress, `DEBUG` for verbose, `WARNING` for recoverable issues, `ERROR` for failures.
- **Structured**: Use JSON formatting for all logs.
- **Context**: Bind request-specific IDs (e.g., `job_id`) to all log lines in a session.
- **Privacy**: Never log PII or raw sensitive data.

## Metrics Collection
Implement Prometheus-compatible counters, gauges, and histograms for:
- Total jobs processed by status.
- Per-stage latency.
- Resource utilization (CPU/GPU/Disk).
- Model inference time.

## Health Checks
- `/health` — Liveness check (is the process running?).
- `/ready` — Readiness check (are dependencies/models loaded?).
- `/metrics` — Metrics scrape endpoint.

## Alerting Thresholds
Define clear thresholds for warnings and critical alerts (e.g., latency spikes, resource exhaustion, or metric degradation).
