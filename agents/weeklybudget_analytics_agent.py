# weeklybudget_analytics_agent.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_main import llm
from pymongo import MongoClient
from datetime import datetime, timedelta
import json

def get_week_dates(date=None):
    """Get the start and end dates for a week (Monday to Sunday)"""
    if date is None:
        date = datetime.now()
    
    # Get Monday of the week
    start_of_week = date - timedelta(days=date.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get Sunday of the week
    end_of_week = start_of_week + timedelta(days=6)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Calculate week number
    first_day_of_year = datetime(date.year, 1, 1)
    days_since_year_start = (start_of_week - first_day_of_year).days
    week_number = (days_since_year_start + first_day_of_year.weekday() + 1) // 7 + 1
    
    return {
        'weekStartDate': start_of_week,
        'weekEndDate': end_of_week,
        'weekNumber': week_number,
        'year': date.year
    }

def analyze_weekly_budget(user_id: str, test_mode=True):
    """
    Fetches current week's budget and previous 2 weeks for analysis.
    Uses AI to suggest riskScore and status for each category.
    Returns analyzed data with AI summary.
    """
    
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
    db = client["test"] 
    weekly_budgets = db.weeklybudgets
    
    # Get current week dates
    current_week = get_week_dates()
    print(f"\n📅 Analyzing Week {current_week['weekNumber']}, {current_week['year']}")
    print(f"   {current_week['weekStartDate'].strftime('%Y-%m-%d')} to {current_week['weekEndDate'].strftime('%Y-%m-%d')}\n")
    
    # Debug: Show what we're searching for
    query = {
        "userId": user_id,
        "weekNumber": current_week['weekNumber'],
        "year": current_week['year']
    }
    print(f"🔍 Searching with query: {query}")
    
    # Fetch current week's budget (query by week range instead of exact date)
    current_budget = weekly_budgets.find_one(query)
    
    if not current_budget:
        # Debug: Let's see what's actually in the database
        print(f"❌ No budget found for current week for user {user_id}")
        print("\n🔍 Checking what documents exist for this user...")
        all_budgets = list(weekly_budgets.find({"userId": user_id}).sort([("year", -1), ("weekNumber", -1)]))
        print(f"   Found {len(all_budgets)} total budgets")
        for b in all_budgets[:3]:
            print(f"   - Week {b.get('weekNumber')}, Year {b.get('year')}")
        return None
    
    # Fetch previous 2 weeks for analysis (query by week number)
    previous_budgets = list(weekly_budgets.find({
        "userId": user_id,
        "year": {"$lte": current_week['year']},
        "$or": [
            {"year": {"$lt": current_week['year']}},
            {"year": current_week['year'], "weekNumber": {"$lt": current_week['weekNumber']}}
        ]
    }).sort([("year", -1), ("weekNumber", -1)]).limit(2))
    
    print(f"✅ Found current week budget")
    print(f"✅ Found {len(previous_budgets)} previous weeks for analysis\n")
    
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
    
    for idx, prev_budget in enumerate(previous_budgets):
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
  "aiSummary": "<your detailed but concise summary here>"
}}

Respond ONLY with the JSON object. No additional text.
"""
    
    print("🤖 Analyzing with AI...\n")
    
    # Get AI analysis
    ai_response = llm.invoke(ANALYSIS_PROMPT)
    
    # Parse AI response
    try:
        # Extract JSON from response
        response_text = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
        
        # Try to find JSON in response
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_str = response_text.split('```')[1].split('```')[0].strip()
        else:
            json_str = response_text.strip()
        
        ai_analysis = json.loads(json_str)
        
        # Display results
        print("=" * 80)
        print("📊 WEEKLY BUDGET ANALYSIS RESULTS")
        print("=" * 80)
        print(f"\n👤 User: {user_id}")
        print(f"📅 Week {current_week['weekNumber']}, {current_week['year']}")
        print(f"   ({current_week['weekStartDate'].strftime('%b %d')} - {current_week['weekEndDate'].strftime('%b %d, %Y')})")
        print("\n" + "-" * 80)
        print("CATEGORY ANALYSIS:")
        print("-" * 80)
        
        for category, analysis in ai_analysis['categories'].items():
            current_cat = current_budget['categories'].get(category, {})
            spent = current_cat.get('currentSpentPaise', 0) / 100
            budget = current_cat.get('maxBudgetPaise', 0) / 100
            utilization = (spent / budget * 100) if budget > 0 else 0
            
            status_emoji = {
                'safe': '✅',
                'warning': '⚠️',
                'over_budget': '🔴'
            }.get(analysis['status'], '❓')
            
            print(f"\n{category.upper().replace('_', ' ')}:")
            print(f"  {status_emoji} Status: {analysis['status']}")
            print(f"  📊 Risk Score: {analysis['riskScore']}/100")
            print(f"  💰 Spent: ₹{spent:.2f} / ₹{budget:.2f} ({utilization:.1f}%)")
            print(f"  📝 Transactions: {current_cat.get('transactionCount', 0)}")
        
        print("\n" + "=" * 80)
        print("AI SUMMARY:")
        print("=" * 80)
        print(f"\n{ai_analysis['aiSummary']}\n")
        print("=" * 80)
        
        # In test mode, don't update the database
        if test_mode:
            print("\n🧪 TEST MODE: Results displayed only. No database updates.\n")
            return {
                "current_budget": current_budget,
                "ai_analysis": ai_analysis,
                "test_mode": True
            }
        else:
            # Update the database with AI analysis
            update_doc = {
                "$set": {
                    "aiLastAnalyzed": datetime.now(),
                    "aiSummary": ai_analysis['aiSummary']
                }
            }
            
            # Update each category with riskScore and status
            for category, analysis in ai_analysis['categories'].items():
                update_doc["$set"][f"categories.{category}.riskScore"] = analysis['riskScore']
                update_doc["$set"][f"categories.{category}.status"] = analysis['status']
            
            result = weekly_budgets.update_one(
                {"_id": current_budget["_id"]},
                update_doc
            )
            
            print(f"\n✅ Database updated successfully!")
            print(f"   Modified: {result.modified_count} document(s)\n")
            
            return {
                "current_budget": current_budget,
                "ai_analysis": ai_analysis,
                "updated": True
            }
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing AI response: {e}")
        print(f"\nRaw response:\n{response_text}")
        return None
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test the agent
    result = analyze_weekly_budget("usr_rahul_001", test_mode=True)
