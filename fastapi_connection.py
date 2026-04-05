import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langgraph.types import Command

from nodes.graph import garph
from nodes.gamestate import state


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/web", StaticFiles(directory="web"), name="web")


@app.get("/")
def serve_game():
    return FileResponse("web/index.html")


THREAD       = {"configurable": {"thread_id": "shimla_default"}}
LATEST_STATE = {}

VALID_NPCS = {"arjun", "bell", "graves", "officer"}

VALID_LOCATIONS = {
    "Thorne's study",
    "Arjun's office",
    "Reading hall",
    "Storage room",
    "Interrogation",
    "Admin office",
    "Pantry",
}


# ── Request Models ─────────────────────────────────────────────

class TalkRequest(BaseModel):
    npc_name:     str
    player_input: str

class SearchRequest(BaseModel):
    location: str


# ── Helper ─────────────────────────────────────────────────────
# Used by /talk and /search only
# Returns everything the game engine needs to update UI after an action

def extract_response(graph_state: dict) -> dict:
    npcs          = graph_state.get("npcs", {})
    scores        = {}
    summaries     = {}
    lies_caught   = {}

    for npc_id, npc in npcs.items():
        if npc_id == "officer":
            continue
        scores[npc_id]      = getattr(npc, "sus", 0.0)
        summaries[npc_id]   = getattr(npc, "running_summary", "")
        lies_caught[npc_id] = getattr(npc, "lies_caught", [])

    return {
        "current_npc":          graph_state.get("current_npc", ""),
        "npc_reply":            graph_state.get("npc_response", ""),
        "search_result":        graph_state.get("search_result", ""),
        "scores":               scores,
        "total_suspicion":      sum(scores.values()),
        "evidence_found":       graph_state.get("evidence_found", []),
        "locations_unlocked":   graph_state.get("locations_unlocked", {}),
        "summaries":            summaries,
        "lies_caught":          lies_caught,
    }


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/start")
def start_game():
    global THREAD, LATEST_STATE

    THREAD = {"configurable": {"thread_id": f"shimla_{int(time.time())}"}}

    result       = garph.invoke(state, config=THREAD)
    LATEST_STATE = result

    return {
        "status":    "game_started",
        "thread_id": THREAD["configurable"]["thread_id"],
        **extract_response(result),
    }


@app.post("/talk")
def talk(request: TalkRequest):
    global LATEST_STATE

    npc_name     = request.npc_name.lower().strip()
    player_input = request.player_input.strip()

    if npc_name not in VALID_NPCS:
        return {"error": "invalid_npc", "message": f"Unknown NPC: {npc_name}"}

    if not player_input:
        return {"error": "empty_input", "message": "player_input cannot be empty."}

    result = garph.invoke(
        Command(
            resume = player_input,
            update = {
                "current_npc":     npc_name,
                "player_input":    player_input,
                "search":          False,
                "search_location": "",
            }
        ),
        config=THREAD
    )
    LATEST_STATE = result

    return {"action": "talk", **extract_response(result)}


@app.post("/search")
def search(request: SearchRequest):
    global LATEST_STATE

    location = request.location.strip()

    if location not in VALID_LOCATIONS:
        return {"error": "invalid_location", "message": f"Unknown location: {location}"}

    result = garph.invoke(
        Command(
            resume = "",
            update = {
                "search":          True,
                "search_location": location,
                "current_npc":     "officer",
                "player_input":    "",
            }
        ),
        config=THREAD
    )
    LATEST_STATE = result

    return {"action": "search", "location_searched": location, **extract_response(result)}


@app.get("/current-situation")
def current_situation():
    npcs = LATEST_STATE.get("npcs", {})

    # Only what the player should see — no internal scores or lie data
    npc_summaries = {
        npc_id: getattr(npc, "running_summary", "No interactions yet.")
        for npc_id, npc in npcs.items()
        if npc_id != "officer"
    }

    return {
        "status":               "current_game_state",
        "evidence_found":       LATEST_STATE.get("evidence_found", []),
        "locations_unlocked":   LATEST_STATE.get("locations_unlocked", {}),
        "npc_summaries":        npc_summaries,
    }
