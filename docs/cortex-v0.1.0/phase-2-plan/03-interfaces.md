# Phase 2 — Interface Design

**Date:** 2026-04-10
**Project:** OneAI-Cortex

---

## 1. Framework Adapter Protocol (Core Abstraction)

This is the most critical interface in the system — it decouples the platform from any specific agent framework.

```python
class FrameworkAdapter(Protocol):
    """Interface that every framework adapter must implement.
    Designed around USER-FACING concepts, not framework internals.
    Every adapter is versioned (semver) and declares SDK compatibility."""

    @property
    def framework_name(self) -> str:
        """e.g., 'deepagents', 'crewai', 'autogen'"""
        ...

    @property
    def adapter_version(self) -> str:
        """Semantic version of this adapter, e.g., '1.0.0'"""
        ...

    @property
    def sdk_compatibility(self) -> str:
        """SDK version range, e.g., '>=0.5.0,<1.0.0' (PEP 440 specifier)"""
        ...

    @property
    def supported_models(self) -> list[ModelSpec]:
        """Models this framework supports."""
        ...

    async def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate agent config before saving. Returns errors if invalid."""
        ...

    async def create_runtime(self, config: AgentConfig, user_api_keys: dict[str, str]) -> AgentRuntime:
        """Build a runnable agent from config. Does NOT execute it."""
        ...

    async def execute(
        self,
        runtime: AgentRuntime,
        messages: list[Message],
        session_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Execute agent with messages, yielding streaming events."""
        ...

    async def generate_sdk_package(self, config: AgentConfig) -> SDKPackage:
        """Generate a standalone SDK package for this agent."""
        ...

    def get_available_tools(self) -> list[ToolSpec]:
        """Tools this framework provides out of the box."""
        ...

    async def attach_mcp_servers(self, runtime: AgentRuntime, mcp_configs: list[MCPServerConfig]) -> None:
        """Attach MCP servers to an agent runtime before execution."""
        ...

    async def resume_after_interrupt(
        self,
        runtime: AgentRuntime,
        session_id: str,
        approved: bool,
        modified_args: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Resume execution after HITL interrupt. If approved=False, tool call is skipped."""
        ...
```

### Supporting Types

> **Design principle:** AgentConfig maps 1:1 to `create_deep_agent()` parameters.
> Framework-agnostic names are used, but the mapping is explicit and complete.
> See ADR-012 for the full parameter mapping rationale.

