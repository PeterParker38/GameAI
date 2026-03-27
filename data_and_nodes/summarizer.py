from llms import speed
from data_and_nodes.gamestate import state as global_state


SUMMARY_PROMPT = f"""You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff. Do NOT start with "The player". Be direct and factual.

Examples:
"Bell denied poisoning Thorne but became defensive when aconite was mentioned."
"Arjun appeared anxious when page 42 was brought up."
"Mrs. Graves stayed calm and redirected questions about the pantry."
"""


def summarization_node(global_state):
    npc_name = global_state['current_npc']
    npc = global_state['npcs'][npc_name]
    chat_history = npc['chat_history']
    
    """
        chat history must be stored like 
            chat_history = [
                {"player": "Where were you?", "npc": "I was at the library."},
                {"player": "With who?",        "npc": "Alone, I swear."},
            ]
    """
    
    lastchat = chat_history[-1]
    player_input = lastchat['player']
    npc_response = lastchat['npc']
    
    prompt_edited = f"""
    {SUMMARY_PROMPT}
    \n\n
    
    Here is the data: 
    NPC: {npc_name}
    Player said: {player_input}
    NPC replied: {npc_response}

    Write the one-line summary now:

    """

    response = speed.invoke(prompt_edited)

    summary_line = response.content
    old_summary = npc["running_summary"]
    new_summary = old_summary+ summary_line
    npc['running_summary'] = new_summary
    return {'npcs':
            {
                npc_name: npc
            }
    }