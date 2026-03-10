import ollama

def generate_response(messages):
    response = ollama.chat(
        model="phi3:latest",
        messages=messages
    )
    return response["message"]["content"]