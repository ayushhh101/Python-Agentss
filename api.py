from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import json
from agents.risk_analyzer_agent import analyze_risk_predictions

# speech_to_text removed to avoid whisper error
from sp_text import speech_to_text  

from agents.sms_agent import data_creater
from agents.db_agent_one import mongo_query_agent
from db import save_tx
from main_agent import run_agent_pipeline
from agents.mongo_goal_inserter import process_and_insert_goal
from agents.weeklybudget_updater import update_weekly_budget_analysis
from agents.weeklybudget_generator import create_next_week_budget
# from agents.daily_saving_agent import daily_challenge
from agents.notification import main_notifn


app = FastAPI(title="FinWell Agent API", version="1.0.0")

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Create MongoDB client at module level (reuse connection)
MONGO_URL = "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/"
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["test"]


class AgentQuery(BaseModel):
    userId: str
    query: str
    lang: str = "english"


@app.get("/")
def root():
    print("Server running")
    return {"message": "FinWell Agent API is running"}


# -------------------------------------------------------------------
#  SPEECH → TEXT → TRANSACTION PROCESSOR
# -------------------------------------------------------------------
@app.post("/api/speech_msg")
async def speech_input(
    meta: str = Form(...),
    audio: UploadFile = File(...),
    lang: str = Form(...)
):
    try:
        parsed = json.loads(meta)
        user_id = parsed["userId"]
        timestamp = str(parsed["timestamp"])
        print(user_id)
        # Save uploaded audio
        audio_bytes = await audio.read()
        temp_path = "temp_input_audio.m4a"
        
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # Speech → Text (COMMENTED OUT BECAUSE OF WHISPER ISSUE)
        sms_text = speech_to_text(temp_path, lang)
        print(sms_text)

        # Parse transaction
        result = data_creater(
            user_id=user_id,
            sms_text=sms_text,
            timestamp=timestamp
        )
        print(result)

        # Run query agent
        fin = mongo_query_agent(result)
        print(fin)

        # Save to MongoDB
        response = await save_tx(fin)
        print(response)


        return {"message": "Success", "data": response}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in meta")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing speech input: {str(e)}"
        )


# -------------------------------------------------------------------
#  TEXT QUERY PIPELINE
# -------------------------------------------------------------------
@app.post("/query")
async def handle_query(body: AgentQuery, background_tasks: BackgroundTasks):
    try:
        response =await run_agent_pipeline(body.userId, body.query, body.lang)

        if isinstance(response, dict) and "error" in response:
            raise HTTPException(status_code=400, detail=response["error"])

        # ✅ Use async MongoDB insert
        await db.chats.insert_one({
            "userId": body.userId,
            "query": body.query,
            "lang": body.lang,
            "response": response,
            "timestamp": datetime.utcnow(),
        })

        background_tasks.add_task(
            process_and_insert_goal,
            body.userId,
            body.query,
            response,
            body.lang
        )

        return {"response": response}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server Error: {str(e)}"
        )


# -------------------------------------------------------------------
# WEEKLY BUDGET ANALYSIS
# -------------------------------------------------------------------
class WeeklyBudgetRequest(BaseModel):
    userId: str


@app.post("/api/weekly-budget/analyze")
async def analyze_weekly_budget(body: WeeklyBudgetRequest):
    try:
        result = update_weekly_budget_analysis(body.userId)

        if not result.get("success"):
            raise HTTPException(
                status_code=404 if "No budget found" in result.get("error", "") else 500,
                detail=result.get("error")
            )

        return result

    except Exception as e:
        raise HTTPException(500, f"Error analyzing weekly budget: {str(e)}")


@app.post("/api/weekly-budget/create-next")
async def create_next_weekly_budget(body: WeeklyBudgetRequest):
    try:
        result = create_next_week_budget(body.userId)

        if not result.get("success"):
            code = 409 if "already exists" in result.get("error", "") else 404
            raise HTTPException(status_code=code, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(500, f"Error creating next week's budget: {str(e)}")


# -------------------------------------------------------------------
# DAILY TASK API
# -------------------------------------------------------------------
from fastapi import Query

# @app.get("/api/daily_task")
# async def daily_task_api(userId: str = Query(...)):
#     resp = await daily_challenge(userId)   # ✅ MUST await
#     return {"message": "Successful", "data": resp}



# -------------------------------------------------------------------
# ADMIN BROADCAST NOTIFICATION
# -------------------------------------------------------------------
@app.get("/api/admin/notification")
async def create_notification(msg: str = Query(...)):
    resp = await main_notifn(msg)
    return {"message": "Notification sent", "data": resp}


# -------------------------------------------------------------------
# RISK PREDICTION ANALYZER
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# RISK PREDICTION ANALYZER
# -------------------------------------------------------------------
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize Motor client (add this at the top of your file with other DB connections)
motor_client = AsyncIOMotorClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
motor_db = motor_client["test"]

class RiskAnalysisRequest(BaseModel):
    userId: str

@app.post("/api/risk-analysis/generate")
async def generate_risk_analysis(body: RiskAnalysisRequest):
    """
    Generate comprehensive risk predictions based on last 2 months of financial data.
    Analyzes transactions, weekly budgets, monthly summaries, and user analytics.
    """
    try:
        # Assuming analyze_risk_predictions is async, otherwise await it
        result =  analyze_risk_predictions(body.userId)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404 if "No analytics found" in result.get("error", "") else 500,
                detail=result.get("error")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating risk analysis: {str(e)}")

@app.get("/api/risk-analysis/get")
async def get_risk_analysis(userId: str = Query(...), month: str = Query(None)):
    """
    Retrieve saved risk analysis for a user.
    If month is not provided, returns the latest analysis.
    Month format: YYYY-MM (e.g., "2025-12")
    """
    try:
        query = {"userId": userId}
        if month:
            query["month"] = month
        
        # Get the most recent analysis using Motor
        risk_data = await motor_db.riskpredictions.find_one(
            query,
            sort=[("generatedAt", -1)]
        )
        
        if not risk_data:
            raise HTTPException(
                status_code=404,
                detail=f"No risk analysis found for user {userId}" + (f" in {month}" if month else "")
            )
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in risk_data:
            risk_data["_id"] = str(risk_data["_id"])
        
        return {
            "success": True,
            "data": risk_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error retrieving risk analysis: {str(e)}")