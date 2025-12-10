from motor.motor_asyncio import AsyncIOMotorClient
import json

MONGO_URL = "mongodb+srv://mumbaihacks:mumbaihacks@cluster0.fonvcex.mongodb.net/"

client = AsyncIOMotorClient(MONGO_URL)
db = client["test"]
transactions = db["transactions"]
notifications = db["notifications"]


async def save_tx(transaction):
    clean = transaction.strip()

    # Remove parentheses wrapper
    if clean.startswith("(") and clean.endswith(")"):
        clean = clean[1:-1]

    # Parse JSON
    transaction = json.loads(clean)

    # Insert into DB
    result = await transactions.insert_one(transaction)
    print(result)
    print("Inserted ID:", result.inserted_id)

    # -----------------------
    # Build Notification
    # -----------------------
    amount_rupees = transaction["amountPaise"] / 100
    msg_content = transaction['category']

    if transaction["type"] == "income":
        msg_head = f"+₹{amount_rupees}"
    else:
        msg_head = f"-₹{amount_rupees}"

    notif_doc = {
        "msg_type": "transaction",
        "msg_head": msg_head,
        "msg_content": msg_content,
        "userId": transaction.get("userId"),
        "transactionId": str(result.inserted_id)
    }

    notif_result = await notifications.insert_one(notif_doc)
    print("Notification inserted:", notif_result.inserted_id)

    return {"transaction_id": str(result.inserted_id)}