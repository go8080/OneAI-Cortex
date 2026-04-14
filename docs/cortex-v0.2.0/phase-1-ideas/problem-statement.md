# Phase 1 — Problem Statement

**Date:** 2026-04-10
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Categorized Pre-Built Tool Catalog

---

## Problem Definition

**What:** OneAI-Cortex has a flat tool system with no categorization and no pre-built tool catalog. Users must manually register every tool via `POST /tools`. There is no way to browse, discover, or filter tools by domain (search, database, communication, etc.). The platform ships with zero tools out-of-the-box. Additionally, there is no mechanism for users to test whether a tool actually works with their API keys before attaching it to an agent — leading to runtime failures during agent execution.

**Who:**
- Agent builders who need to quickly find and attach relevant tools to their agents
- New users evaluating the platform who expect a ready-to-use tool ecosystem
- AI teams building domain-specific agents (e.g., research agents need search + research tools)
- Platform maintainers who need a structured way to manage 196+ LangChain tools

**Why now:** The LangChain tool ecosystem is mature (196+ tools across 60 modules in langchain_classic). OneAI-Cortex already supports tool references in agent configs (`config.tools = ["tool_name"]`), but the tools table is empty by default. Users cannot build meaningful agents without manually registering every tool they need.

**Constraints:**
- Must fit existing layer cake architecture (Model → Repository → Service → API)
- Agent configs reference tools by name (JSONB) — this contract must not break
- 20 predefined categories from business requirements
- Source tools come from LangChain Classic (which delegates to langchain_community)
- Tool model already has `tool_type` enum (builtin/custom) — must align with this
- Must not break existing custom tool registration flow

**Success looks like:**
- API consumers can list all 20 tool categories via a single endpoint
- Users can browse tools filtered by category (e.g., `GET /tools?category=search`)
- 196+ LangChain tools are pre-populated in the database with correct category assignments
- Agents can reference pre-built tools by name in their config, same as custom tools
- New platform deployments ship with a full tool catalog out-of-the-box
- Users can **try any tool** before using it in an agent via `POST /tools/{tool_id}/test`:
  - Provide API keys required by the tool
  - Provide input query and parameters as per the tool's needs
  - Execute the tool and get the actual output back
  - User evaluates the output and decides whether to use the tool in their agent
- If the API key is invalid, the tool execution error itself tells the user (e.g., 401 Unauthorized)
- If the output is not what they expected, they can see it directly and decide not to use the tool
- Tool test results are stored (status, output snapshot, last_tested_at) for reference
