import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Load the secret API key from your .env file
load_dotenv()

# 2. Initialize the Gemini AI "brain"
llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-fast")

# 3. Ask it a test question
print("Sending test message to Gemini...")
response = llm.invoke("Hello! Are you online and ready to build an autonomous supply chain agent?")

# 4. Print the AI's answer
print("\n--- AI RESPONSE ---")
print(response.content)