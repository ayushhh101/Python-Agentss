import json
from agents.llm_main import llm
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "db_agent_one_prompt.txt")
# Load mongo-agent prompt
def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

base_prompt = load_prompt()

def mongo_query_agent(tx_string: str):
    """
    Takes transaction JSON dict from sms_agent and returns a MongoDB insertOne query string.
    """
    # Convert dict → pretty JSON string
    final_prompt = base_prompt.replace("{{transaction_json}}", tx_string)

    # Call the LLM
    response = llm.invoke(final_prompt)
    print(response)
    # Return the raw insertOne query (string)
    return response.content
