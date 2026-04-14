# Phase 2 — Interface Design

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## 1. Existing API Contracts (Verified — No Changes)

### POST /api/v1/agents — Create Agent with API Keys

**Request Body:**
```json
{
  "name": "Research Assistant",
  "description": "Helps with research tasks",
  "framework": "deepagents",
  "config": {
    "model": "anthropic:claude-sonnet-4-6",
    "system_prompt": "You are a helpful assistant.",
    "user_api_keys": {
      "ANTHROPIC_API_KEY": "sk-ant-api03-..."
    }
  }
}
```

**Internal flow:** `AgentService.create_agent()` → `_encrypt_config_secrets(config)` → encrypts `user_api_keys` values → stores in `AgentVersion.config` JSONB.

### GET /api/v1/agents/{id}/versions/{version} — Retrieve Version Config

**Response:**
```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "version": 1,
  "config": {
    "model": "anthropic:claude-sonnet-4-6",
    "system_prompt": "You are a helpful assistant.",
    "user_api_keys": {
      "ANTHROPIC_API_KEY": "gAAAAABm...encrypted-fernet-token..."
    },
    "tools": [],
    "mcp_servers": []
  },
  "change_summary": "Initial version",
  "created_at": "2026-04-13T12:00:00Z"
}
```

**Note:** `user_api_keys` values are **Fernet-encrypted tokens**, not plaintext. The frontend should:
- Check if the key exists in the dict → show "Configured" indicator
- Never attempt to decrypt or display the value
- To overwrite: send new plaintext value via `PUT /agents/{id}` → backend re-encrypts

### PUT /api/v1/agents/{id} — Update Agent with New API Keys

**Request Body:**
```json
{
  "name": "Research Assistant",
  "config": {
    "model": "anthropic:claude-sonnet-4-6",
    "system_prompt": "Updated prompt.",
    "user_api_keys": {
      "ANTHROPIC_API_KEY": "sk-ant-api03-new-key-..."
    }
  },
  "change_summary": "Updated API key and prompt"
}
```

**Internal flow:** Config changes trigger `AgentService.update_agent()` → creates new `AgentVersion` with incremented version number → encrypts `user_api_keys` → updates `Agent.current_version`.

---

## 2. Existing Service Interfaces (Verified — No Changes)

### AgentService._encrypt_config_secrets()

```python
def _encrypt_config_secrets(self, config: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields in agent config."""
    config = dict(config)  # shallow copy
    if "user_api_keys" in config and config["user_api_keys"]:
        config["user_api_keys"] = self._encryption.encrypt_dict_values(
            config["user_api_keys"]
        )
    return config
```

### RunnerService.run_session() — Key Decryption

```python
# Lines 92-94 in runner.py
user_api_keys = {}
if config_dict.get("user_api_keys"):
    user_api_keys = self._encryption.decrypt_dict_values(config_dict["user_api_keys"])
```

### DeepAgentsAdapter.create_runtime() — Key Injection

```python
# Lines 110-114 in adapter.py
env_backup: dict[str, str | None] = {}
for key_name, key_value in user_api_keys.items():
    env_backup[key_name] = os.environ.get(key_name)
    os.environ[key_name] = key_value
```

---

## 3. Error Message Patterns (For Frontend Pattern Matching)

When `create_runtime()` fails due to missing API keys, the error propagates from the LLM provider SDK. Common patterns:

| Provider | Typical Error Message | Match Pattern |
|----------|----------------------|---------------|
| Anthropic | `"AuthenticationError: Invalid API key"` | `authentication\|api.?key` |
| OpenAI | `"AuthenticationError: Incorrect API key provided"` | `authentication\|api.?key` |
| Google | `"UNAUTHENTICATED: Request had invalid authentication credentials"` | `unauthenticated\|credentials` |
| Generic | `"Failed to create agent runtime: ..."` | `failed.*runtime` |

**Frontend regex recommendation:** `/api.?key|unauthorized|authentication|unauthenticated|ANTHROPIC_API_KEY|OPENAI_API_KEY|GOOGLE_API_KEY/i`
