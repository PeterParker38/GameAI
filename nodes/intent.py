from nodes.gamestate import State
from pydantic import BaseModel
from nodes.llms import speed
from nodes.sus import LOCATION_EVIDENCE
'''from nodes.prompt import intent_prompt'''

keys = list(LOCATION_EVIDENCE.keys())
intent_prompt = f'''
    Role: You are an intent classifier.
    SUSPECTS: arjun, bell, graves.
    SEARCHABLE LOCATIONS: Bedroom, Kitchen, Garden, Study.
    
    OUTPUT (strict JSON only):
{{
  "conversation_with_suspect": true/false,
  "suspect_name": "arjun" | "bell" | "graves" | null,

  "conversation_with_officer": true/false,

  "search_for_evidence": true/false,
  "search_location": one of {keys} or null,

  "accuse_graves": true/false
}}

RULES:
- Return ONLY valid JSON. No extra text.
- Use lowercase for all values.
- If talking to a suspect → set conversation_with_suspect=true and fill suspect_name.
- If talking to officer → set conversation_with_officer=true.
- If searching → set search_for_evidence=true and fill search_location.
- If accusing → set accuse_graves=true.
- If multiple intents appear → choose the most dominant one.
- If unclear → set all fields to false/null.
'''

class intent_engg(BaseModel):
    conversation_with_suspects: bool
    suspect_name: str | None
    conversation_with_officer: bool
    search_for_evidence: bool
    search_location: str | None
    accusing_graves_as_killer: bool

structured_speed = speed.with_structured_output(intent_engg)

def intent(state):
    if(state['current_npc'] != "officer" or state['current_npc'] != ""):
        return "npc"
    elif(state['search']):
        if(state['search_location']!= ""):
            return f"search"
        else:
            return "wrong_location"
    elif(state['accusation_availble']):
        return "acuusation available"
    elif(state['current_npc'] == "officer" or state['current_npc'] == ""):
        return "officer"