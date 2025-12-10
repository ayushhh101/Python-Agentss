# {
#   "_id": {
#     "$oid": "6936de6a4ad004c39fc518e7"
#   },
#   "challengeId": "challenge_1733616000000_save25",
#   "userId": "usr_rahul_001",
#   "title": "Save ₹25 today",
#   "description": "Put aside a small amount",
#   "category": "saving",
#   "targetAmountPaise": 2500,
#   "rewardAmountPaise": 2500,
#   "status": "completed",
#   "completedAt": null,
#   "difficulty": "easy",
#   "priority": 5,
#   "isExpired": false,
#   "streakContribution": 1,
#   "completionData": {
#     "actualAmountPaise": 0
#   },
#   "aiGeneratedAt": {
#     "$date": "2025-12-08T14:19:22.814Z"
#   },
#   "dateAssigned": {
#     "$date": "2025-12-08T14:19:22.814Z"
#   },
#   "__v": 0,
#   "createdAt": {
#     "$date": "2025-12-08T14:19:22.823Z"
#   },
#   "updatedAt": {
#     "$date": "2025-12-08T14:19:22.823Z"
#   }
# }
from   agents.llm_main import llm
from pymongo import MongoClient
from agents.json_extractor_two import extract_json_two
import json
from datetime import datetime

def daily_challenge(userId: str):
    client = MongoClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
    db = client["test"]
    analytics = db.weeklybudgets.find_one({"userId": userId, "weekNumber": 49})

    if not analytics:
        raise ValueError(f"No analytics found for user {userId}. Run analytics script first.")

    # Convert Mongo document → JSON string for LLM
    analytics_json = json.dumps(analytics, default=str)
    prompt = f""" 
    You are a daily_saving_challenges_creater agent.
    You will be given the weekly budget of a user in {analytics_json} of current week
    You will 2 fields for each category , eg 
    categories
    Object

    food
    Object
    currentSpentPaise
    235200
    maxBudgetPaise
    235185
    transactionCount
    0
    riskScore
    0
    status
    "safe"

    fuel
    Object
    currentSpentPaise
    0
    maxBudgetPaise
    161488
    transactionCount
    0
    riskScore
    0
    status
    "safe"

    transport
    

    recharge
    

    miscellaneous
    

    entertainment
    

    medical
   

    send_home
    
    You have to compare both fields(currentSpentPaise,maxBudgetPaise) for all categories
    Then you will have to take the top 3 categories for which (currentSpentPaise/maxBudgetPaise) is maximum

    Then take these 3 into account and prepare daily challenge task in 5-6 words 
    Associate a 20-50(mandatory multiple of 5) amount with it 
    {{
        challengeId: String,              // "challenge_1733616000000_save25"
        userId: String,                   // "usr_rahul_001"

        title: String,                    // "Save ₹25 today"
        description: String,              // "Put aside a small amount"
        category: String,                 // "saving"

        type: String,                     // "active" | "completed"
        status: String,                   // "active" | "completed" | "expired"

        icon: String,                     // "checkmark-circle"
        color: String,                    // Tailwind HEX e.g. "#10B981"
        btnText: String,                  // "Done"

        amountPaise: Number,              // 2500 (Always store amounts in paise)
        rewardPaise: Number,              // 2500
        difficulty: String,               // "easy" | "medium" | "hard"
        priority: Number,                 // 1–10

        streakContribution: Number,       // e.g. 1

        isExpired: Boolean,               // false

        // For completed challenges
        completionData: {{
            actualAmountPaise: Number,      // 0 or actual saved amount
            completedAt: Date               // nullable
        }},

        // System metadata
        aiGeneratedAt: Date,
        dateAssigned: Date,
        createdAt: Date,
        updatedAt: Date
        }}


        Now seeing these fields create a schema same and fill values accordingly 
        Return ONLY valid JSON.


"""
    detection = llm.invoke(prompt)
    detection_text = detection.content if hasattr(detection, "content") else str(detection)
    detection_json = extract_json_two(detection_text)
    print(detection_json)
    respy = db.dailychallenges.insert_many(detection_json)
    print("✅ Challenge saved to DB")


    now = datetime.utcnow().isoformat()
    return respy
if __name__=='__main__':
    daily_challenge('usr_rahul_001')