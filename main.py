from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langgraph.types import Command
from build_graph import graph

user_id = "1"

global_config = {"configurable": {"thread_id": "1"}}

def create_prompt(user_type):
    return f"You are an agent called Ethanbot, Ethan's web portfolio manager. You are speaking to {user_type}"

def rewind(num_rewind:int, config, user_input):
    #TODO: fix. essentially need to clear old states instead of appending, which is what update_state seems to do, and also figure out the most effective way to time travel without relying on node type perhaps.
    global graph
    num_encountered = 0
    for state in graph.get_state_history(config):
        if "chatbot" in state.next:
            num_encountered+=1
            if num_rewind == num_encountered:
                config = state.config
                last_message = state.values["messages"][-1]
                print("last message: ", last_message)
                new_message = HumanMessage(
                    content=user_input,
                    id=last_message.id
                )
                graph.update_state(config, {"messages": [new_message]})
                break
    # return config

def stream_graph_updates(user_input: str, user_type: str, user_id: str, num_rewind: int, config: dict):
    state = {
        "messages": [SystemMessage(content=create_prompt(user_type)), {"role": "user", "content": user_input}],
        "user_type": user_type,
        "user_id": user_id,
    }
    if num_rewind != 0:
        rewind(int(num_rewind), config, user_input)
    for event in graph.stream(state, config):
        if "__interrupt__" in event:
            
            action = input("continue or no: ")
            for resume_event in graph.stream(Command(resume={"action": action}), config):
                # print("RESUME_EVENT: ", resume_event)
                try:
                    is_chatbot = resume_event.get("chatbot", False)
                except:
                    is_chatbot = False
                if is_chatbot:
                    msg = resume_event["chatbot"]["messages"][-1].content
                    if msg:
                        print("ASSISTANT:", msg, "\n")

        else:
            for value in event.values():
                # print("Value: ", value)
                msg = value["messages"][-1].content
                if msg:
                    print("ASSISTANT:", msg, "\n")

while True:
    num_rewind = 0
    
    config = global_config

    for state in graph.get_state_history(config):
        print("Num Messages: ", len(state.values["messages"]), "Next: ", state.next)
        print("-" * 80)

    user_input = input("User ('q' to exit, 'e' to edit previous messages): ")

    if user_input.lower() in ["quit", "q"]:
        break

    elif user_input.lower() in ["edit", "e"]:
        num_rewind = input("Number of messages to rewind (num pls): ")
        user_input = input("User: ")

    user_type = input("User Type: ").lower()
    if user_type == "":
        user_type = "viewer"

    stream_graph_updates(user_input, user_type, user_id, num_rewind, config)
