# llm_groq.py
import os
import json

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None

def call_groq_reasoner(prompt: str, model: str = "groq-1"):
    """
    Call Groq model via LangChain wrapper and return text response.
    Raises RuntimeError if Groq client is not available or API key missing.
    """
    if ChatGroq is None:
        raise RuntimeError("langchain_groq.ChatGroq not available. Install 'langchain-groq' and ensure compatibility.")
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    client = ChatGroq(api_key=GROQ_API_KEY, model=model)

    try:
        resp = client.predict(messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=300)
        return resp
    except Exception:
        try:
            gen = client.generate(messages=[{"role": "user", "content": prompt}], temperature=0.0, max_tokens=300)
            if isinstance(gen, dict):
                return gen.get('text') or json.dumps(gen)
            return str(gen)
        except Exception as e:
            raise RuntimeError(f"Groq call failed: {e}")
