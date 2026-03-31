from nodes.gamestate import State, state
from nodes.graph import garph_ as graph
from langgraph.types import Command


config = {"configurable": {"thread_id": "session-1"}}


def run(command):
    for _ in graph.stream(command, config=config):
        pass
    state_values = graph.get_state(config).values
    return state_values.get("npc_response", "...")


def get_current_npc():
    return graph.get_state(config).values.get("current_npc", "officer")


print("Type 'quit' to exit.\n")

# Kick the graph to the first interrupt — no input yet, no output yet
for _ in graph.stream(state, config=config):
    pass
'''
# Game loop — every resume runs the full pipeline
while True:
    player_input = input("You: ")
    if player_input.lower() == "quit":
        break
    response = run(Command(resume=player_input))
    current_npc = get_current_npc()
    print(f"\n{current_npc}: {response}\n") 
'''
while True:
    player_input = input("You: ")
    if player_input.lower() == "quit":
        break
    if player_input.lower() == "debug":
        # print memory state for all NPCs
        values = graph.get_state(config).values
        for npc_id, npc in values.get("npcs", {}).items():
            print(f"\n--- {npc_id} ---")
            print(f"  running_summary : {npc.running_summary or '(empty)'}")
            print(f"  chat_history    : {npc.chat_history}")
            print(f"  lies_told       : {npc.lies_told}")
            print(f"  sus             : {npc.sus}")
        continue

    response = run(Command(resume=player_input))
    current_npc = get_current_npc()
    print(f"\n{current_npc}: {response}\n")