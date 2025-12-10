 
# main.py
import pandas as pd
import json

# Import your custom agent creation functions and the LLM instance
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "sms_agent_prompt.txt")

def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


base_prompt = load_prompt()

from agents.llm_main import llm


def data_creater(user_id: str, sms_text: str, timestamp: str):
    """
    Runs the LLM agent using the prompt template stored in prompt.txt.
    """

    # Replace variables inside the prompt
    final_prompt = (
        base_prompt
        .replace("{{msg}}", sms_text)
        .replace("{{userId}}", user_id)
        .replace("{{timestamp}}", timestamp)
    )

        
        
    response = llm.invoke(final_prompt)
    print(response.content)
    return response.content.strip()

if __name__=='__main__':
        data_creater(
            '101',
            'Swiggy CASHBACK Payment received. Rs. 485 credited for 6 deliveries completed today. Daily bonus: Rs. 40 added.',
            '2025-02-01T10:15:22+05:30'
        )

        data_creater(
            '101',
            'Zomato CASHBACK Rs. 610 credited for 7 orders completed. Weekend incentive of Rs. 30 has been added.',
            '2025-02-02T11:18:40+05:30'
        )

        data_creater(
            '101',
            'Amazon Flex CASHBACK Rs. 540 credited to your account for parcel deliveries. Performance bonus: Rs. 20 included.',
            '2025-02-03T15:30:55+05:30'
        )

        data_creater(
            '101',
            'Uber OTHER Trip amount of Rs. 348 has been debited for the ride from Bandra to Andheri. Invoice generated.',
            '2025-02-04T18:22:10+05:30'
        )

        data_creater(
            '101',
            'Account Alert INFO Your weekly activity report is ready. Review your transactions, payouts, and account summary in the app.',
            '2025-02-05T09:44:31+05:30'
        )
