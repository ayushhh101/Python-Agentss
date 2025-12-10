# weeklybudget_updater.py
"""
Module to update weekly budget documents in MongoDB with AI-generated risk scores and status.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_main import llm
from pymongo import MongoClient
from datetime import datetime, timedelta
import json

MONGO_URI = "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/"
DB_NAME = "test"

def get_week_dates(date=None):
    """Get the start and end dates for a week (Monday to Sunday)"""
    if date is None:
        date = datetime.now()
    
    start_of_week = date - timedelta(days=date.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_of_week = start_of_week + timedelta(days=6)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    first_day_of_year = datetime(date.year, 1, 1)
    days_since_year_start = (start_of_week - first_day_of_year).days
    week_number = (days_since_year_start + first_day_of_year.weekday() + 1) // 7 + 1
    
    return {
        'weekStartDate': start_of_week,
        'weekEndDate': end_of_week,
        'weekNumber': week_number,
        'year': date.year
    }


def update_weekly_budget_analysis(user_id: str):
    """
    Fetches current week's budget, analyzes with AI, and updates MongoDB.
    Returns the updated document with AI analysis.
    """
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        weekly_budgets = db.weeklybudgets
        
        # Get current week dates
        current_week = get_week_dates()
        
        # Fetch current week's budget
        current_budget = weekly_budgets.find_one({
            "userId": user_id,
            "weekNumber": current_week['weekNumber'],
            "year": current_week['year']
        })
        
        if not current_budget:
            return {
                "success": False,
                "error": f"No budget found for week {current_week['weekNumber']}, {current_week['year']}",
                "userId": user_id
            }
        
        # Fetch previous 2 weeks for analysis
        previous_budgets = list(weekly_budgets.find({
            "userId": user_id,
            "year": {"$lte": current_week['year']},
            "$or": [
                {"year": {"$lt": current_week['year']}},
                {"year": current_week['year'], "weekNumber": {"$lt": current_week['weekNumber']}}
            ]
        }).sort([("year", -1), ("weekNumber", -1)]).limit(2))
        
        # Prepare data for AI analysis
        analysis_data = {
            "current_week": {
                "weekNumber": current_budget.get('weekNumber'),
                "year": current_budget.get('year'),
                "categories": current_budget.get('categories', {}),
                "totalSpentPaise": current_budget.get('totalSpentPaise', 0),
                "totalBudgetPaise": current_budget.get('totalBudgetPaise', 0),
                "transactionSummary": current_budget.get('transactionSummary', {})
            },
            "previous_weeks": []
        }
        
        for prev_budget in previous_budgets:
            analysis_data["previous_weeks"].append({
                "weekNumber": prev_budget.get('weekNumber'),
                "year": prev_budget.get('year'),
                "categories": prev_budget.get('categories', {}),
                "totalSpentPaise": prev_budget.get('totalSpentPaise', 0),
                "transactionSummary": prev_budget.get('transactionSummary', {})
            })
        
        # Convert to JSON for LLM
        analysis_json = json.dumps(analysis_data, default=str, indent=2)
        
        # AI Analysis Prompt
        ANALYSIS_PROMPT = f"""
You are a financial budget analysis AI. Analyze the current week's spending patterns based on historical data from the previous 2 weeks.

**CURRENT WEEK DATA:**
{analysis_json}

**YOUR TASK:**
For each category (food, fuel, transport, recharge, miscellaneous, entertainment, medical, send_home), analyze:

1. **riskScore** (0-100): Calculate based on:
   - Current spending vs max budget (utilization %)
   - Spending velocity compared to previous weeks
   - Transaction frequency patterns
   - Days remaining in the week
   
   Formula guidelines:
   - 0-50% utilization: riskScore = 0-30 (safe zone)
   - 50-80% utilization: riskScore = 30-60 (watch zone)
   - 80-100% utilization: riskScore = 60-85 (warning zone)
   - Over 100% utilization: riskScore = 85-100 (danger zone)
   - Adjust based on trends from previous weeks

2. **status**: Assign one of:
   - "safe": Under 80% budget, normal spending pattern
   - "warning": 80-100% budget OR unusual spike in spending
   - "over_budget": Exceeded max budget

3. **aiSummary**: Provide a single concise sentence (max 150 characters) summarizing the overall budget health and most critical insight

**CRITICAL RULES:**
- Use ONLY the data provided above
- All amounts are in PAISE (divide by 100 for rupees in summary)
- Be precise with numbers
- Consider spending velocity (how fast money is being spent)
- Account for transaction frequency changes
- Today's date is {datetime.now().strftime('%Y-%m-%d')} (Week: {current_week['weekNumber']})

**OUTPUT FORMAT (JSON):**
{{
  "categories": {{
    "food": {{"riskScore": <number>, "status": "<status>"}},
    "fuel": {{"riskScore": <number>, "status": "<status>"}},
    "transport": {{"riskScore": <number>, "status": "<status>"}},
    "recharge": {{"riskScore": <number>, "status": "<status>"}},
    "miscellaneous": {{"riskScore": <number>, "status": "<status>"}},
    "entertainment": {{"riskScore": <number>, "status": "<status>"}},
    "medical": {{"riskScore": <number>, "status": "<status>"}},
    "send_home": {{"riskScore": <number>, "status": "<status>"}}
  }},
  "aiSummary": "<single line summary here>"
}}

Respond ONLY with the JSON object. No additional text.
"""
        
        # Get AI analysis
        ai_response = llm.invoke(ANALYSIS_PROMPT)
        
        # Parse AI response
        response_text = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
        
        # Extract JSON from response
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_str = response_text.split('```')[1].split('```')[0].strip()
        else:
            json_str = response_text.strip()
        
        ai_analysis = json.loads(json_str)
        
        # Prepare update document
        update_doc = {
            "$set": {
                "aiLastAnalyzed": datetime.utcnow(),
                "aiSummary": ai_analysis['aiSummary']
            }
        }
        
        # Update each category with riskScore and status
        for category, analysis in ai_analysis['categories'].items():
            update_doc["$set"][f"categories.{category}.riskScore"] = analysis['riskScore']
            update_doc["$set"][f"categories.{category}.status"] = analysis['status']
        
        # Update the database
        result = weekly_budgets.update_one(
            {"_id": current_budget["_id"]},
            update_doc
        )
        
        # Fetch the updated document
        updated_budget = weekly_budgets.find_one({"_id": current_budget["_id"]})
        
        # Convert ObjectId to string for JSON serialization
        updated_budget['_id'] = str(updated_budget['_id'])
        
        return {
            "success": True,
            "message": f"Weekly budget analysis updated for week {current_week['weekNumber']}, {current_week['year']}",
            "userId": user_id,
            "weekNumber": current_week['weekNumber'],
            "year": current_week['year'],
            "modifiedCount": result.modified_count,
            "aiSummary": ai_analysis['aiSummary'],
            "categoryAnalysis": ai_analysis['categories'],
            "updatedDocument": updated_budget
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse AI response: {str(e)}",
            "userId": user_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error during analysis: {str(e)}",
            "userId": user_id
        }


if __name__ == "__main__":
    # Test the updater
    result = update_weekly_budget_analysis("usr_rahul_001")
    print(json.dumps(result, indent=2, default=str))
