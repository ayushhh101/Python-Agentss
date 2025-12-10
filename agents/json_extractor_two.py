def extract_json_two(text: str):
    """
    Extract the first valid JSON (object or array) from an LLM response.
    Supports nested braces and ignores extra text.
    """
    import json

    start = None
    stack = 0

    for i, ch in enumerate(text):
        if ch == '{' or ch == '[':
            if start is None:
                start = i
            stack += 1
        elif ch == '}' or ch == ']':
            stack -= 1
            if stack == 0 and start is not None:
                candidate = text[start:i + 1].strip()
                try:
                    return json.loads(candidate)
                except Exception:
                    continue

    raise ValueError("No valid JSON found in LLM output.")
