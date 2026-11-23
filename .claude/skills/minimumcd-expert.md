# Minimum CD Expert

This skill implements the principles of Minimum CD to ensure a high-velocity, high-quality delivery flow.

## 🎯 Core Mandate
Ensure that all changes are delivered in a standard, safe, and frequent manner, avoiding over-engineered CI/CD pipelines while maintaining strict quality gates.

## 🛠️ Key Competencies
- **Trunk-Based Development**:
    - Enforcing short-lived branches.
    - Ensuring a high-frequency merge cadence (e.g., daily) to prevent integration drift.
    - Breaking changes into small, atomic commits.
- **Immutable Artifact Pipeline**:
    - Ensuring that once an artifact (e.g., model checkpoint, build) is created, it is never modified in-place—only replaced.
    - Standardizing the path from `commit` $\to$ `test` $\to$ `audit` $\to$ `deploy`.
- **Safe Delivery Gates**:
    - Implementing the "Red $\rightarrow$ Green $\rightarrow$ Refactor" cycle.
    - Defining "Done" as meeting both quantitative metrics and qualitative sign-off.
- **Flow Analysis**:
    - Identifying bottlenecks in the delivery pipeline.
    - Applying YAGNI to the CI process: if it doesn't improve safety or speed, remove it.

## 📋 Delivery Rules
- **Standard Way**: Every change follows the same pipeline; no "special" deployments.
- **Short-Lived**: Branches that exceed a specific age (e.g., 48 hours) are considered technical debt.
- **Daily Integration**: Frequent integration into the main branch.
- **Immutable**: Validated artifacts are treated as read-only.
