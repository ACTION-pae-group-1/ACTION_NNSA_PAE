# Error Handling & Resilience Expert

**Fail fast on bugs. Degrade gracefully on expected failures. Never silently swallow.**

## Classification

| Category | Examples | Strategy |
|----------|----------|----------|
| **Bug** | `None` access, index OOB, type mismatch, logic error | **Fail fast** — crash loudly, provide stack trace, alert |
| **Expected** | File not found, invalid upload, config load fail | **Handle explicitly** — return typed error, log, continue |
| **Transient** | Network blip, DB lock, resource spike | **Retry with backoff** — max 3x, exponential, jitter |
| **Resource** | Disk full, OOM, quota exceeded | **Graceful degrade** — shed load, return 503, alert |

## Patterns

### Bugs $\rightarrow$ Exceptions (Never Catch All)
Avoid wrapping large blocks of code in generic `try...except` blocks. Let bugs crash the system so they can be identified and fixed.

### Expected Failures $\rightarrow$ Result Types
Use Result types or specialized error objects for expected failures to force the caller to handle the error case.

### Transient $\rightarrow$ Retry Decorator
Implement retries with exponential backoff and jitter for operations that may fail due to temporary external issues.

### Resource $\rightarrow$ Circuit Breaker
Implement circuit breakers or semaphores to shed load and prevent total system collapse when resources (e.g., GPU, Memory) are exhausted.

## HTTP Error Mapping
Maintain a consistent mapping of internal exceptions to HTTP status codes (e.g., 422 for validation, 404 for missing resources, 503 for unavailable services).

## Logging on Error
- **Bug**: Use `logger.exception()` for full tracebacks.
- **Expected**: Use `logger.warning()` with structured data, no traceback.
- **Transient**: Use `logger.info()` for retry attempts.
- **Resource**: Use `logger.error()` for alert-worthy resource issues.

## Testing Errors
- **Unit Tests**: Verify every error path.
- **Integration Tests**: Verify correct HTTP response codes.
- **Chaos Testing**: Simulate resource failure (e.g., killing a process) to verify graceful degradation.
