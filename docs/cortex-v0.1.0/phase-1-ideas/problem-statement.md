# Phase 1 — Problem Statement

**Date:** 2026-04-10
**Status:** Accepted
**Project:** OneAI-Cortex

---

## Problem Definition

**What:** No unified open-source platform exists where users can build, test, evaluate, and deploy/export AI agents without deep knowledge of underlying agentic frameworks. Each framework (LangGraph, CrewAI, AutoGen, Mastra, etc.) has its own APIs, patterns, and deployment strategies — forcing users to become framework experts before they can ship an agent.

**Who:**
- Developers building AI agents who want framework abstraction
- AI teams evaluating multiple frameworks without rewriting
- Businesses needing self-hosted or cloud-hosted agent deployment
- Open-source community seeking a vendor-neutral agent platform

**Why now:** The agent framework landscape is fragmenting rapidly. Users need a layer above that abstracts framework complexity and provides a unified Build → Test → Evaluate → Deploy/Export pipeline.

**Constraints:**
- Open source from day one (full transparency, community-driven)
- Start with DeepAgents (LangGraph-based by LangChain) as first runtime
- Must be extensible to add other agent frameworks later
- Must support both self-hosting and cloud hosting
- Users must be able to download a standalone SDK for any agent they build

**Success looks like:**
A user signs up, builds an agent via API/UI, tests it with sample inputs, evaluates its performance metrics, and either hosts it on the platform or downloads a standalone SDK package — all within a single session.
