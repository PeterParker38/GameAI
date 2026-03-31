import json
import re
from nodes.gamestate import State
from nodes.llms import conv
from pydantic import BaseModel, Field


class LLMOutput(BaseModel):
    response: str
    lies_told: list[str] = Field(default_factory=list)


BREAKDOWNS = {
    "graves": [25, 55, 85],
    "bell":   [20, 40, 65],
    "arjun":  [15, 35, 60]
}

STATE_LABELS = {
    "graves": ["composed", "crack", "shaken", "collapse"],
    "bell":   ["defensive", "uneasy", "shaken", "break"],
    "arjun":  ["guarded", "fracture", "shaken", "collapse"]
}

BEHAVIOR_RULES = {
    "graves": {
        "composed":  "calm, controlled, superior tone, answers cleanly",
        "crack":     "irritated, shorter replies, defensive, subtle contradictions",
        "shaken":    "loses composure, partial admissions, fear beneath anger",
        "collapse":  "mask slips, near-confession fragments, emotional fatigue"
    },
    "bell": {
        "defensive": "irritated, sarcastic, dismissive",
        "uneasy":    "over-explains, reacts strongly to poison mentions, defensive",
        "shaken":    "contradictions increase, partial admissions, visible fear",
        "break":     "blurts details, self-preserving, may implicate others"
    },
    "arjun": {
        "guarded":   "hesitant, indirect answers, intellectual tone",
        "fracture":  "anxious, defensive, overexplains",
        "shaken":    "fear visible, partial truth, emotional",
        "collapse":  "admits concealment, emotional breakdown, stops lying"
    }
}


def get_breakdown_state(npc_id, sus):
    if npc_id not in BREAKDOWNS:
        return None
    b1, b2, b3 = BREAKDOWNS[npc_id]
    if sus < b1:   return STATE_LABELS[npc_id][0]
    elif sus < b2: return STATE_LABELS[npc_id][1]
    elif sus < b3: return STATE_LABELS[npc_id][2]
    else:          return STATE_LABELS[npc_id][3]


def _extract_json(raw: str) -> tuple[str, list[str]]:
    """
    Find the LAST valid JSON object in the output (handles models that
    prepend spoken text before the JSON block).
    Strips asterisk action cues from the response field.
    """
    # find all {...} blocks in the output
    candidates = re.findall(r'\{[^{}]*\}', raw, re.DOTALL)

    for block in reversed(candidates):   # last JSON block wins
        try:
            data     = json.loads(block)
            response = data.get("response", "").strip()
            lies     = [l for l in data.get("lies_told", []) if l and l != "..."]
            if response:
                # strip *action cues*
                response = re.sub(r'\*[^*]+\*', '', response).strip()
                return response, lies
        except (json.JSONDecodeError, Exception):
            continue

    # no valid JSON found — strip fences and use raw text
    fallback = re.sub(r"^```(?:json)?", "", raw.strip()).strip()
    fallback = re.sub(r"```$", "", fallback).strip()
    fallback = re.sub(r'\*[^*]+\*', '', fallback).strip()
    return fallback, []


def prompt_response(state: State):
    npc_id = state.get("current_npc")
    if not npc_id or npc_id not in state.get("npcs", {}):
        return {"npc_response": ""}

    npc       = state["npcs"][npc_id]
    chat_hist = npc.chat_history or []

    if not chat_hist:
        return {"npc_response": ""}

    last_msg = chat_hist[-1]
    if "player" not in last_msg:
        return {"npc_response": ""}

    player_message = last_msg["player"]
    running_summ   = npc.running_summary or ""
    retrieved      = getattr(npc, "retrieved_data", "") or ""

    # ── Build prompt ──────────────────────────────────────────────────────────
    if npc_id == "officer":
        prompt_final = f"""
{npc.prompt}

The player said: {player_message}

Respond strictly as the officer. Output ONLY this JSON, nothing before or after it:
{{"response": "your reply here"}}
"""
    else:
        breakdown_state = get_breakdown_state(npc_id, npc.sus)
        if breakdown_state is None:
            return {"npc_response": ""}

        behavior = BEHAVIOR_RULES[npc_id][breakdown_state]

        # inject last 6 exchanges as memory
        history_lines = []
        for entry in chat_hist[-6:]:
            if "player" in entry:
                history_lines.append(f"Player: {entry['player']}")
            if "npc" in entry:
                history_lines.append(f"You replied: {entry['npc']}")
        history_str = "\n".join(history_lines) or "No prior conversation."

        prompt_final = f"""
{npc.prompt}

--- STATE ---
breakdown_state: {breakdown_state}
behavior: {behavior}
sus: {npc.sus}
lies_caught: {npc.lies_caught}
evidence_found: {state.get("evidence_found", [])}

--- CONVERSATION HISTORY (your memory) ---
{history_str}

--- CASE FILE CONTEXT ---
{retrieved or "Nothing retrieved."}

--- INVESTIGATION SUMMARY ---
{running_summ or "No summary yet."}

--- PLAYER SAYS ---
{player_message}

RULES:
- Stay in character per your prompt above
- Do NOT write asterisk action cues like *adjusts spectacles*
- Only list lies you explicitly state right now

Output ONLY this JSON, nothing before or after it:
{{"response": "your spoken dialogue", "lies_told": []}}
"""

    raw_output = conv.invoke(prompt_final).content.strip()
    parsed_response, parsed_lies = _extract_json(raw_output)

    if not parsed_response:
        parsed_response = "..."

    # save reply into chat history
    chat_hist[-1]    = {"player": player_message, "npc": parsed_response}
    npc.chat_history = chat_hist[-6:]

    # record new lies
    if npc_id != "officer":
        for lie in parsed_lies:
            if lie not in npc.lies_told:
                npc.lies_told.append(lie)

    return {
        "npc_response": parsed_response,
        "npcs": {**state["npcs"], npc_id: npc}
    }


print("interaction.py: run successful")