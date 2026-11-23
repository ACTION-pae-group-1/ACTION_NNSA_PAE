# Backend Engineering Expert

This skill provides expertise in backend development, API design, and core processing pipelines.

## 🎯 Role & Scope
- **Primary Owner**: Core system logic, data processing, and server-side architecture.
- **Scope**:
    - Implementing high-performance processing pipelines.
    - Hardware optimization (e.g., GPU acceleration, batch size tuning).
    - Path portability and dependency auditing.
    - Coordinating sequential data flow between pipeline stages.

## Architecture Pattern
- **API**: <e.g., FastAPI / Express / Go>
- **Pipeline**: `<Stage 1>` $\to$ `<Stage 2>` $\to$ `<Stage 3>` $\to$ `<Stage 4>`.
- **Core Logic**: Implementation of specialized processing modes (e.g., heuristic, statistical, neural).

## TDD Backend Workflow
All backend changes must be verified using the following TDD cycle:
1. **Test First**: Write a unit test or property test that defines the expected output for a specific input.
2. **Fail**: Run the test to confirm it fails.
3. **Implement**: Write the minimum amount of code required to pass the test.
4. **Verify**: Run the full test suite to ensure no regressions in the pipeline.

## Critical Engineering Constraints
- **Performance**: Processing should be optimized for the target latency requirements.
- **Precision**: The goal is to perform targeted operations without introducing artifacts or altering non-targeted signal components.
- **Consistency**: Use standardized libraries for data transformation to ensure consistency across the pipeline.
