# data_analysis_agent.py

from   agents.llm_main import llm
from pymongo import MongoClient
import json

def create_data_analysis_agent(user_id: str):
    """
    Fetches precomputed analytics for the given user from MongoDB
    and creates a financial analysis agent that ONLY analyzes that data.
    """

    # ----------------------------
    # 1) Connect to MongoDB
    # ----------------------------
    client = MongoClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
    db = client["test"]
    analytics = db.useranalytics.find_one({"userId": user_id})

    if not analytics:
        raise ValueError(f"No analytics found for user {user_id}. Run analytics script first.")

    # Convert Mongo document → JSON string for LLM
    analytics_json = json.dumps(analytics, default=str)

    # ----------------------------
    # 2) Build agent instructions
    # ----------------------------
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
    - Provide clean rupee-denominated numbers that downstream agents will use.
    - End with: *Final Answer:* followed by your factual summary.

    — USER ANALYTICS DATA START —
    {analytics_json}
    — USER ANALYTICS DATA END —
    """



    # ----------------------------
    # 3) Agent interface
    # ----------------------------
    def agent(query: str):
        """
        You give this agent a question like:
        "Summarize my spending"
        and it answers using UserAnalytics only.
        """
        prompt = AGENT_PREFIX + "\nUser Query: " + query
        result = llm.invoke(prompt)

        if hasattr(result, "content"):
            return result.content

        return str(result)

    return agent
# -----------------------------------------
# Local Testing (run python data_analysis_agent.py)
# -----------------------------------------
if __name__ == "__main__":
    # Test user
    test_user_id = "usr_rahul_001"
    

    # Create the agent
    print("Loading analytics agent...")
    agent = create_data_analysis_agent(test_user_id)

    # Test query
    test_query = "Give me a summary of my financial situation."

    print("\nRunning test query...\n")
    response = agent(test_query)

    print("===== AGENT RESPONSE =====")
    print(response)
    print("==========================")
