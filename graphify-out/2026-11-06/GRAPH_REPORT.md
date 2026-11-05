# Graph Report - Agri_watch  (2026-11-06)

## Corpus Check
- 44 files · ~54,033 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .css 2, .bat 2)

## Summary
- 384 nodes · 680 edges · 24 communities (11 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d4914b7b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- mandi_tracker.py
- tools.py
- LangGraph State Machine & Workflow Routing
- External Libraries & Voice/Mandi Integration
- AgriWatchLangGraphLLM
- LiveKit WebRTC Real-Time Voice Agent
- llm_reasoner_node
- observability.py
- Project Architecture & Implementation Plans
- LangGraph Pipeline Integration Tests
- Cron Automation & Setup Scripts
- KICKOFF — Agri_watch
- index.md
- prewarm
- package.json
- app.py
- voice-worker
- TestAgriWatchBackend
- .oxlintrc.json
- React + Vite

## God Nodes (most connected - your core abstractions)
1. `AgentState` - 22 edges
2. `traceable()` - 18 edges
3. `get_crop_price()` - 14 edges
4. `compare_mandi_arbitrage()` - 14 edges
5. `get_agriwatch_graph()` - 13 edges
6. `sync_mandi_data()` - 13 edges
7. `check_msp_floor()` - 11 edges
8. `get_crop_price_trend()` - 11 edges
9. `TestAgriWatchLangGraph` - 11 edges
10. `entrypoint()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `entrypoint()` --uses--> `AgriWatchLangGraphLLM`  [INFERRED]
  voice_engine/livekit_worker.py → agents/llm_adapter.py
- `TestAgriWatchLangGraph` --uses--> `AgentState`  [INFERRED]
  tests/test_langgraph_pipeline.py → agents/state.py
- `AgriWatchVoiceAssistant` --uses--> `AgentState`  [INFERRED]
  voice_engine/livekit_worker.py → agents/state.py
- `TestSpecialistSubAgent` --uses--> `AgentState`  [INFERRED]
  tests/test_specialist_subagent.py → agents/state.py
- `start_console()` --uses--> `AgentState`  [INFERRED]
  voice_engine/interactive_console.py → agents/state.py

## Import Cycles
- None detected.

## Communities (24 total, 13 thin omitted)

### Community 0 - "mandi_tracker.py"
Cohesion: 0.08
Nodes (9): find_nearest_date(), is_commodity_match(), MandiPriceService, fetch_records_for_date(), load_existing_keys_for_dates(), sync_mandi_data(), TestDailyMandiSync, start_daily_sync_scheduler() (+1 more)

### Community 1 - "tools.py"
Cohesion: 0.07
Nodes (22): check_msp_floor_tool(), compare_mandi_arbitrage_tool(), consult_economic_specialist_tool(), get_crop_price_tool(), get_crop_price_trend_tool(), traceable(), evaluate_holding_strategy(), evaluate_vehicle_arbitrage() (+14 more)

### Community 2 - "LangGraph State Machine & Workflow Routing"
Cohesion: 0.07
Nodes (11): fallback_node(), build_agriwatch_graph(), get_agriwatch_graph(), route_guardrail(), route_llm_result(), guardrail_node(), init_observability(), AgentState (+3 more)

### Community 5 - "LiveKit WebRTC Real-Time Voice Agent"
Cohesion: 0.10
Nodes (5): AgriWatchVoiceAgent, AgriWatchVoiceAssistant, entrypoint(), user_presence_task(), _user_state_changed()

### Community 6 - "llm_reasoner_node"
Cohesion: 0.25
Nodes (3): get_groq_llm(), llm_reasoner_node(), resolve_groq_model()

### Community 8 - "Project Architecture & Implementation Plans"
Cohesion: 0.22
Nodes (9): Milestone M1: Gnani LiveKit Setup, Milestone M2: Dual-Loop Steering Router, Milestone M3: LiveKit Voice Worker, Agri_watch Sovereign Indic Voice Agent, LangGraph Cognitive Multi-Agent Harness, APMC Market Intelligence Suite, Agri_watch System Architecture, LiveKit Voice Engine & Gnani STT/TTS (+1 more)

### Community 17 - "package.json"
Cohesion: 0.07
Nodes (37): dependencies, livekit-client@^2.23.0, @livekit/components-react@^2.9.25, lucide-react@^1.69.0, react@^19.3.1, react-dom@^19.3.1, tailwindcss@^4.3.4, @tailwindcss/vite@^4.3.4 (+29 more)

### Community 18 - "app.py"
Cohesion: 0.09
Nodes (15): chat_endpoint(), ChatRequest, ChatResponse, _create_token(), get_livekit_token(), get_metadata(), get_price_endpoint(), health_check() (+7 more)

### Community 19 - "voice-worker"
Cohesion: 0.08
Nodes (25): context, dockerfile, interval, retries, start_period, test, timeout, services (+17 more)

### Community 21 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 22 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

## Knowledge Gaps
- **4 isolated node(s):** `Milestone M1: Gnani LiveKit Setup`, `Milestone M2: Dual-Loop Steering Router`, `Milestone M3: LiveKit Voice Worker`, `Agri_watch Core Dependencies`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 192 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentState` connect `LangGraph State Machine & Workflow Routing` to `tools.py`, `AgriWatchLangGraphLLM`, `LiveKit WebRTC Real-Time Voice Agent`, `llm_reasoner_node`, `LangGraph Pipeline Integration Tests`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AgentState` (e.g. with `fallback_node()` and `build_agriwatch_graph()`) actually correct?**
  _`AgentState` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Milestone M1: Gnani LiveKit Setup`, `Milestone M2: Dual-Loop Steering Router`, `Milestone M3: LiveKit Voice Worker` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `mandi_tracker.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Why does `traceable()` connect `tools.py` to `LangGraph State Machine & Workflow Routing`, `LiveKit WebRTC Real-Time Voice Agent`, `llm_reasoner_node`, `observability.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Should `tools.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06836055656382335 - nodes in this community are weakly interconnected._
- **Why does `sync_mandi_data()` connect `mandi_tracker.py` to `tools.py`, `LangGraph State Machine & Workflow Routing`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._