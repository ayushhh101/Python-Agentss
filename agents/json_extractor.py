import json
def extract_json(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return valid JSON:\n{text}")
    return json.loads(text[start:end+1])
