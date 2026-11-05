# Graph Report - Agri_watch  (2026-11-03)

## Corpus Check
- 32 files · ~48,332 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .example 1, .dot 1)

## Summary
- 254 nodes · 484 edges · 18 communities (8 shown, 10 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `082f556b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- daily_mandi_sync.py
- tools.py
- LangGraph State Machine & Workflow Routing
- External Libraries & Voice/Mandi Integration
- AgriWatchLangGraphLLM
- LiveKit WebRTC Real-Time Voice Agent
- llm_reasoner.py
- observability.py
- Project Architecture & Implementation Plans
- LangGraph Pipeline Integration Tests
- Cron Automation & Setup Scripts
- KICKOFF — Agri_watch
- index.md
- prewarm
- MandiPriceService

## God Nodes (most connected - your core abstractions)
1. `AgentState` - 22 edges
2. `traceable()` - 18 edges
3. `sync_mandi_data()` - 13 edges
4. `get_agriwatch_graph()` - 12 edges
5. `get_crop_price()` - 12 edges
6. `compare_mandi_arbitrage()` - 12 edges
7. `TestAgriWatchLangGraph` - 11 edges
8. `entrypoint()` - 11 edges
9. `fallback_node()` - 10 edges
10. `get_crop_price_trend()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `entrypoint()` --uses--> `AgriWatchLangGraphLLM`  [INFERRED]
  voice_engine/livekit_worker.py → agents/llm_adapter.py
- `TestAgriWatchLangGraph` --uses--> `AgentState`  [INFERRED]
  tests/test_langgraph_pipeline.py → agents/state.py
- `TestSpecialistSubAgent` --uses--> `AgentState`  [INFERRED]
  tests/test_specialist_subagent.py → agents/state.py
- `AgriWatchVoiceAssistant` --uses--> `AgentState`  [INFERRED]
  voice_engine/livekit_worker.py → agents/state.py
- `fetch_records_for_date()` --uses--> `MandiPriceService`  [INFERRED]
  scripts/daily_mandi_sync.py → mandi_tracker.py

## Import Cycles
- None detected.

## Communities (18 total, 10 thin omitted)

### Community 0 - "daily_mandi_sync.py"
Cohesion: 0.14
Nodes (6): fetch_records_for_date(), load_existing_keys_for_dates(), sync_mandi_data(), TestDailyMandiSync, start_daily_sync_scheduler(), _scheduler_loop()

### Community 1 - "tools.py"
Cohesion: 0.09
Nodes (17): fallback_node(), traceable(), evaluate_holding_strategy(), evaluate_vehicle_arbitrage(), run_economic_specialist(), check_msp_floor(), clean_market_name(), compare_mandi_arbitrage() (+9 more)

### Community 2 - "LangGraph State Machine & Workflow Routing"
Cohesion: 0.09
Nodes (8): build_agriwatch_graph(), get_agriwatch_graph(), route_guardrail(), route_llm_result(), guardrail_node(), init_observability(), AgentState, start_console()

### Community 3 - "External Libraries & Voice/Mandi Integration"
Cohesion: 0.10
Nodes (4): load_env(), generate_participant_token(), get_gnani_api_key(), GnaniVoiceClient

### Community 5 - "LiveKit WebRTC Real-Time Voice Agent"
Cohesion: 0.10
Nodes (5): AgriWatchVoiceAgent, AgriWatchVoiceAssistant, entrypoint(), user_presence_task(), _user_state_changed()

### Community 6 - "llm_reasoner.py"
Cohesion: 0.11
Nodes (8): check_msp_floor_tool(), compare_mandi_arbitrage_tool(), consult_economic_specialist_tool(), get_crop_price_tool(), get_crop_price_trend_tool(), get_groq_llm(), llm_reasoner_node(), resolve_groq_model()

### Community 8 - "Project Architecture & Implementation Plans"
Cohesion: 0.22
Nodes (9): Milestone M1: Gnani LiveKit Setup, Milestone M2: Dual-Loop Steering Router, Milestone M3: LiveKit Voice Worker, Agri_watch Sovereign Indic Voice Agent, LangGraph Cognitive Multi-Agent Harness, APMC Market Intelligence Suite, Agri_watch System Architecture, LiveKit Voice Engine & Gnani STT/TTS (+1 more)

### Community 17 - "MandiPriceService"
Cohesion: 0.16
Nodes (3): find_nearest_date(), is_commodity_match(), MandiPriceService

## Knowledge Gaps
- **4 isolated node(s):** `Milestone M1: Gnani LiveKit Setup`, `Milestone M2: Dual-Loop Steering Router`, `Milestone M3: LiveKit Voice Worker`, `Agri_watch Core Dependencies`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 132 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentState` connect `LangGraph State Machine & Workflow Routing` to `tools.py`, `AgriWatchLangGraphLLM`, `LiveKit WebRTC Real-Time Voice Agent`, `llm_reasoner.py`, `LangGraph Pipeline Integration Tests`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AgentState` (e.g. with `fallback_node()` and `build_agriwatch_graph()`) actually correct?**
  _`AgentState` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Milestone M1: Gnani LiveKit Setup`, `Milestone M2: Dual-Loop Steering Router`, `Milestone M3: LiveKit Voice Worker` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `daily_mandi_sync.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._
- **Why does `traceable()` connect `tools.py` to `LangGraph State Machine & Workflow Routing`, `LiveKit WebRTC Real-Time Voice Agent`, `llm_reasoner.py`, `observability.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Should `tools.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0851063829787234 - nodes in this community are weakly interconnected._
- **Why does `sync_mandi_data()` connect `daily_mandi_sync.py` to `MandiPriceService`, `LangGraph State Machine & Workflow Routing`, `tools.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._