```python
@dataclass
class AgentConfig:
    """Framework-agnostic agent configuration.
    Maps to all 17 create_deep_agent() parameters."""

    # === Identity ===
    name: str

    # === Model (maps to: model) ===
    model: str                              # "provider:model" format, e.g., "anthropic:claude-sonnet-4-6"
                                            # Resolved via LangChain's init_chat_model()
                                            # Default: "anthropic:claude-sonnet-4-6"

    # === Prompting (maps to: system_prompt) ===
    system_prompt: str

    # === Tools & MCP (maps to: tools + MCP attachment) ===
    tools: list[str]                        # tool IDs from registry
    mcp_servers: list[str]                  # MCP server IDs assigned to this agent

    # === Subagents (maps to: subagents) ===
    subagents: list[SyncSubAgentConfig | AsyncSubAgentConfig] = field(default_factory=list)

    # === Middleware (maps to: middleware — toggles for the 10-middleware stack) ===
    middleware: MiddlewareConfig = field(default_factory=MiddlewareConfig)

    # === Output (maps to: response_format) ===
    response_format: dict[str, Any] | None = None   # JSON schema for structured output, or None for freeform

    # === Execution control ===
    temperature: float = 0.7
    max_tokens: int = 4096
    recursion_limit: int = 100              # max graph steps before forced stop

    # === Backend (maps to: backend) ===
    backend: BackendConfig = field(default_factory=BackendConfig)

    # === Human-in-the-loop (maps to: interrupt_on) ===
    interrupt_on: dict[str, bool | InterruptConfig] | None = None
    # e.g., {"edit_file": True, "execute": {"message": "Approve shell command?"}}

    # === Checkpointing (maps to: checkpointer) ===
    checkpointing_enabled: bool = True      # use AsyncSqliteSaver for session persistence

    # === Debug (maps to: debug) ===
    debug: bool = False

    # === Escape hatch ===
    framework_specific: dict[str, Any] = field(default_factory=dict)

    # === Encrypted secrets (NOT a create_deep_agent param — Cortex-only) ===
    user_api_keys: dict[str, str] = field(default_factory=dict)  # encrypted at rest


@dataclass
class SyncSubAgentConfig:
    """Sync subagent — runs in-process, blocks parent until done.
    Maps to DeepAgents SubAgent TypedDict."""
    name: str
    description: str
    system_prompt: str
    model: str | None = None                # None = inherit parent model
    tools: list[str] | None = None          # None = inherit parent tools
    interrupt_on: dict[str, bool | InterruptConfig] | None = None  # None = inherit parent

@dataclass
class AsyncSubAgentConfig:
    """Async subagent — runs on remote Agent Protocol server, non-blocking.
    Maps to DeepAgents AsyncSubAgent TypedDict."""
    name: str
    description: str
    graph_id: str                           # graph name on remote server
    url: str | None = None                  # remote server URL
    headers: dict[str, str] = field(default_factory=dict)  # auth headers (encrypted at rest)


@dataclass
class MiddlewareConfig:
    """Configuration for the DeepAgents middleware stack.
    Each flag enables/disables a middleware in the ordered pipeline."""
    todo_list: bool = True
    filesystem: bool = True
    subagent: bool = True                   # auto-enabled if subagents configured
    summarization: bool = True
    patch_tool_calls: bool = True
    async_subagent: bool = True             # auto-enabled if async subagents configured
    prompt_caching: bool = True
    human_in_the_loop: bool = False         # auto-enabled if interrupt_on is set
    # NOTE: Skills and Memory middleware are deferred to v0.2


@dataclass
class BackendConfig:
    """Backend selection for file operations within agent execution."""
    type: Literal["state", "filesystem"] = "state"
    # StateBackend: ephemeral, in-memory (default)
    # FilesystemBackend: persistent, scoped to root_dir
    root_dir: str | None = None             # only for filesystem backend
    max_file_size_mb: int = 10              # only for filesystem backend


@dataclass
class InterruptConfig:
    """Detailed interrupt configuration for a specific tool."""
    message: str = "Approval required"      # shown to user via SSE


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""
    name: str
    transport: Literal["stdio", "sse", "http"]
    url: str | None = None                  # for sse/http transports
    command: str | None = None              # for stdio transport
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)  # includes API keys
    auth_header: str | None = None          # for http transport auth

@dataclass
class MCPTestResult:
    """Result of testing MCP server connectivity."""
    reachable: bool
    tools_discovered: list[ToolSpec]
    error: str | None = None
    latency_ms: int = 0

@dataclass
class AdapterVersionInfo:
    """Version metadata for a framework adapter."""
    adapter_name: str                       # e.g., "deepagents"
    adapter_version: str                    # semver: "1.0.0"
    sdk_name: str                           # e.g., "deepagents"
    sdk_version_installed: str              # actual installed version
    sdk_compatibility: str                  # required range: ">=0.5.0,<1.0.0"
    compatible: bool                        # is installed version in range?

@dataclass
class ModelSpec:
    """Supported model specification."""
    provider: str                           # e.g., "anthropic", "openai", "google"
    model_id: str                           # e.g., "claude-sonnet-4-6", "gpt-5"
    display_name: str                       # human-readable
    requires_api_key: str                   # env var name, e.g., "ANTHROPIC_API_KEY"

@dataclass
class AgentRuntime:
    """Opaque handle to a ready-to-execute agent. Framework-specific internally."""
    runtime_id: str
    framework: str
    session_id: str | None = None           # for checkpointed sessions
    _internal: Any  # Framework's native object (e.g., CompiledStateGraph for DeepAgents)

@dataclass
class AgentEvent:
    """Streaming event from agent execution."""
    type: Literal["message", "tool_call", "tool_result", "error", "interrupt", "done"]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # type="interrupt" → metadata includes: tool_name, tool_args, interrupt_message
    # Client must call resume endpoint with approved=True/False

@dataclass
class SDKPackage:
    """Generated SDK artifact."""
    filename: str                  # e.g., "my-agent-sdk-v3.zip"
    content: bytes                 # ZIP file bytes
    dependencies: list[str]        # pyproject.toml dependencies (uv sync)
    python_version: str            # minimum python version
    instructions: str              # setup/usage README content

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

### Parameter Mapping: AgentConfig → `create_deep_agent()`

> See ADR-012 for full rationale. This table shows how each AgentConfig field
> maps to the underlying DeepAgents function call.

| AgentConfig field | `create_deep_agent()` param | Notes |
|---|---|---|
| `model` | `model` | Resolved via `resolve_model()` — "provider:model" string |
| `system_prompt` | `system_prompt` | Prepended before BASE_AGENT_PROMPT |
| `tools` | `tools` | Tool IDs resolved to LangChain BaseTool instances from registry |
| `subagents` | `subagents` | SyncSubAgentConfig → SubAgent dict, AsyncSubAgentConfig → AsyncSubAgent dict |
| `middleware` | `middleware` | MiddlewareConfig toggles control which middleware are in the stack |
| `response_format` | `response_format` | JSON schema dict passed through to LangGraph |
| `backend` | `backend` | BackendConfig.type → StateBackend() or FilesystemBackend(root_dir=...) |
| `interrupt_on` | `interrupt_on` | Dict passed through; triggers HumanInTheLoopMiddleware |
| `checkpointing_enabled` | `checkpointer` | True → AsyncSqliteSaver, False → None |
| `debug` | `debug` | Passed through |
| `name` | `name` | Agent name for metadata |
| `framework_specific` | varies | Escape hatch for any param not covered above |
| `temperature`, `max_tokens` | via model config | Applied when resolving the model instance |
| `recursion_limit` | via graph config | Set on the CompiledStateGraph after creation |
| `user_api_keys` | N/A (env vars) | Decrypted and set as env vars during execution, NOT passed to create_deep_agent() |
| `mcp_servers` | via `attach_mcp_servers()` | Loaded from DB, attached after runtime creation |

**Not mapped in v0.1 (deferred):**
- `skills` → Skills middleware deferred
- `memory` → Memory/AGENTS.md deferred
- `store` → StoreBackend deferred
- `cache` → Prompt cache uses defaults
- `context_schema` → Advanced typing, deferred

---

## 1b. Encryption Interface (core/encryption.py)

> All user-provided secrets are encrypted before DB storage and decrypted on retrieval.
> Services call these functions; repositories never see plaintext secrets.

```python
class SecretEncryption:
    """Fernet-based field-level encryption for secrets at rest.
    Initialized with ENCRYPTION_KEY from environment."""

    def __init__(self, key: str) -> None:
        """key: Fernet key from ENCRYPTION_KEY env var."""
        ...

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a single secret value. Returns base64 Fernet token."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a single secret value. Raises InvalidToken if tampered."""
        ...

    def encrypt_dict_values(self, data: dict[str, str]) -> dict[str, str]:
        """Encrypt all values in a dict (keys stay plaintext).
        Used for: mcp_servers.env_vars, tools.auth_config"""
        ...

    def decrypt_dict_values(self, data: dict[str, str]) -> dict[str, str]:
        """Decrypt all values in a dict."""
        ...

    def mask_secret(self, plaintext: str, visible_prefix: int = 8) -> str:
        """Return masked version for API responses. e.g., 'sk-ant-ab...****'"""
        ...
