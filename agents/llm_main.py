from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()



GOOGLE_API_KEYS = os.getenv("GOOGLE_API_KEY") 

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.5,
    google_api_key=GOOGLE_API_KEYS  
)