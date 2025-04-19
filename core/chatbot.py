# core/chatbot.py
from openai import OpenAI
import os

# Set your API key from the environment variable.
#openai.api_key = os.getenv("OPENAI_API_KEY")
#print("Loaded API Key:", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key="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")

def ai_chatbot_response(user_message):
    """
    Call OpenAI's GPT-3.5-turbo API to get a response to the user's message.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and friendly medical assistant chatbot."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7  # Adjust the creativity level as needed.
        )
        # Extract and return the chatbot's reply
        return response.choices[0].message.content
         
    except Exception as e:
        # Log the exception and return a fallback message
        print("OpenAI API error:", e)
        return "Sorry, I'm having trouble generating a response right now. Please try again later."
    