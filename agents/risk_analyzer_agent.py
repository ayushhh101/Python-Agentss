# risk_analyzer_agent.py

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_main import llm
from pymongo import MongoClient
from datetime import datetime, timedelta
from collections import defaultdict
import json
import traceback


def analyze_risk_predictions(user_id: str):
    """
    Analyzes user's financial data from last 2 months (October-November) 
    and generates risk predictions for the current month (December).
    
    Returns risk analysis with:
    1. High Risk: Categories with abnormal spending patterns
    2. Medium Risk: Near-zero balance predictions
    3. Pattern Detection: Day-wise spending patterns
    4. Predicted Risks Ahead: 3 future risk predictions
    """
    
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
    db = client["test"]
    
    print(f"\n{'='*80}")
    print(f"🔍 RISK ANALYZER AGENT")
    print(f"{'='*80}")
    print(f"👤 User: {user_id}")
    print(f"📅 Analysis Period: Last 2 months (Oct-Nov 2025)")
    print(f"🎯 Prediction Target: December 2025\n")
    
    # ----------------------------
    # 1) Fetch User Analytics
    # ----------------------------
    print("📊 Fetching user analytics...")
    user_analytics = db.useranalytics.find_one({"userId": user_id})
    
    if not user_analytics:
        return {
            "success": False,
            "error": f"No analytics found for user {user_id}"
        }
    
    # ----------------------------
    # 2) Fetch Monthly Summaries (Oct & Nov)
    # ----------------------------
    print("📈 Fetching monthly summaries...")
    monthly_summaries = list(db.monthly_summary.find({
        "userId": user_id,
        "year": 2025,
        "month": {"$in": [10, 11]}
    }).sort("month", 1))
    
    # ----------------------------
    # 3) Fetch Weekly Budgets (Last 8 weeks)
    # ----------------------------
    print("💰 Fetching weekly budgets...")
    eight_weeks_ago = datetime.now() - timedelta(weeks=8)
    weekly_budgets = list(db.weeklybudgets.find({
        "userId": user_id,
        "weekStartDate": {"$gte": eight_weeks_ago}
    }).sort("weekStartDate", 1))
    
    # ----------------------------
    # 4) Fetch Recent Transactions (Last 60 days)
    # ----------------------------
    print("💳 Fetching recent transactions...")
    sixty_days_ago = datetime.now() - timedelta(days=60)
    transactions = list(db.transactions.find({
        "userId": user_id,
        "createdAt": {"$gte": sixty_days_ago.isoformat()}
    }).sort("createdAt", 1))
    
    # ----------------------------
    # 5) Calculate Current Balance
    # ----------------------------
    print("💵 Calculating current balance...\n")
    
    # Get total income and expenses from useranalytics
    monthly_timeseries = user_analytics.get('monthly_timeseries', [])
    
    # Calculate total balance
    total_income = 0
    total_expenses = 0
    
    for month_data in monthly_timeseries:
        total_income += month_data.get('income', 0)
        total_expenses += month_data.get('expenses', 0)
    
    current_balance_paise = total_income - total_expenses
    
    # ----------------------------
    # 6) Prepare Data for AI Analysis
    # ----------------------------
    analysis_data = {
        "current_balance_paise": current_balance_paise,
        "current_balance_rupees": current_balance_paise / 100,
        "user_analytics": {
            "monthly_timeseries": user_analytics.get('monthly_timeseries', []),
            "metrics_summary": user_analytics.get('metrics_summary', {})
        },
        "monthly_summaries": [],
        "weekly_budgets": [],
        "transaction_count": len(transactions),
        "analysis_date": datetime.now().isoformat()
    }
    
    # Add monthly summaries
    for summary in monthly_summaries:
        analysis_data["monthly_summaries"].append({
            "month": summary.get('month'),
            "year": summary.get('year'),
            "incomeExpense": summary.get('summary', {}).get('incomeExpense', []),
            "categoryTotals": summary.get('summary', {}).get('full', {}).get('categoryTotals', []),
            "weekdayWeekend": summary.get('summary', {}).get('full', {}).get('weekdayWeekend', []),
            "biggestSpike": summary.get('summary', {}).get('biggestSpike', {}),
            "topIncomeSlots": summary.get('summary', {}).get('topIncomeSlots', [])
        })
    
    # Add weekly budgets
    for budget in weekly_budgets:
        analysis_data["weekly_budgets"].append({
            "weekNumber": budget.get('weekNumber'),
            "year": budget.get('year'),
            "categories": budget.get('categories', {}),
            "totalSpentPaise": budget.get('totalSpentPaise', 0),
            "totalBudgetPaise": budget.get('totalBudgetPaise', 0),
            "overallRiskScore": budget.get('overallRiskScore', 0),
            "budgetUtilization": budget.get('budgetUtilization', 0)
        })
    
    # Convert to JSON for LLM
    analysis_json = json.dumps(analysis_data, default=str, indent=2)
    
    # ----------------------------
    # 7) AI Analysis Prompt
    # ----------------------------
    RISK_ANALYSIS_PROMPT = f"""
You are a financial risk prediction AI. Analyze user's financial data from last 2 months (Oct-Nov 2025) and predict risks for December 2025.

**USER FINANCIAL DATA:**
{analysis_json}

**CURRENT BALANCE:** ₹{current_balance_paise / 100:.2f}
**CURRENT DATE:** December 10, 2025

**STRICT OUTPUT FORMAT REQUIREMENTS:**

You MUST respond with ONLY a valid JSON object following this EXACT structure. Do NOT add any text before or after the JSON.

**1. HIGH RISK - Format Rules:**
- high_risk_head: MUST be exactly "<Category> spending <X>% above normal" (e.g., "Fuel spending 32% above normal")
- high_risk_description: MUST be exactly "₹<current> spent vs ₹<average> average" (e.g., "₹720 spent vs ₹545 average")
- Use actual category name from data (food, fuel, transport, entertainment, medical, recharge, etc.)
- Calculate percentage as: ((current - average) / average) * 100
- Round percentages to whole numbers

**2. MEDIUM RISK - Format Rules:**
- medium_risk_head: MUST be exactly "Near-zero balance predicted in <X> days" (e.g., "Near-zero balance predicted in 4 days")
- medium_risk_description: MUST be exactly "Based on current spending rate" (keep it simple, no extra text)
- Calculate daily spending rate from recent transactions
- balance_today_rupees: Current balance ({current_balance_paise / 100:.2f})
- balance_plus_2days_rupees: Today's balance - (2 * daily_spending_rate)
- balance_plus_4days_rupees: Today's balance - (4 * daily_spending_rate)
- days_until_zero: How many days until balance reaches ₹350 or less

**3. PATTERN DETECTION - Format Rules:**
- pattern_detected_head: MUST be exactly "You spend more on <DayName>s" (e.g., "You spend more on Sundays")
- pattern_detected_description: MUST be exactly "Average +₹<X> extra every <DayName>" (e.g., "Average +₹180 extra every Sunday")
- Analyze weekdayWeekend data where: 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday, 7=Sunday
- Find the day with highest spending
- Calculate how much extra compared to average day
- highest_spending_day: Full day name (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)

**4. THREE PREDICTED RISKS - Format Rules:**
Each risk MUST have:
- title: Short heading (3-5 words max) like "Income Drop Week" or "Festival Overspend Risk" or "EMI Crunch Period"
- description: One line with specific date/context (e.g., "Dec 1-7 • Based on last 3 months" or "Nov 10-14 • Diwali week")
- riskLevel: EXACTLY one of: "high" OR "medium" OR "low" (lowercase only)

Examples of valid risks:
1. {{"title": "Income Drop Week", "description": "Dec 1-7 • Based on last 3 months", "riskLevel": "high"}}
2. {{"title": "Festival Overspend Risk", "description": "Nov 10-14 • Diwali week", "riskLevel": "high"}}
3. {{"title": "EMI Crunch Period", "description": "Dec 3-7 • Multiple dues", "riskLevel": "high"}}

**MANDATORY JSON STRUCTURE (copy this exactly):**
{{
  "high_risk_head": "Fuel spending 32% above normal",
  "high_risk_description": "₹720 spent vs ₹545 average",
  "high_risk_category": "fuel",
  "normal_spending_rupees": 545,
  "current_spending_rupees": 720,
  
  "medium_risk_head": "Near-zero balance predicted in 4 days",
  "medium_risk_description": "Based on current spending rate",
  "balance_today_rupees": 4850,
  "balance_plus_2days_rupees": 2100,
  "balance_plus_4days_rupees": 350,
  "days_until_zero": 4,
  
  "pattern_detected_head": "You spend more on Sundays",
  "pattern_detected_description": "Average +₹180 extra every Sunday",
  "highest_spending_day": "Sunday",
  "extra_amount_rupees": 180,
  
  "three_predicted_risks": [
    {{
      "title": "Income Drop Week",
      "description": "Dec 1-7 • Based on last 3 months",
      "riskLevel": "high"
    }},
    {{
      "title": "Festival Overspend Risk",
      "description": "Nov 10-14 • Diwali week",
      "riskLevel": "high"
    }},
    {{
      "title": "EMI Crunch Period",
      "description": "Dec 3-7 • Multiple dues",
      "riskLevel": "high"
    }}
  ]
}}

**CRITICAL VALIDATION RULES:**
✓ ALL monetary amounts in RUPEES (divide paise by 100)
✓ NO ₹ symbol in JSON values, only in description strings
✓ Numbers must be actual numbers, not strings (except in description fields)
✓ Day names: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday (capitalize first letter)
✓ Category names: lowercase (food, fuel, transport, etc.)
✓ Risk levels: lowercase only (high, medium, low)
✓ Percentages: whole numbers only (32, not 32.5)
✓ Use ACTUAL data from the provided financial data
✓ Description formats MUST match examples EXACTLY

Respond with ONLY the JSON object. No markdown code blocks, no explanations, no extra text.
"""
    
    print("🤖 Analyzing with AI...\n")
    
    # ----------------------------
    # 8) Get AI Analysis
    # ----------------------------
    try:
        ai_response = llm.invoke(RISK_ANALYSIS_PROMPT)
        
        # Parse AI response
        response_text = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
        
        # Extract JSON from response (try multiple methods)
        json_str = None
        
        # Method 1: Look for JSON code blocks
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_str = response_text.split('```')[1].split('```')[0].strip()
        else:
            # Method 2: Find JSON object boundaries
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1].strip()
            else:
                json_str = response_text.strip()
        
        ai_analysis = json.loads(json_str)
        
        # ----------------------------
        # VALIDATE OUTPUT STRUCTURE
        # ----------------------------
        required_fields = [
            'high_risk_head', 'high_risk_description', 'high_risk_category',
            'normal_spending_rupees', 'current_spending_rupees',
            'medium_risk_head', 'medium_risk_description',
            'balance_today_rupees', 'balance_plus_2days_rupees', 'balance_plus_4days_rupees',
            'days_until_zero',
            'pattern_detected_head', 'pattern_detected_description',
            'highest_spending_day', 'extra_amount_rupees',
            'three_predicted_risks'
        ]
        
        missing_fields = [field for field in required_fields if field not in ai_analysis]
        if missing_fields:
            raise ValueError(f"AI response missing required fields: {missing_fields}")
        
        # Validate three_predicted_risks structure
        if not isinstance(ai_analysis['three_predicted_risks'], list) or len(ai_analysis['three_predicted_risks']) != 3:
            raise ValueError("three_predicted_risks must be an array of exactly 3 items")
        
        for idx, risk in enumerate(ai_analysis['three_predicted_risks']):
            if not all(key in risk for key in ['title', 'description', 'riskLevel']):
                raise ValueError(f"Risk #{idx+1} missing required fields (title, description, riskLevel)")
            if risk['riskLevel'] not in ['high', 'medium', 'low']:
                raise ValueError(f"Risk #{idx+1} has invalid riskLevel: {risk['riskLevel']} (must be high/medium/low)")
        
        print("✅ AI response validated successfully")
        
        # ----------------------------
        # 9) Format Final Result
        # ----------------------------
        current_month = datetime.now().strftime("%Y-%m")
        
        result = {
            "userId": user_id,
            "month": current_month,
            "generatedAt": datetime.utcnow(),
            
            # High Risk
            "high_risk_head": ai_analysis.get('high_risk_head'),
            "high_risk_description": ai_analysis.get('high_risk_description'),
            "high_risk_category": ai_analysis.get('high_risk_category'),
            "normal_spending_rupees": ai_analysis.get('normal_spending_rupees'),
            "current_spending_rupees": ai_analysis.get('current_spending_rupees'),
            
            # Medium Risk
            "medium_risk_head": ai_analysis.get('medium_risk_head'),
            "medium_risk_description": ai_analysis.get('medium_risk_description'),
            "balance_today_rupees": ai_analysis.get('balance_today_rupees'),
            "balance_plus_2days_rupees": ai_analysis.get('balance_plus_2days_rupees'),
            "balance_plus_4days_rupees": ai_analysis.get('balance_plus_4days_rupees'),
            "days_until_zero": ai_analysis.get('days_until_zero'),
            
            # Pattern Detection
            "pattern_detected_head": ai_analysis.get('pattern_detected_head'),
            "pattern_detected_description": ai_analysis.get('pattern_detected_description'),
            "highest_spending_day": ai_analysis.get('highest_spending_day'),
            "extra_amount_rupees": ai_analysis.get('extra_amount_rupees'),
            
            # Predicted Risks
            "three_predicted_risks": ai_analysis.get('three_predicted_risks', [])
        }
        
        # ----------------------------
        # 10) Display Results
        # ----------------------------
        print("="*80)
        print("📊 RISK ANALYSIS RESULTS")
        print("="*80)
        
        print(f"\n🔴 HIGH RISK:")
        print(f"   {result['high_risk_head']}")
        print(f"   {result['high_risk_description']}")
        
        print(f"\n⚠️  MEDIUM RISK:")
        print(f"   {result['medium_risk_head']}")
        print(f"   {result['medium_risk_description']}")
        print(f"   Today: ₹{result['balance_today_rupees']:,.2f}")
        print(f"   +2 days: ₹{result['balance_plus_2days_rupees']:,.2f}")
        print(f"   +4 days: ₹{result['balance_plus_4days_rupees']:,.2f}")
        
        print(f"\n👁️  PATTERN DETECTED:")
        print(f"   {result['pattern_detected_head']}")
        print(f"   {result['pattern_detected_description']}")
        
        print(f"\n⚡ PREDICTED RISKS AHEAD:")
        for idx, risk in enumerate(result['three_predicted_risks'], 1):
            risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk['riskLevel'], "⚪")
            print(f"   {idx}. {risk_emoji} {risk['title']}")
            print(f"      {risk['description']} [{risk['riskLevel'].upper()}]")
        
        print("\n" + "="*80 + "\n")
        
        # ----------------------------
        # 11) Save to MongoDB
        # ----------------------------
        print("💾 Saving to MongoDB...")
        
        db.riskpredictions.update_one(
            {
                "userId": user_id,
                "month": current_month
            },
            {
                "$set": result
            },
            upsert=True
        )
        
        print("✅ Risk analysis saved successfully!\n")
        
        return {
            "success": True,
            "data": result
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing AI response: {e}")
        print(f"\nRaw response:\n{response_text}")
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Failed to parse AI response: {str(e)}"
        }
    
    except Exception as e:
        print(f"❌ Error during risk analysis: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


# ----------------------------
# Local Testing
# ----------------------------
if __name__ == "__main__":
    # Test the agent
    result = analyze_risk_predictions("usr_rahul_001")
    
    if result.get("success"):
        print("\n✅ Test completed successfully!")
    else:
        print(f"\n❌ Test failed: {result.get('error')}")

