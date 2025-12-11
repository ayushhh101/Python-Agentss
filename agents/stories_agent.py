from llm_main import llm
import asyncio
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(
    "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/test?retryWrites=true&w=majority"
)
db = client["test"]


async def ai_story(userId, month):
    """Generate and store AI-powered financial story for a user."""
    
    # Fetch Mongo data
    story_summary = await db.stories.find_one({"userId": userId, "month": month})
    detailed_story_summary = await db.monthly_summary.find_one({"userId": userId, "month": month})

    story_summary = story_summary or {}
    detailed_story_summary = detailed_story_summary or {}

    prompt = f"""
You are an AI agent that generates a financial story for the user.

You are given:
1) story_summary = {story_summary}
2) detailed_story_summary = {detailed_story_summary}

Return ONLY a valid JSON object with fields:
- userId
- month(10 for oct , 11 for november and likewise)
- monthly_summ_head
- monthly_summ_content
- earning_head
- earning_content (2-3 lines , point wise)
- spike_header
- spike_content
- smart_header    ((2-3 lines , point wise))
- smart_content

all content are in paise , convert them in rs by /100
"""

    # LLM CALL
    raw = llm.invoke(prompt).content.strip()

    # CLEAN MARKDOWN CODE FENCES
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    # PARSE JSON
    try:
        story_json = json.loads(cleaned)
        print("\n✅ JSON PARSED SUCCESSFULLY")
    except Exception as e:
        print(f"\n❌ JSON PARSING FAILED: {e}")
        print(f"Cleaned content preview: {cleaned[:200]}...")
        story_json = None

    # FALLBACK JSON
    if not story_json:
        story_json = {
            "userId": userId,
            "month": month,
            "monthly_summ_head": "Story Unavailable",
            "monthly_summ_content": "The system could not generate a story due to formatting issues.",
            "earning_head": "",
            "earning_content": "",
            "spike_header": "",
            "spike_content": "",
            "smart_header": "",
            "smart_content": ""
        }

    # Add timestamp
    story_json["timestamp"] = datetime.utcnow()

    # SAVE TO MONGO
    result = await db.stories_agent.insert_one(story_json)

    print("\n--- AI STORY SAVED SUCCESSFULLY ---")
    print(f"Inserted ID: {result.inserted_id}")
    print(f"User: {story_json['userId']}, Month: {story_json['month']}")
    print(f"Summary: {story_json['monthly_summ_head']}")

    return story_json

if __name__ == "__main__":
    asyncio.run(ai_story("usr_rahul_001", 10))
