from nodes.gamestate import State
from nodes.llms import speed
from nodes.sus import LOCATION_EVIDENCE

keys = list(LOCATION_EVIDENCE.keys())


def intent_node(state: State) -> dict:
    """
    Runs AS A NODE — updates current_npc and pushes player message
    into the correct NPC's chat history before routing happens.
    """
    text = state.get("player_input", "").lower()
    player_input = state.get("player_input", "")

    # Determine target NPC
    if "talk to arjun" in text:
        new_npc = "arjun"
    elif "talk to bell" in text:
        new_npc = "bell"
    elif "talk to graves" in text:
        new_npc = "graves"
    elif "talk to officer" in text:
        new_npc = "officer"
    else:
        new_npc = state.get("current_npc", "officer")

    # Push player message into the correct NPC's chat history
    npcs = state["npcs"]
    npc = npcs[new_npc]
    if npc.chat_history is None:
        npc.chat_history = []
    npc.chat_history.append({"player": player_input})

    return {
        "current_npc": new_npc,
        "npcs": {**npcs, new_npc: npc}
    }


def intent(state: State) -> str:
    """
    Pure routing function — only reads state, never writes to it.
    Returns a plain string matching keys in add_conditional_edges.
    """
    current_npc = state.get("current_npc", "officer")

    if state.get("search") and state.get("search_location", "") != "":
        return "search"

    if state.get("accusation_available"):
        return "accusation_available"

    if current_npc in ("arjun", "bell", "graves"):
        return "npc"

    return "officer"