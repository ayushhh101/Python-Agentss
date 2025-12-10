# translation_agent.py

from agents.llm_main import llm

def translate_to_hindi(english_text: str):
    """
    A simple translation agent that converts English responses
    into clean, natural Hindi.
    """

    prompt = f"""
    You are a professional translator.

    Your task:
    - Convert the following English text into **fluent, natural, easy-to-read Hindi**.
    - Do NOT add anything extra.
    - Preserve formatting like headings, bullet points, and bold text exactly as they are.

    English Text:
    {english_text}

    Now give ONLY the Hindi translation:
    """

    result = llm.invoke(prompt)
    
    # If result has .content (OpenAI style)
    if hasattr(result, "content"):
        return result.content

    return str(result)
