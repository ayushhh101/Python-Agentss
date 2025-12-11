import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/")
db = client["test"]
useranalytics = db["useranalytics"]


def month_range(year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


async def generate_user_analytics(userId: str, year: int, month: int):

    start, end = month_range(year, month)

    pipeline = [
        { "$match": { "userId": userId } },

        { "$addFields": {
            "month": { "$dateToString": { "format": "%Y-%m", "date": "$timestamp" } },
            "isIncome": { "$eq": ["$type", "income"] },
            "isExpense": { "$eq": ["$type", "expense"] }
        }},

        { "$facet": {

            # ------------------------------------------
            # 1️⃣ Raw monthly aggregates
            # ------------------------------------------
            "raw_monthly_aggregates": [
                { "$match": { "timestamp": { "$gte": start, "$lt": end } } },
                { "$group": {
                    "_id": "$month",
                    "totalIncome": { "$sum": {
                        "$cond": ["$isIncome", "$amountPaise", 0]
                    }},
                    "totalExpenses": { "$sum": {
                        "$cond": ["$isExpense", "$amountPaise", 0]
                    }},
                    "transactionCount": { "$sum": 1 },
                    "categories": {
                        "$push": {
                            "category": "$category",
                            "amountPaise": "$amountPaise",
                            "type": "$type"
                        }
                    }
                }},
                { "$sort": { "_id": 1 } }
            ],

            # ------------------------------------------
            # 2️⃣ Monthly Timeseries
            # ------------------------------------------
            "monthly_timeseries": [
                { "$group": {
                    "_id": "$month",
                    "income": {
                        "$sum": { "$cond": ["$isIncome", "$amountPaise", 0] }
                    },
                    "expenses": {
                        "$sum": { "$cond": ["$isExpense", "$amountPaise", 0] }
                    },
                    "savings": {
                        "$sum": {
                            "$cond": [
                                ["$isIncome"],
                                "$amountPaise",
                                { "$multiply": ["$amountPaise", -1] }
                            ]
                        }
                    },
                    "transactionCount": { "$sum": 1 }
                }},
                { "$sort": { "_id": 1 } },
                { "$project": {
                    "month": "$_id",
                    "income": 1,
                    "expenses": 1,
                    "savings": 1,
                    "transactionCount": 1,
                    "_id": 0
                }}
            ],

            # ------------------------------------------
            # 3️⃣ Category totals
            # ------------------------------------------
            "categorySummary": [
                { "$group": { "_id": "$category", "total": { "$sum": "$amountPaise" } } },
                { "$sort": { "total": -1 } }
            ],

            # ------------------------------------------
            # 4️⃣ Sources
            # ------------------------------------------
            "sources": [
                { "$group": { "_id": "$source" } },
                { "$project": { "_id": 0, "source": "$_id" } }
            ],

            # ------------------------------------------
            # 5️⃣ Income Metrics (avg / min / max)
            # ------------------------------------------
            "incomeMetrics": [
                { "$group": {
                    "_id": "$month",
                    "totalIncome": { "$sum": {
                        "$cond": ["$isIncome", "$amountPaise", 0]
                    }}
                }},
                { "$group": {
                    "_id": None,
                    "avgMonthlyIncome": { "$avg": "$totalIncome" },
                    "minMonthlyIncome": { "$min": "$totalIncome" },
                    "maxMonthlyIncome": { "$max": "$totalIncome" }
                }}
            ],

            # ------------------------------------------
            # 6️⃣ Expense Metrics
            # ------------------------------------------
            "expenseMetrics": [
                { "$group": {
                    "_id": "$month",
                    "totalExpenses": { "$sum": {
                        "$cond": ["$isExpense", "$amountPaise", 0]
                    }}
                }},
                { "$group": {
                    "_id": None,
                    "avgMonthlyExpenses": { "$avg": "$totalExpenses" }
                }}
            ],

            # ------------------------------------------
            # 7️⃣ Savings Metrics
            # ------------------------------------------
            "savingsMetrics": [
                { "$group": {
                    "_id": "$month",
                    "savings": {
                        "$sum": {
                            "$cond": [
                                ["$isIncome"],
                                "$amountPaise",
                                { "$multiply": ["$amountPaise", -1] }
                            ]
                        }
                    }
                }},
                { "$group": {
                    "_id": None,
                    "avgMonthlySavings": { "$avg": "$savings" },
                    "bestMonthSavings": { "$max": "$savings" },
                    "worstMonthSavings": { "$min": "$savings" }
                }}
            ]
        }},

        # --------------------------------------------------------
        # Merge facet outputs into a single analytics document
        # --------------------------------------------------------
        { "$project": {
            "raw_monthly_aggregates": 1,
            "monthly_timeseries": 1,
            "sources": "$sources.source",
            "metrics_summary": {
                "income": { "$arrayElemAt": ["$incomeMetrics", 0] },
                "expenses": { "$arrayElemAt": ["$expenseMetrics", 0] },
                "savings": { "$arrayElemAt": ["$savingsMetrics", 0] }
            }
        }}
    ]

    analytics = await db.transactions.aggregate(pipeline).to_list(None)
    analytics_doc = analytics[0]

    # Metadata fields
    analytics_doc["userId"] = userId
    analytics_doc["createdAt"] = datetime.utcnow()
    analytics_doc["lastAnalyticsUpdatedAt"] = datetime.utcnow()

    # Store in useranalytics
    await useranalytics.insert_one(analytics_doc)

    print("\n🌟 User analytics stored successfully!")
    return analytics_doc



# ------------------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------------------
async def main():
    await generate_user_analytics("usr_rahul_001", 2025, 10)


if __name__ == "__main__":
    asyncio.run(main())