```

**Security rules:**
- `ENCRYPTION_KEY` missing at startup → **app refuses to start**
- Tampered ciphertext → `InvalidToken` exception → logged as security event
- API GET responses **never return raw secrets** — only masked prefixes or key names
- API POST/PUT responses return the key **once** at creation, then never again
- Secrets are **never logged** — only masked prefixes in structured logs

**What gets encrypted:**

| Location | Field | Encrypted |
|----------|-------|-----------|
| `agent_versions.config` | `user_api_keys` nested object | YES — values only |
| `mcp_servers.env_vars` | All values | YES |
| `mcp_servers.auth_header` | Entire field | YES |
| `tools.auth_config` | All values | YES |
| `api_keys.key_hash` | — | NO — already one-way SHA-256 hashed |
| Everything else | — | NO — not secrets |

---

## 2. API Contracts

> **SECURITY NOTE:** All GET endpoints that return resources containing secrets
> MUST mask or omit secret values. Secrets are only returned in full on POST (creation).

### Auth (provided by OneAI-Auth — NOT in Cortex)

> Registration, login, OAuth, token refresh are all handled by OneAI-Auth.
> Users interact with OneAI-Auth directly for these operations.
> See: OneAI-Auth endpoints at `{AUTH_SERVICE_URL}/api/v1/auth/*`

### Cortex API Keys (local to Cortex)

```
POST   /api/v1/api-keys              → APIKeyCreate      → APIKeyResponse (201) — returns key once
GET    /api/v1/api-keys              →                   → list[APIKeySummary] (200) — prefix only
DELETE /api/v1/api-keys/{id}         →                   → 204 (revoke)
```

> Cortex API keys are for **programmatic access** to hosted agents and the Cortex API.
> They are an alternative to JWT Bearer tokens for machine-to-machine scenarios.

### Auth Integration (internal — not user-facing endpoints)

```python
# FastAPI dependency — injected into every protected endpoint
async def get_current_user(
    authorization: str = Header(...),  # "Bearer <jwt>" or "ApiKey <key>"
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """
    Validates JWT (from OneAI-Auth) or Cortex API key.
    Returns AuthenticatedUser(user_id=UUID, auth_method="jwt"|"api_key").
    No HTTP call to Auth service — JWT decoded locally with shared secret.
    """

@dataclass
class AuthenticatedUser:
    user_id: UUID          # from JWT sub claim or API key lookup
    auth_method: str       # "jwt" or "api_key"

# For profile enrichment (display name, avatar) — async HTTP client
class AuthClient:
    """Calls OneAI-Auth API when user profile data is needed."""
    async def get_user_profile(self, user_id: UUID) -> UserProfile | None: ...
```

### Agents (Builder)

```
POST   /api/v1/agents                → AgentCreate       → AgentResponse (201)
GET    /api/v1/agents                → ?page,limit       → PaginatedResponse[AgentResponse] (200)
GET    /api/v1/agents/{id}           →                   → AgentResponse (200)
PUT    /api/v1/agents/{id}           → AgentUpdate       → AgentResponse (200) — creates new version
DELETE /api/v1/agents/{id}           →                   → 204 (soft delete)
GET    /api/v1/agents/{id}/versions  → ?page,limit       → PaginatedResponse[AgentVersionResponse] (200)
GET    /api/v1/agents/{id}/versions/{version} →          → AgentVersionResponse (200)
```

### Runner

```
POST   /api/v1/agents/{id}/run       → RunRequest        → SSE stream of AgentEvent
POST   /api/v1/sessions/{id}/resume  → ResumeRequest     → SSE stream of AgentEvent (resume after HITL interrupt)
GET    /api/v1/agents/{id}/sessions   → ?page,limit      → PaginatedResponse[SessionResponse] (200)
GET    /api/v1/sessions/{id}          →                   → SessionResponse with messages (200)
DELETE /api/v1/sessions/{id}          →                   → 204
```

> **HITL flow:** When agent hits an `interrupt_on` tool, SSE emits `AgentEvent(type="interrupt")`.
> Client calls `POST /sessions/{id}/resume` with `{approved: true/false, modified_args?: {...}}`
> to continue or skip the tool call. See Flow 2c in data-flows.md.

### Evaluator

```
POST   /api/v1/agents/{id}/test-suites         → TestSuiteCreate    → TestSuiteResponse (201)
GET    /api/v1/agents/{id}/test-suites          →                    → list[TestSuiteResponse] (200)
PUT    /api/v1/test-suites/{id}                 → TestSuiteUpdate    → TestSuiteResponse (200)
POST   /api/v1/test-suites/{id}/run             → EvalRunRequest     → EvalRunResponse (201)
GET    /api/v1/eval-runs/{id}                   →                    → EvalRunResponse with results (200)
GET    /api/v1/agents/{id}/eval-runs            → ?page,limit        → PaginatedResponse[EvalRunResponse] (200)
```

### MCP Servers

```
POST   /api/v1/mcp-servers                          → MCPServerCreate       → MCPServerResponse (201)
GET    /api/v1/mcp-servers                           → ?page,limit           → PaginatedResponse[MCPServerResponse] (200)
GET    /api/v1/mcp-servers/{id}                      →                       → MCPServerResponse (200)
PUT    /api/v1/mcp-servers/{id}                      → MCPServerUpdate       → MCPServerResponse (200)
DELETE /api/v1/mcp-servers/{id}                      →                       → 204
POST   /api/v1/mcp-servers/{id}/test                 →                       → MCPTestResult (200) — connectivity + tool discovery
GET    /api/v1/mcp-servers/{id}/tools                →                       → list[ToolSpec] (200) — discover available tools
POST   /api/v1/agents/{id}/mcp-servers               → {mcp_server_id}       → 201 (assign MCP server to agent)
DELETE /api/v1/agents/{id}/mcp-servers/{mcp_id}      →                       → 204 (unassign)
GET    /api/v1/agents/{id}/mcp-servers               →                       → list[MCPServerResponse] (200)
```

### Deployer

```
POST   /api/v1/agents/{id}/deploy     → DeployRequest     → DeploymentResponse (201)
DELETE /api/v1/deployments/{id}        →                   → 204 (undeploy)
GET    /api/v1/agents/{id}/deployments →                   → list[DeploymentResponse] (200)
GET    /api/v1/agents/{id}/sdk         → ?version          → binary ZIP download (200)
```

### Hosted Agent Endpoint (deployed agents)

```
POST   /api/v1/hosted/{deployment_id}/chat  → ChatRequest → SSE stream of AgentEvent
```

### Tools

```
GET    /api/v1/tools                  → ?framework        → list[ToolResponse] (200)
POST   /api/v1/tools                  → ToolCreate        → ToolResponse (201) — register custom
GET    /api/v1/tools/{id}             →                   → ToolResponse (200)
POST   /api/v1/tools/{id}/test        →                   → ToolTestResult (200) — test auth/connectivity
```

### Frameworks

```
GET    /api/v1/frameworks             →                   → list[AdapterVersionInfo] (200) — all registered adapters with version info
GET    /api/v1/frameworks/{name}      →                   → AdapterVersionInfo (200) — specific adapter details
```

### Health

```
GET    /api/v1/health                 →                   → {"status": "ok", "version": "0.1.0"}
GET    /api/v1/health/ready           →                   → {"ready": true, "db": "ok", "redis": "ok", "auth": "ok"}
```

> **Note:** `auth: "ok"` in readiness check is a HARD requirement — readiness fails if OneAI-Auth is unreachable.

---

## 3. Service Layer Interfaces

```python
class AgentService:
    async def create_agent(self, user_id: UUID, data: AgentCreate) -> Agent: ...
    async def get_agent(self, user_id: UUID, agent_id: UUID) -> Agent: ...
    async def list_agents(self, user_id: UUID, offset: int, limit: int) -> list[Agent]: ...
    async def update_agent(self, user_id: UUID, agent_id: UUID, data: AgentUpdate) -> Agent: ...
    async def delete_agent(self, user_id: UUID, agent_id: UUID) -> None: ...
    async def get_versions(self, agent_id: UUID, offset: int, limit: int) -> list[AgentVersion]: ...

class RunnerService:
    async def run_agent(
        self, user_id: UUID, agent_id: UUID, request: RunRequest
    ) -> AsyncIterator[AgentEvent]: ...
    async def resume_session(
        self, user_id: UUID, session_id: UUID, approved: bool, modified_args: dict | None = None
    ) -> AsyncIterator[AgentEvent]: ...  # resume after HITL interrupt
    async def list_sessions(self, agent_id: UUID, offset: int, limit: int) -> list[Session]: ...
    async def get_session(self, session_id: UUID) -> Session: ...
    async def delete_session(self, session_id: UUID) -> None: ...

class EvaluatorService:
    async def create_test_suite(self, agent_id: UUID, data: TestSuiteCreate) -> TestSuite: ...
    async def run_evaluation(self, test_suite_id: UUID, request: EvalRunRequest) -> EvalRun: ...
    async def get_eval_run(self, eval_run_id: UUID) -> EvalRun: ...
    async def list_eval_runs(self, agent_id: UUID, offset: int, limit: int) -> list[EvalRun]: ...

class DeployerService:
    async def deploy_agent(self, user_id: UUID, agent_id: UUID, request: DeployRequest) -> Deployment: ...
    async def undeploy(self, deployment_id: UUID) -> None: ...
    async def generate_sdk(self, agent_id: UUID, version: int | None) -> SDKPackage: ...
    async def list_deployments(self, agent_id: UUID) -> list[Deployment]: ...

class APIKeyService:
    """Cortex-local API keys for programmatic access (NOT user auth — that's OneAI-Auth)."""
    async def create_api_key(self, user_id: UUID, data: APIKeyCreate) -> APIKey: ...
    async def list_api_keys(self, user_id: UUID) -> list[APIKey]: ...
    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> None: ...
    async def validate_api_key(self, raw_key: str) -> UUID | None: ...  # returns user_id or None

class MCPService:
    """Manages MCP server registrations, testing, and agent assignments."""
    async def register_server(self, user_id: UUID, data: MCPServerCreate) -> MCPServer: ...
    async def list_servers(self, user_id: UUID, offset: int, limit: int) -> list[MCPServer]: ...
    async def get_server(self, user_id: UUID, server_id: UUID) -> MCPServer: ...
    async def update_server(self, user_id: UUID, server_id: UUID, data: MCPServerUpdate) -> MCPServer: ...
    async def delete_server(self, user_id: UUID, server_id: UUID) -> None: ...
    async def test_server(self, server_id: UUID) -> MCPTestResult: ...  # connectivity + auth + tool discovery
    async def discover_tools(self, server_id: UUID) -> list[ToolSpec]: ...
    async def assign_to_agent(self, agent_id: UUID, mcp_server_id: UUID) -> None: ...
    async def unassign_from_agent(self, agent_id: UUID, mcp_server_id: UUID) -> None: ...
    async def get_agent_servers(self, agent_id: UUID) -> list[MCPServer]: ...

class ToolService:
    async def list_tools(self, framework: str | None) -> list[Tool]: ...
    async def register_tool(self, data: ToolCreate) -> Tool: ...
    async def get_tool(self, tool_id: UUID) -> Tool: ...
    async def test_tool(self, tool_id: UUID) -> ToolTestResult: ...  # validate API keys/auth/connectivity
```

---

## 4. Repository Layer Interfaces

```python
class BaseRepository(Generic[T]):
    async def get_by_id(self, id: UUID) -> T | None: ...
    async def create(self, data: dict[str, Any]) -> T: ...
    async def update(self, id: UUID, data: dict[str, Any]) -> T: ...
    async def soft_delete(self, id: UUID) -> None: ...
    async def list(self, *, filters: dict | None, offset: int = 0, limit: int = 50) -> list[T]: ...
    async def count(self, *, filters: dict | None = None) -> int: ...

class AgentRepository(BaseRepository[Agent]):
    async def get_by_user(self, user_id: UUID, offset: int, limit: int) -> list[Agent]: ...
    async def create_version(self, agent_id: UUID, config_snapshot: dict) -> AgentVersion: ...
    async def get_versions(self, agent_id: UUID, offset: int, limit: int) -> list[AgentVersion]: ...
    async def get_version(self, agent_id: UUID, version: int) -> AgentVersion | None: ...
    async def get_latest_version(self, agent_id: UUID) -> AgentVersion | None: ...

class SessionRepository(BaseRepository[Session]):
    async def get_by_agent(self, agent_id: UUID, offset: int, limit: int) -> list[Session]: ...
    async def add_message(self, session_id: UUID, role: str, content: str, metadata: dict) -> Message: ...
    async def get_messages(self, session_id: UUID) -> list[Message]: ...

class EvaluationRepository(BaseRepository[TestSuite]):
    async def create_eval_run(self, test_suite_id: UUID, agent_version: int) -> EvalRun: ...
    async def add_eval_result(self, run_id: UUID, result: dict) -> EvalResult: ...
    async def get_eval_run_with_results(self, run_id: UUID) -> EvalRun: ...
    async def get_runs_by_agent(self, agent_id: UUID, offset: int, limit: int) -> list[EvalRun]: ...
```
