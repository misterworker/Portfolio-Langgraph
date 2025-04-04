import requests
import time

API_URL = "http://127.0.0.1:8000"

def chat_with_bot(user_input: str, fingerprint: str, num_rewind: int = 0):
    """Start a conversation with the chatbot."""
    payload = {
        "user_input": user_input,
        "fingerprint": fingerprint,
        "num_rewind": num_rewind
    }

    response = requests.post(f"{API_URL}/chat", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        response = data["response"]
        other = data["other"]
        if other == "interrupt":
            print("Human Review Time!")
            return True
        else:
            print("ASSISTANT:", response)
            return False
    else:
        print("Error:", response.status_code, response.text)
        return False

def resume_conversation(fingerprint: str, action: bool):
    """Resume the conversation if paused for user input."""
    payload = {
        "action": action,
        "fingerprint": fingerprint,
    }

    # Sending the resume decision to the FastAPI app
    response = requests.post(f"{API_URL}/resume", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("ASSISTANT:", data.get("response", "No message from assistant"))
    else:
        print("Error:", response.status_code, response.text)

def wipe_thread(fingerprint: str):
    payload = {
        "fingerprint": fingerprint,
    }
    response = requests.post(f"{API_URL}/wipe", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("ASSISTANT:", data.get("response", "No message from assistant"))
    else:
        print("Error:", response.status_code, response.text)

def interact_with_chatbot():
    """Interact with the chatbot through the FastAPI API."""
    fingerprint = "1"
    user_input = input("You (w to wipe thread): ")
    if user_input == "w":
        wipe_thread(fingerprint)
        return

    conversation_active = chat_with_bot(user_input, fingerprint)

    # If the conversation requires user input to continue, ask the user
    while conversation_active:
        user_decision = input("Do you want to continue? (yes/no): ").strip().lower()

        if user_decision == "yes":
            resume_conversation(fingerprint, True)
        else:
            resume_conversation(fingerprint, False)
            break

        # Check if the conversation has resumed or is done
        conversation_active = chat_with_bot("continue", fingerprint)

while True:
    interact_with_chatbot()
