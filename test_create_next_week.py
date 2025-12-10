"""
Test script for Creating Next Week's Budget API
"""

import requests
import json

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/weekly-budget/create-next"

test_user = "usr_rahul_001"

def test_create_next_week_budget():
    """Test the create next week's budget endpoint"""
    
    print("🧪 Testing Create Next Week's Budget API")
    print("=" * 60)
    print(f"\n📍 Endpoint: {ENDPOINT}")
    print(f"👤 User ID: {test_user}\n")
    
    try:
        # Make POST request
        print("📤 Sending request...")
        response = requests.post(
            ENDPOINT,
            json={"userId": test_user},
            headers={"Content-Type": "application/json"}
        )
        
        # Check response status
        print(f"📥 Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ SUCCESS!")
            print("=" * 60)
            print(f"\n📊 New Budget Created:")
            print(f"   Week: {data.get('weekNumber')}, {data.get('year')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Start Date: {data.get('weekStartDate')}")
            print(f"   End Date: {data.get('weekEndDate')}")
            print(f"   Total Budget: ₹{data.get('totalBudgetPaise', 0) / 100:.2f}")
            print(f"   Document ID: {data.get('insertedId')}")
            
            print(f"\n📈 Category Budgets:")
            created_doc = data.get('createdDocument', {})
            categories = created_doc.get('categories', {})
            
            for category, details in categories.items():
                print(f"   • {category.title()}: ₹{details.get('maxBudgetPaise', 0) / 100:.2f} (Spent: ₹{details.get('currentSpentPaise', 0) / 100:.2f})")
            
            print("\n" + "=" * 60)
            print("\n📄 Full Response:")
            print(json.dumps(data, indent=2, default=str))
            
        elif response.status_code == 409:
            print(f"⚠️  CONFLICT: Budget already exists")
            print(response.json())
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(response.json())
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to the server!")
        print("   Make sure FastAPI is running on http://localhost:8000")
        print("\n   Start server with:")
        print("   cd e:\\Finguru_backend_python")
        print("   uvicorn api:app --reload --port 8000")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


if __name__ == "__main__":
    test_create_next_week_budget()
