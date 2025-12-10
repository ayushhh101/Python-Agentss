from llm_main import llm
from motor.motor_asyncio import AsyncIOMotorClient
from json_extractor_two import extract_json_two
import json
from datetime import datetime
import time

# ✅ Create MongoDB client at module level
MONGO_URL = "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/"
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["test"]


def generate_challenge_id(amount):
    """Generate consistent challengeId format."""
    ts = int(time.time() * 1000)
    return f"challenge_{ts}_save{amount}"


async def daily_challenge(userId: str):
    # -----------------------------
    #  GET WEEKLY ANALYTICS
    # -----------------------------
    analytics = await db.weeklybudgets.find_one({"userId": userId, "weekNumber": 49})

    if not analytics:
        raise ValueError(f"No analytics found for user {userId}. Run analytics script first.")

    analytics_json = json.dumps(analytics, default=str)

    # -----------------------------
    #  LLM PROMPT
    # -----------------------------
    prompt = f"""
You are a daily_saving_challenges_creater agent.

You are given the user's weekly budget in this JSON:
{analytics_json}

Your task:
1. Look at each category → compute (currentSpentPaise / maxBudgetPaise)
2. Pick top 3 most overspent categories
3. Create **3 daily saving challenges**
4. Each challenge must:
   - Have a short title (5–6 words)
   - Amount between 20–50 (multiple of 5)
   - Follow EXACT schema below
   - Amounts must be stored in paise
   - Generate timestamps automatically
   - Return ONLY a JSON array of objects

Challenge Schema to output:
{{
    "challengeId": String,
    "userId": String,

    "title": String,
    "description": String,
    "category": String,

    "type": "active",
    "status": "active",

    "icon": "checkmark-circle",
    "color": "#10B981",
    "btnText": "Done",

    "amountPaise": Number,
    "rewardPaise": Number,

    "difficulty": "easy",
    "priority": Number,

    "streakContribution": 1,
    "isExpired": false,

    "completionData": {{
        "actualAmountPaise": 0,
        "completedAt": null
    }},

    "aiGeneratedAt": Date,
    "dateAssigned": Date,
    "createdAt": Date,
    "updatedAt": Date
}}

Now produce **exactly 3 valid challenge objects** in a JSON list.  
Return **only JSON**, no explanation.
"""

    # -----------------------------
    #  LLM CALL
    # -----------------------------
    detection = llm.invoke(prompt)
    detection_text = detection.content if hasattr(detection, "content") else str(detection)

    try:
        detection_json = extract_json_two(detection_text)
    except Exception as e:
        print("❌ JSON extraction failed:", e)
        print("Raw LLM output:", detection_text)
        raise

    if not isinstance(detection_json, list):
        detection_json = [detection_json]   # Normalize → always list


    # -----------------------------
    #  FIX SCHEMA (IDs, timestamps)
    # -----------------------------
    now = datetime.utcnow()

    final_docs = []
    for doc in detection_json:
        amount_rupees = int(doc.get("amountPaise", 0) / 100)
        doc["challengeId"] = generate_challenge_id(amount_rupees)
        doc["userId"] = userId

        doc["aiGeneratedAt"] = now
        doc["dateAssigned"] = now
        doc["createdAt"] = now
        doc["updatedAt"] = now

        final_docs.append(doc)

    # -----------------------------
    #  INSERT INTO DATABASE
    # -----------------------------
    result = await db.dailychallenges.insert_many(final_docs)

    print("✅ Challenges saved!")
    print("Inserted IDs:", result.inserted_ids)

    # -----------------------------
    #  RETURN SAFE JSON RESPONSE
    # -----------------------------
    return {
        "message": "Daily challenges generated",
        "count": len(result.inserted_ids),
        "insertedIds": [str(i) for i in result.inserted_ids]
    }


# Testing (standalone)
if __name__ == "__main__":
    import asyncio
    
    async def test():
        result = await daily_challenge("usr_rahul_001")
        print(result)
    
    asyncio.run(test())