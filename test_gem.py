import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("Initializing client...")
client = genai.Client(api_key=api_key)

models_to_test = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-2.0-flash']

for m in models_to_test:
    try:
        print(f"Testing {m} ...")
        response = client.models.generate_content(
            model=m,
            contents='Hello World'
        )
        print(f"SUCCESS with {m}: {response.text}")
    except Exception as e:
        print(f"FAILED with {m}: {e}")
