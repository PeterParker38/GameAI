from gamestate.gamestate import State
from database.database_1 import retrieve

def retrieval(state: State):
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    
    last_message = npc.chat_history[-1]  # last message
    message = last_message["content"]
    return {'npc.retrieved_data' : retrieve(message)}

### add the llm file
## install json....



def detect_lie(state: State):
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    
    last_message = npc.chat_history[-1]  # last message
    player_message = last_message["content"]
    
    lies_told = npc.lies_told
    lies_caught = npc.lies_caught
    evidence_found = state.evidence_found
    
    prompt = f"""<s>[INST]
You are a lie detection system for a murder mystery game. 
Respond in JSON only. No explanation. No extra text.

PLAYER MESSAGE:
{player_message}

LIES THE NPC HAS TOLD:
{json.dumps(lies_told, indent=2)}

LIES ALREADY CAUGHT:
{lies_caught}

EVIDENCE THE PLAYER HAS FOUND:
{evidence_found}

TASK:
Determine if the player's message has caught or challenged any of the NPC's lies.
A lie is caught if the player references evidence or information that directly contradicts it.

Respond with exactly this JSON structure:
{{
  "lie_caught": true or false,
  "topic": "the key from lies_told that was caught, or null",
  "reason": "one sentence explanation"
}}
[/INST]"""

    raw = speed.invoke(prompt)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return raw[start:end]   # return JSON string — tool must return string
    except Exception:
        return json.dumps({"lie_caught": False, "topic": None, "reason": "parse error"})