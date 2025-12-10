import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient


client = AsyncIOMotorClient(
    "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/test?retryWrites=true&w=majority"
)

db = client["test"]

# --------------------------------------------------------------------------------
# 1️⃣ TOTAL EARNINGS & EXPENSES FOR OCTOBER
# --------------------------------------------------------------------------------
async def get_total_income_expense_oct(userId: str,mon):
    start = datetime(2025, mon, 1)
    end = datetime(2025,mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "timestamp": {"$gte": start, "$lt": end}
        }},
        {"$group": {
            "_id": "$type",
            "totalAmount": {"$sum": "$amountPaise"}
        }}
    ]

    return await db.transactions.aggregate(pipeline).to_list(None)


# --------------------------------------------------------------------------------
# 2️⃣ COMPARE OCTOBER VS SEPTEMBER (Income change %)
# --------------------------------------------------------------------------------
async def compare_oct_vs_sep(userId: str,mon):
    sep_start = datetime(2025, mon-1, 1)
    sep_end = datetime(2025, mon, 1)
    oct_start = datetime(2025, mon, 1)
    oct_end = datetime(2025, mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "type": "income",
            "timestamp": {"$gte": sep_start, "$lt": oct_end}
        }},
        {"$group": {
            "_id": {
                "month": {"$month": "$timestamp"},
                "year": {"$year": "$timestamp"}
            },
            "totalIncome": {"$sum": "$amountPaise"}
        }},
        {"$sort": {"_id.month": 1}}
    ]

    data = await db.transactions.aggregate(pipeline).to_list(None)
    sep_income = next((d["totalIncome"] for d in data if d["_id"]["month"] == 10), 0)
    oct_income = next((d["totalIncome"] for d in data if d["_id"]["month"] == 11), 0)

    change = ((oct_income - sep_income) / sep_income * 100) if sep_income > 0 else 0

    return {
        "September": sep_income / 100,
        "October": oct_income / 100,
        "PercentChange": change
    }


# --------------------------------------------------------------------------------
# 3️⃣ BIGGEST SPIKE CATEGORY + % OF TOTAL SPENDING
# --------------------------------------------------------------------------------
async def get_biggest_spike_category_oct(userId: str,mon):
    start = datetime(2025, mon, 1)
    end = datetime(2025, mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "type": "expense",
            "timestamp": {"$gte": start, "$lt": end}
        }},
        {"$group": {
            "_id": None,
            "totalSpending": {"$sum": "$amountPaise"},
            "categories": {"$push": {"category": "$category", "amount": "$amountPaise"}}
        }},
        {"$unwind": "$categories"},
        {"$project": {
            "category": "$categories.category",
            "amount": "$categories.amount",
            "percent": {
                "$multiply": [
                    {"$divide": ["$categories.amount", "$totalSpending"]}, 100
                ]
            }
        }},
        {"$sort": {"amount": -1}},
        {"$limit": 1}
    ]

    data = await db.transactions.aggregate(pipeline).to_list(None)
    if not data:
        return None

    top = data[0]

    return {
        "category": top["category"],
        "amount": top["amount"] / 100,
        "percent": top["percent"]
    }


# --------------------------------------------------------------------------------
# 4️⃣ WEEKDAY VS WEEKEND PERFORMANCE + BEST TIME SLOT
# --------------------------------------------------------------------------------
async def get_weekday_weekend_insights_oct(userId: str,mon):
    start = datetime(2025, mon, 1)
    end = datetime(2025, mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "type": "income",
            "timestamp": {"$gte": start, "$lt": end}
        }},
        {"$project": {
            "amountPaise": 1,
            "dayOfWeek": {"$dayOfWeek": "$timestamp"},
            "hour": {"$hour": "$timestamp"}
        }},
        {"$group": {
            "_id": {"day": "$dayOfWeek", "hour": "$hour"},
            "total": {"$sum": "$amountPaise"}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 5}
    ]

    return await db.transactions.aggregate(pipeline).to_list(None)


# --------------------------------------------------------------------------------
# 4B️⃣ SATURDAY EVENINGS (5–9 PM)
# --------------------------------------------------------------------------------
async def get_saturday_evening_income_oct(userId: str,mon):
    start = datetime(2025, mon, 1)
    end = datetime(2025, mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "type": "income",
            "timestamp": {"$gte": start, "$lt": end}
        }},
        {"$project": {
            "amountPaise": 1,
            "day": {"$dayOfWeek": "$timestamp"},
            "hour": {"$hour": "$timestamp"}
        }},
        {"$match": {
            "day": 7,
            "hour": {"$gte": 17, "$lte": 21}
        }},
        {"$group": {
            "_id": None,
            "totalSatEvenings": {"$sum": "$amountPaise"}
        }}
    ]

    data = await db.transactions.aggregate(pipeline).to_list(None)
    return data[0]["totalSatEvenings"] / 100 if data else 0


# --------------------------------------------------------------------------------
# 5️⃣ FULL FACET MONTHLY SUMMARY
# --------------------------------------------------------------------------------
async def get_full_monthly_summary_oct(userId: str,mon):
    start = datetime(2025, mon, 1)
    end = datetime(2025, mon+1, 1)

    pipeline = [
        {"$match": {
            "userId": userId,
            "timestamp": {"$gte": start, "$lt": end}
        }},
        {"$addFields": {
            "dayOfWeek": {"$dayOfWeek": "$timestamp"},
            "hour": {"$hour": "$timestamp"}
        }},
        {"$facet": {
            "income": [
                {"$match": {"type": "income"}},
                {"$group": {"_id": None, "total": {"$sum": "$amountPaise"}}}
            ],
            "expense": [
                {"$match": {"type": "expense"}},
                {"$group": {"_id": None, "total": {"$sum": "$amountPaise"}}}
            ],
            "categoryTotals": [
                {"$group": {"_id": "$category", "total": {"$sum": "$amountPaise"}}},
                {"$sort": {"total": -1}}
            ],
            "weekdayWeekend": [
                {"$group": {"_id": "$dayOfWeek", "total": {"$sum": "$amountPaise"}}}
            ],
            "hourly": [
                {"$group": {
                    "_id": {"day": "$dayOfWeek", "hour": "$hour"},
                    "total": {"$sum": "$amountPaise"}
                }},
                {"$sort": {"total": -1}}
            ]
        }}
    ]

    result = await db.transactions.aggregate(pipeline).to_list(None)
    return result[0] if result else {}


# --------------------------------------------------------------------------------
# 6️⃣ SAVE FULL SUMMARY INTO MONGO
# --------------------------------------------------------------------------------
async def save_monthly_summary(userId: str,mon):
    summary_doc = {
        "userId": userId,
        "year": 2025,
        "month": mon,
        "generatedAt": datetime.utcnow(),
        "summary": {
            "incomeExpense": await get_total_income_expense_oct(userId,mon),
            "compareMonth": await compare_oct_vs_sep(userId,mon),
            "biggestSpike": await get_biggest_spike_category_oct(userId,mon),
            "topIncomeSlots": await get_weekday_weekend_insights_oct(userId,mon),
            "saturdayEvening": await get_saturday_evening_income_oct(userId,mon),
            "full": await get_full_monthly_summary_oct(userId,mon)
        }
    }

    await db.monthly_summary.insert_one(summary_doc)
    return summary_doc


# --------------------------------------------------------------------------------
# RUN EVERYTHING
# --------------------------------------------------------------------------------
async def main():
    user = "usr_rahul_001"
    result = await save_monthly_summary(user,11)
    print("Summary Saved:\n", result)


if __name__ == "__main__":
    asyncio.run(main())
