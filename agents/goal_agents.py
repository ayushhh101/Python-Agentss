import uuid
import json
from datetime import datetime
from agents.llm_main import llm
from agents.json_extractor import extract_json
from bson import ObjectId



def goal_agent_cb(userId: str, query: str, response: str, lang: str):

    # ---- 1. Detect goal ----
    detect_prompt = f"""
    You are a goal detection agent.

    User Query: "{query}"
    Assistant Answer: "{response}"
    Language: "{lang}"

    Rules:

    A “goal” is when the user clearly expresses a personal future intention.

    If NO GOAL → return ONLY:
    {{"is_goal": false}}

    If GOAL → return EXACT JSON:
    {{
        "is_goal": true,
        "type": "<short goal>",
        "description": "<full description>",
        "targetAmountPaise": <number or null>,
        "deadline": "<ISO date(by yourself mandatory)>",
        "icon": "by yourself based on whatever the {query} is  , and icon should be a valid icon from the Ionicons, MaterialCommunityIcons, FontAwesome5 , dont add any prefix , eg. fire , motorbike , cake "
        "color": "choose one ONLY from these EXACT values: 
        #D946EF, #3B82F6, #10B981, #F59E0B, #F43F5E, #6366F1, #F97316, #14B8A6, #EF4444, #84CC16",

        "bg": "you MUST choose the matching pair for the selected color. 
        Allowed pairs ONLY:

        #D946EF → bg-[#4A044E]
        #3B82F6 → bg-[#1E3A8A]
        #10B981 → bg-[#064E3B]
        #F59E0B → bg-[#78350F]
        #F43F5E → bg-[#4C0519]
        #6366F1 → bg-[#1E1B4B]
        #F97316 → bg-[#431407]
        #14B8A6 → bg-[#042F2E]
        #EF4444 → bg-[#450A0A]
        #84CC16 → bg-[#1A2E05]"



        
    }}

    Return ONLY valid JSON.
    """

    detection = llm.invoke(detect_prompt)
    detection_text = detection.content if hasattr(detection, "content") else str(detection)
    detection_json = extract_json(detection_text)

    if not detection_json.get("is_goal"):
        print("Goal Agent: No goal found")
        return None

    # Convert paise → rupees for new schema
    target_rupees = None
    if detection_json.get("targetAmountPaise") is not None:
        target_rupees = detection_json["targetAmountPaise"] / 100

    # ---- 2. Prepare Mongo JSON using NEW SCHEMA ----
    now = datetime.utcnow().isoformat()

    goal_doc = {
        "userId": userId,
        "title": detection_json.get("type"),
        "target": target_rupees,
        "saved": 0,
        "deadline": detection_json.get("deadline"),
        "status": "active",
        "icon": detection_json.get("icon"),
        "color": detection_json.get("color"),
        "bg": detection_json.get('bg'),
        "transactions": [],

        # meta
        "createdAt": now,
        "updatedAt": now
    }

    # ---- 3. Return pure JSON ----
    format_prompt = f"""
    You are a JSON formatter.

    Return ONLY this JSON in a single line.

    JSON:
    {json.dumps(goal_doc, ensure_ascii=False)}
    """

    formatted = llm.invoke(format_prompt)
    formatted_json = formatted.content.strip()

    return formatted_json
