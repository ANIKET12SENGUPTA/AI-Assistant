chat_history = []

def add_memory(role, content):
    chat_history.append({"role": role, "content": content})

def get_memory():
    return chat_history