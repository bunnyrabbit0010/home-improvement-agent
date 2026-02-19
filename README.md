# Roofing Project Agent

An agentic assistant for homeowners planning roofing projects.

This project is being built to move beyond a simple search script into a robust, type-safe multi-step agent that can:
- Discover and vet roofing contractors
- Extract and compare quote details from PDFs
- Coordinate scheduling and communications with human approval gates

## Vision

The goal is to build a genuinely agentic system that can plan, self-correct, and execute tasks autonomously within user-defined boundaries.

Key requirements:
- Strong schema validation and type safety
- Stateful orchestration across multi-step workflows
- Reliable extraction from messy web and document data
- Secure access to user context (files, calendar, email)
- Human-in-the-loop controls for sensitive actions

## Core Stack ("Agentic Trio")

The planned architecture centers on:
- `LangGraph`: Stateful orchestration, retries, branching, and loop-back behavior
- `Firecrawl`: Web search/scrape/extract from sources like Yelp, Google Maps, and contractor sites
- `MCP (Model Context Protocol)`: Secure tool/context access for local files, calendars, and messaging integrations

Supporting libraries and patterns:
- `Pydantic` models for strict schemas
- Structured output extraction for deterministic quote parsing
- Tool abstractions for BBB checks, review summarization, and outbound communication

## Implementation Roadmap

### Phase 1: Discovery and Vetting Engine

Input:
- ZIP code
- Roof type / requested service

Output:
- Structured JSON list of vetted roofing contractors

Planned flow:
1. Define contractor schemas with `Pydantic`.
2. Use `Firecrawl` search over sources such as Yelp and Google Maps.
3. For each candidate, run vetting sub-steps in a LangGraph workflow:
   - Scrape contractor site and detect relevant roofing specialization
   - Check BBB profile/reputation signals
   - Summarize recent reviews and identify recurring strengths/risks
4. Rank/return top candidates in a consistent output format.

### Phase 2: Quote Analyzer (Structured Extraction)

Input:
- Multiple contractor quote PDFs

Output:
- Side-by-side normalized comparison table
- Outlier flags for unusual pricing/terms

Planned flow:
1. Convert PDFs to structured text.
2. Use a strict extraction schema (material cost, labor cost, warranty years, debris removal, shingle type, etc.).
3. Validate outputs with `Pydantic`.
4. Generate a Markdown comparison table with outlier highlighting.

### Phase 3: Communication Hub (MCP Integration)

Input:
- Vetted contractors + quote context + homeowner preferences

Output:
- Drafted and approved outreach + scheduled meetings

Planned flow:
1. Integrate calendar tooling (e.g., Google Calendar via MCP) for availability lookup.
2. Integrate messaging tooling (e.g., Gmail/SendGrid) for contractor outreach.
3. Add Human-in-the-Loop (HITL) checkpoints:
   - Agent drafts emails/messages
   - Execution pauses for homeowner approval before send

## Current Status

Current repository status:
- Prototype script in `agents/researcher.py` that performs contractor discovery/extraction with Firecrawl
- Initial Pydantic schema for contractor results
- Core roadmap above defines next build milestones toward full agent behavior

## Near-Term Build Priorities

1. Restructure into modular components (`agents/`, `tools/`, `schema/`, `workflows/`).
2. Implement a first LangGraph workflow for Phase 1.
3. Add schema versioning and test fixtures for extraction quality.
4. Implement quote ingestion/extraction pipeline for Phase 2.
5. Add MCP-backed calendar/email tools with HITL interrupts for Phase 3.
