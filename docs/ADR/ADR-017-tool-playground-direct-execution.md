## ADR-017: Tool Playground — Direct Execution Model

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from Ideas phase — user feedback on testing approach)

### Context

Users need to verify that a tool works with their API keys and produces useful output before attaching it to an agent. Three testing approaches were considered:
- Binary pass/fail test (too blunt — no diagnostic value)
- 3-stage diagnostic test: key validation → input test → output validation (over-engineered)
- Direct execution: user provides keys + input, sees actual output (simple and effective)

User feedback: "just keep API key and add input queries and parameters as per the tool needs and test the tool — if it's ok then we move further to use it under the agent or not."

### Decision

Implement a **tool playground endpoint** (`POST /tools/{tool_id}/test`) that directly executes the tool:
1. User provides their API keys and input query/parameters
2. Endpoint instantiates the LangChain tool with those keys
3. Executes the tool with the user's input
4. Returns the **actual output** (or error message if it failed)
5. User evaluates the output and decides whether to use the tool

No artificial validation stages. The tool execution itself is the test. Provider error messages (401, 403, timeout) are more informative than any custom validation layer.

Tool execution errors return HTTP 200 with `status="failed"` in the body — the endpoint worked, the tool didn't. This keeps error handling simple and gives users the full error context.

### Consequences

**Positive:**
- Simple to implement — one endpoint, one execution, one response
- User sees real output and makes their own judgment
- Provider errors are naturally descriptive (no custom error mapping needed)
- No wasted API calls on pre-validation probes
- Consistent with "try it yourself" pattern (like Swagger "Try it out")

**Negative:**
- No automated output quality assessment — user must judge output themselves
- No staged diagnostics — if it fails, user sees one error (not which stage failed)
- API key validation happens implicitly through execution (slightly more expensive than a lightweight auth probe)

**Neutral:**
- Test results stored globally (last test wins), not per-user
- `test_detail` JSONB captures output/error snapshot for reference

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Binary pass/fail test | No diagnostic value; user can't tell bad key from bad output |
| 3-stage diagnostic test | Over-engineered; separate key validation and output schema checking add complexity without proportional value — the execution itself provides all the information |

### Validation

- Playground endpoint returns actual tool output on success
- Playground endpoint returns provider error message on failure (e.g., "401 Unauthorized")
- Missing required API keys are caught before execution (400 error)
- Custom tools without `langchain_class` return clear 400 error
- `test_status` and `test_detail` are updated after each test
