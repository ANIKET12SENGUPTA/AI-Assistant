def build_system_prompt(context: str):
    return {
        "role": "system",
        "content": f"""
You are an advanced AI Assistant.

Guidelines:
- Be clear and concise.
- If external context is provided, use it only if relevant.
- If no context is useful, answer normally.
- If you don’t know something, say so honestly.

Context from documents (if any):
{context}
"""
    }