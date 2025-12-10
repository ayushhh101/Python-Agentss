# mongo_goal_inserter.py

import json
from motor.motor_asyncio import AsyncIOMotorClient
from agents.goal_agents import goal_agent_cb

client = AsyncIOMotorClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
db = client["test"]
goals = db["savingsjars"]


async def process_and_insert_goal(userId: str, query: str, response: str, lang: str):

    mongo_json = goal_agent_cb(userId, query, response, lang)

    # Case 1: LLM returns None or empty
    if not mongo_json:
        print("Goal Agent returned nothing → skipping insert.")
        return None

    mongo_json = mongo_json.strip()

    # Step 1 — Parse JSON safely
    try:
        parsed = json.loads(mongo_json)
    except json.JSONDecodeError:
        print("Invalid JSON returned by LLM:", mongo_json)
        return None

    # Step 2 — Detect "no goal" case
    if parsed.get("is_goal") is False:
        print("Goal Agent: No goal detected → skipping insert.")
        return None

    # Step 3 — This is a real goal → insert it
    result = await goals.insert_one(parsed)
    print("Inserted Goal ID:", result.inserted_id)

    return result.inserted_id
