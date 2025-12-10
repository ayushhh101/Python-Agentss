# data_analysis_agent.py (ASYNC VERSION)

from agents.llm_main import llm
from motor.motor_asyncio import AsyncIOMotorClient
import json
from bson import ObjectId

# ----------------------------
# 1) Connect to MongoDB (Motor)
# ----------------------------
MONGO_URL = "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/"
client = AsyncIOMotorClient(MONGO_URL)
db = client["test"]


def fix_object_id(document):
    """Convert Mongo ObjectId → string for JSON safety."""
    if not document:
        return document

    doc = document.copy()
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


# ---------------------------------------------------------
# CREATE THE DATA ANALYSIS AGENT (ASYNC)
# ---------------------------------------------------------
async def create_data_analysis_agent(user_id: str):
    """
    Async version:
    Fetches precomputed analytics from MongoDB (Motor)
    and builds a financial analysis agent that ONLY analyzes that data.
    """

    # 2) Fetch analytics for user (using async Motor)
    analytics = await db.useranalytics.find_one({"userId": user_id})

    if not analytics:
        raise ValueError(f"No analytics found for user {user_id}. Run analytics script first.")

    analytics = fix_object_id(analytics)

    # Convert Mongo document → JSON string for LLM
    analytics_json = json.dumps(analytics, default=str)

    # 3) Agent prefix instructions
    AGENT_PREFIX = f"""
You are a precise financial data analysis agent.

Your job is ONLY to analyze the user's financial analytics provided below.
Do NOT give advice or recommendations. Do NOT generate a plan. Do NOT mention investments.
Simply extract facts, trends, and numeric insights.

IMPORTANT MONEY RULE:
- All monetary values in the UserAnalytics document are stored in *paise*.
- Before reporting any number, ALWAYS divide it by *100*.
- Output all final monetary values in *₹ (rupees)*.
- Never show paise values.

Use ONLY the data inside the 'UserAnalytics' document.
Never guess or assume anything. If something is missing, clearly say: "Insufficient data."

Your Output MUST:
- Be concise, structured, and factual.
- Use ₹ for all currency formatting.
- Focus only on: income, expenses, savings, top categories, and monthly trends.
- End with: *Final Answer:* followed by your factual summary.

— USER ANALYTICS DATA START —
{analytics_json}
— USER ANALYTICS DATA END —
"""

    # -----------------------------------------
    # 4) Return an async ANALYSIS AGENT function
    # -----------------------------------------
    async def agent(query: str):
        """
        You call this like:
            response = await agent("Summarize my spending")
        """
        prompt = AGENT_PREFIX + "\nUser Query: " + query
        result = llm.invoke(prompt)

        if hasattr(result, "content"):
            return result.content

        return str(result)

    return agent


# -----------------------------------------
# Local Testing (async)
# -----------------------------------------
if __name__ == "__main__":
    import asyncio

    async def test():
        print("Loading analytics agent...")

        agent = await create_data_analysis_agent("usr_rahul_001")

        print("\nRunning test query...\n")
        response = await agent("Give me a summary of my financial situation.")

        print("===== AGENT RESPONSE =====")
        print(response)

    asyncio.run(test())
