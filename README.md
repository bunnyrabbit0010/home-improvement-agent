# Home Improvement Agent

An agentic assistant for homeowners planning home improvement projects.

This project is being built to move beyond a simple search script into a robust, type-safe multi-step agent that can:
- Discover and vet  contractors
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
- Requested service (Roofing/Plumbing/Landscaping/etc.)

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
- Repository has been restructured into modular components: `agents/`, `tools/`, `schema/`, and `workflows/`.
- Phase 1 workflow graph is implemented in `workflows/discovery_vetting_graph.py` with the following nodes:
  - `scrape_yelp_node`
  - `scrape_google_node`
  - `scrape_bbb_node`
  - `scrape_website_node`
  - `synthesize_vetting_node`
- End-to-end CLI execution is available via `main.py`:
  - accepts service type, zip code, and target contractor count
  - executes workflow
  - prints consolidated synthesis output and flags
- Tooling split is now explicit:
  - `tools/firecrawl_tool.py` for discovery/scraping/extraction
  - `tools/llm_tool.py` for OpenAI-based semantic review summarization
- Data models have expanded to support enrichment:
  - Yelp candidate list and selected index in workflow state
  - `Contractor` includes website/contact fields plus `yelp_profile_url`
  - URL normalization separates Yelp profile links from official contractor website links
- Workflow currently runs MVP enrichment/synthesis for selected candidate index `0` (single-candidate path).

## Near-Term Build Priorities

1. Extend Phase 1 from single-candidate MVP to full `N`-candidate enrichment and synthesis loop.
2. Add deterministic ranking/scoring criteria and confidence/provenance tracking per contractor field.
3. Improve source quality controls:
   - contractor website fallback when Yelp website is missing
   - tighter Google/BBB candidate disambiguation and matching
4. Add workflow and tool tests (state transition tests, schema validation fixtures, and smoke integration tests).
5. Begin Phase 2 quote ingestion/extraction pipeline with strict schema validation.
6. Prepare Phase 3 MCP integrations (calendar/email) with explicit HITL approval checkpoints.
