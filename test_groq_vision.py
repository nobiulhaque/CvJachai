import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")

client = Groq(api_key=api_key)

try:
    # A tiny 1x1 base64 transparent GIF disguised as image URL, just to see if the vision model exists
    test_img = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    response = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/gif;base64,{test_img}",
                        },
                    },
                ],
            }
        ]
    )
    print("SUCCESS: Vision Model works:", response.choices[0].message.content)
except Exception as e:
    print("FAILED:", e)
