from agents.llm_main import llm
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

from agents.data_analytics_agent import create_data_analysis_agent

client = AsyncIOMotorClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
db = client["test"]
notifications = db["notifications"]
users_col = db["users"]


def notfn_creater(msg, status_msg, context,lang):
    print(lang)
    """Generate notification JSON (synchronous LLM call)"""
    prompt = f"""
You are a notification-generation assistant.

Context from financial analysis:
{status_msg}

User-specific saving context:
"{context}"

User request:
"{msg}"
EVERYTHING IN Rs, INDIAN CURRENCY 

Task:
1. Create a short, catchy, appealing NOTIFICATION HEADER for the user.
2. Create a warm, simple, helpful 3-4 line notification message.
3. MUST include:
   - a specific recommended savings number
   - a specific safe-to-spend number
LANGUAGE RULE:
- If "{lang}" == "hindi", the **msg_head** and **msg_content** MUST be written entirely in Hindi.
- If "{lang}" != "hindi", output in English.
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
        # Remove markdown code fences if present
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
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


async def planner(msg, userId, user_context,lang):
    """Create and save notification for a single user"""
    
    # Create financial analysis context
    prompt = f"""
    LANGUAGE RULE:
- If "{lang}" == "hindi", the **msg_head** and **msg_content** MUST be written entirely in Hindi.
- If "{lang}" != "hindi", output in English.
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
    notif_json = notfn_creater(msg, analysis, user_context,lang)

    # Save into MongoDB
    doc = {
        "userId": userId,
        "msg_type": "admin_side",
        "msg_head": notif_json["msg_head"],
        "msg_content": notif_json["msg_content"],
        "timestamp": datetime.utcnow()
    }

    result = await notifications.insert_one(doc)
    print(f"✅ Notification created for {userId}: {result.inserted_id}")
    
    return result


async def main_notifn(msg):
    """Main async function to create notifications for all users"""
    
    # Fetch all users
    users = await users_col.find({}).to_list(length=None)
    
    print(f"\n📊 Processing {len(users)} users...")
    
    final_queries = []
    
    for user in users:
        userId = user["userId"]
        lang = user['preferred_language']
        print(lang)
        # Get analytics data (assuming this is sync)
        analytics_data = await create_data_analysis_agent(userId)
        
        # Create and save notification
        mongo_query = await planner(msg, userId, analytics_data,lang)
        final_queries.append(str(mongo_query.inserted_id))

    
    print(f"\n✅ Created {len(final_queries)} notifications")
    return final_queries


if __name__ == "__main__":
    msg = "Make a user notification for how much he should spend this upcoming Diwali according to his current spendings."
    
    # Run the async main function
    final_queries = asyncio.run(main_notifn(msg,"english"))
    
    print("\n--- INSERTED IDs ---")
    print(final_queries)