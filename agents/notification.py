from agents.llm_main import llm
import json
from datetime import datetime
from pymongo import MongoClient

from agents.data_analytics_agent import create_data_analysis_agent

client = MongoClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
db = client["test"]
notifications = db["notifications"]
users_col = db["users"]


def notfn_creater(msg, status_msg, context):
    prompt = f"""
You are a notification-generation assistant.

Context from financial analysis:
{status_msg}

User-specific saving context:
"{context}"

User request:
"{msg}"
EVERYTHING IN Rs , INDIAN CURRENCY 
Task:
1. Create a short, catchy, appealing NOTIFICATION HEADER for the user.
2. Create a warm, simple, helpful 3–4 line notification message.
3. MUST include:
   - a specific recommended savings number
   - a specific safe-to-spend number

STRICT OUTPUT RULES:
- You MUST return ONLY a JSON dictionary.
- NO markdown, NO backticks, NO explanation.
- JSON format:
{{
  "msg_head": "...",
  "msg_content": "..."
}}

"""

    raw = llm.invoke(prompt).content.strip()

    # ---- SAFE JSON handling ----
    try:
        return json.loads(raw)
    except Exception:
        # Try to extract JSON manually if the model added text
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # Final fallback (to avoid crash)
        return {
            "msg_head": "Festival Spending Update",
            "msg_content": "We could not generate a personalized notification due to a formatting issue."
        }

def planner(msg,userId, user_context):

    # Create financial analysis context
    prompt = f"""
You are a financial analysis assistant.

User monthly & spending context:
"{user_context}"

Task:
Create a 3–5 line bullet summary analyzing:
- spending level (high/moderate/low)
- income stability
- savings capability
- risk of festival overspending

Do NOT generate notification.
Only provide analysis context.
"""
    analysis = llm.invoke(prompt).content.strip()

    # Create final structured output
    notif_json = notfn_creater(msg, analysis, user_context)

    # Save into MongoDB
    doc = {
        "userId": userId,
        "msg_type" : "admin_side",
        "msg_head": notif_json["msg_head"],
        "msg_content": notif_json["msg_content"],
        "timestamp": datetime.utcnow()
    }

    return notifications.insert_one(doc)

def main_notifn(msg):
    users = list(users_col.find({}))
    final_queries = []
    for user in users:
        userId = user["userId"]

        analytics_data = create_data_analysis_agent(userId)

        mongo_query = planner(msg, userId, analytics_data)
        final_queries.append(mongo_query.inserted_id)


if __name__ == "__main__":
    users = list(users_col.find({}))

    msg = "Make a user notification for how much he should spend this upcoming Diwali according to his current spendings."

    final_queries = []

    for user in users:
        userId = user["userId"]

        analytics_data = create_data_analysis_agent(userId)

        mongo_query = planner(msg, userId, analytics_data)
        final_queries.append(mongo_query.inserted_id)

    print(final_queries)
