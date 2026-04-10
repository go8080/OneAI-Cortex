## ADR-010: Semantic Versioning for Framework Adapters

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

Framework SDKs (DeepAgents, future CrewAI, etc.) evolve independently of the OneAI-Cortex platform. When a framework SDK updates, the corresponding adapter may break silently — functions change, parameters shift, return types differ. Without version tracking, users won't know which adapter works with which SDK version, and the platform can't prevent incompatible combinations.

### Decision

Every framework adapter declares three version properties:

1. **`adapter_version`** — The adapter's own semantic version (e.g., `1.0.0`). Follows semver: breaking changes = major bump, new features = minor, fixes = patch.

2. **`sdk_compatibility`** — PEP 440 version specifier for the required SDK version range (e.g., `>=0.5.0,<1.0.0`). Uses Python's `packaging` library for comparison.

3. **`sdk_version_installed`** — The actually installed SDK version at runtime (read from `importlib.metadata`).

**Startup behavior:**
- Adapter registry checks each adapter's `sdk_compatibility` against `sdk_version_installed`
- If incompatible: adapter is **not registered**, warning logged, `GET /frameworks` shows `compatible: false`
- If compatible: adapter registered normally

**Agent config stores:**
- `framework: "deepagents"` — which adapter
- `framework_adapter_version: "1.0.0"` — which adapter version created this config (for reproducibility)

### Consequences

**Positive:**
- Silent SDK breakage becomes a loud, clear incompatibility warning at startup
- Agent configs are reproducible — version of adapter that created them is recorded
- Users can see compatibility status via `GET /frameworks`
- Forces adapter authors to think about compatibility ranges

**Negative:**
- Adapter authors must update `sdk_compatibility` when new SDK versions are tested
- Version metadata adds a small amount of complexity to the adapter protocol

**Neutral:**
- Versioning is metadata-only — it doesn't block agent execution if a user explicitly wants to try an untested version (warning, not error)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| No versioning (just pin SDK in requirements.txt) | Silent breakage when users install different SDK versions; no visibility |
| Git tag-based versioning only | Not queryable at runtime; doesn't help with compatibility checking |
| Hard block on incompatible versions | Too strict for open-source — users may want to test bleeding-edge SDK versions |

### Validation

- `GET /frameworks` returns accurate `compatible: true/false` for each adapter
- Installing an out-of-range SDK version results in adapter not registering + clear log warning
- Agent config JSONB includes `framework_adapter_version` field
