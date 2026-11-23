# Config Management Expert

**Single source of truth. Explicit precedence. No magic.**

## 🚀 Scope
- **Standardization**: Defining and enforcing the directory structure for artifacts and checkpoints.
- **Dependency Management**: Managing version pinning and auditing new dependencies.
- **Type-Safety**: Implementing type-safe configuration for system hyper-parameters.

## Precedence Order (Highest Wins)
1. **CLI arguments** — explicit overrides at runtime.
2. **Environment variables** — prefixed for the application (e.g., `APP_`).
3. **Config files** — git-tracked, non-secret YAML/JSON files.
4. **Secrets files** — git-ignored `.env` files (API keys, local paths).
5. **Code defaults** — Sensible defaults defined in code dataclasses.

## Structure
- `config.yaml`: Tracked, version-controlled base configuration.
- `.env`: Git-ignored secrets and local overrides.
- `app/config.py`: Pydantic Settings or similar for type-safe loading.
- `config/<module>/`: Module-specific configurations.

## Rules

### No Implicit Globals
Config should be accessed via dependency injection rather than module-level imports with side effects.

### Type-Safe
Use validation libraries (like Pydantic, pyshacl, etc.) to ensure configuration is valid on load. Fail fast on bad config.

### Environment-Specific Overlays
Use a layered approach: `base` $\to$ `env-specific` $\to$ `.env` $\to$ `CLI`.

### Secrets Handling
- `.env` is used only for secrets, API keys, and local-only paths.
- `.env.example` is committed with dummy values for onboarding.

## Model/Component Configuration
Each major component or model variant should have its own configuration file, loaded by a unique identifier, containing all relevant architecture and inference settings.
