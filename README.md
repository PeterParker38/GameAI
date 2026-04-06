# The Shimla Ledger

 
 _A stormy night. A dead man in the library. Four suspects. No escape._
 An AI-powered murder mystery game set in the Viceregal Library, Shimla, 1926. Built with LangGraph, Neo4j, FastAPI, and Unity.

---

## What is this?

The Shimla Ledger is a fully stateful AI murder mystery game where NPCs remember what you've said, lie to your face, break down under pressure, and can be caught in contradictions. The victim is **Elias Thorne**. Three suspects: **Arjun Singh**, **Dr. Arthur Bell**, **Mrs. Eleanor Graves**. One murderer. You have to figure out who.

Unlike traditional mystery games with hardcoded dialogue trees, every NPC in this game:

- Maintains a running memory of your entire conversation
- Has a suspicion score that shifts their emotional state and dialogue behavior
- Can tell lies that are tracked and detectable
- Responds differently depending on what evidence you've already found

---

## Tech Stack

|Layer|Technology|
|---|---|
|Frontend|Unity|
|Backend|FastAPI + Uvicorn|
|AI Orchestration|LangGraph StateGraph + MemorySaver|
|NPC Dialogue LLM|Groq — llama-3.3-70b-versatile (temperature 0.2)|
|Intent + Lie Detection LLM|Groq — llama-3.3-70b-versatile (temperature 0.0)|
|Summarization LLM|Google Gemini|
|Knowledge Graph|Neo4j AuraDB|
|Deployment|Railway|

---

## Architecture

### The 5 FastAPI Endpoints

|Method|Endpoint|What it does|
|---|---|---|
|GET|`/start`|Initializes a new game session, invokes LangGraph fresh|
|POST|`/talk`|Player talks to an NPC `{npc_name, player_input}`|
|POST|`/search`|Player searches a location `{location}`|
|POST|`/accuse`|Player accuses a suspect `{suspect}`|
|GET|`/state`|Reads current frozen game state without resuming graph|

### LangGraph Pipeline

Every player action resumes a persistent `StateGraph` checkpointed by `MemorySaver`. The graph pauses at `input_node` using `interrupt()` between HTTP requests and resumes via `Command(resume=...)`.

**NPC Conversation Branch** (triggered when `search=False`):

```
input_node → intent_node → retrieve_node → lie_detection_node → prompt_response_node → summary_node → input_node (loop)
```

**Search Branch** (triggered when `search=True`):

```
input_node → intent_node → officer_search_node → discover_evidence_node → update_gates_node → input_node (loop)
```

### What each node does

- **input_node** — receives player input, appends to NPC chat history, calls `interrupt()` to pause graph
- **intent_node / router_node** — uses Groq (temperature 0) to classify player input into conversation or evidence search and route to that branch
- **retrieve_node** — runs a Cypher query on Neo4j based on detected intent and entities, stores result in `npc.retrieved_data`
- **lie_detection_node** — uses Groq (temperature 0) to compare NPC's last statement against `retrieved_data`, appends contradiction to `npc.lies_caught`
- **prompt_response_node** — builds a full prompt using `npc.prompt + breakdown_state behavior rules + retrieved_data + running_summary` , calls Groq (temperature 0.2), parses JSON `{response, lies_told}`, trims `chat_history` to 6 entries
- **summary_node** — calls Gemini to compress chat history into `npc.running_summary`
- **officer_search_node** — validates the searched location, generates officer narration
- **discover_evidence_node** — finds evidence at location, updates `npc.sus` scores, appends to `evidence_found`
- **update_gates_node** — recalculates `locations_unlocked` based on suspicion thresholds and specific evidence IDs, sets `accusation_available`

### NPC Breakdown System

Each NPC has suspicion thresholds that shift their emotional state and dialogue behavior:

|NPC|State 1|State 2|State 3|State 4|
|---|---|---|---|---|
|Graves|composed (0)|crack (25)|shaken (55)|collapse (85)|
|Bell|defensive (0)|uneasy (20)|shaken (40)|break (65)|
|Arjun|guarded (0)|fracture (15)|shaken (35)|collapse (60)|

### Game State

The entire game lives in one persistent `State` TypedDict object:

```python
class State(TypedDict):
    current_npc:          str #intent_node
    search:               bool #intent_node
    search_location:      str #intent_node
    accusation_available: bool #update_gates_node
    last_found_evidence:  Optional[list[str]] #discover_evidence_node  #it was missing, caused sus to never update
    evidence_found:       list[str] #discover_evidence_node
    locations_unlocked:   dict[str, bool] #update_gates_node
    npcs:                 dict[str, NPC] #preset
    player_input:         str #input node
    search_result:       str #discover_evidence_node
    npc_response:         str #prompt_response
```

Each `NPC` object contains:

```python
class NPC(BaseModel):
    npc_id:          str        = "" #preset
    prompt:          str        = "" #preset
    retrieved_data:  str        = "" #retrieval
    lies_told:       list[str]  = [] #interaction
    lies_caught:     list[str]  = [] #lie_detection
    chat_history:    list[dict] = [] #interaction
    sus:             float      = 0.0 #update_gates_node
    running_summary: str        = "" #summarizer
```

### Neo4j Knowledge Graph

Nodes: `NPC`, `Evidence`, `Location`, `Fact`, `Event`, `Phase`, `WinCondition`, `GlobalState`

Key relationships:

```
(Evidence)-[:LINKS_TO]->(NPC)
(Evidence)-[:PROVES]->(Fact)
(Evidence)-[:LOCATED_IN]->(Location)
(NPC)-[:WAS_AT]->(Location)
(NPC)-[:CLAIMS]->(Fact)
(NPC)-[:SUSPECTS]->(NPC)
(Event)-[:OCCURRED_AT]->(Location)
```

---

## Game World

- **Victim:** Elias Thorne
- **Murderer:** Mrs. Eleanor Graves
- **Suspects:** Arjun Singh, Dr. Arthur Bell, Mrs. Eleanor Graves
- **Evidence:** Brandy Glass, Ledger, Pantry Log, Botanical Crates, Torn Page 42, Visha Vigyan Manuscript, Stopped Clock
- **Locations:** Thorne's Study, Arjun's Office, Reading Hall _(unlocked by default)_, Storage Room, Interrogation, Admin Office, Pantry _(locked, unlock via suspicion thresholds)_

---


## Deployed API

The backend is live at:


[Railway-Backend](https://gameaitesting-production.up.railway.app/docs#/)


---

## Team

| Name                | Contributions                                                                    |
| ------------------- | -------------------------------------------------------------------------------- |
| **Rohit**           | Neo4j database design, knowledge graph construction, game state architecture     |
| **Kedar Hadnurkar** | Lie detection, retrieval pipeline, deployment (Railway), graph and gamestate     |
| **Aashima Singh**   | Summarizer node, evidence search system, FastAPI server                          |
| **Aarushi**         | NPC prompting, emotion-driven response generation, suspicion and lie integration |

---

## Project Context

Built as part of a Google Development Group - IIT Indore's initiative. The goal was to build a real stateful AI game — not a chatbot with a skin.