from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder="templates")  # Specify the template folder for HTML
CORS(app)

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    """
    Serve the main HTML page.
    """
    return render_template('index.html')  # Ensure you have templates/index.html

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handle chat requests and return responses from OpenAI's API.
    """
    try:
        # Log the incoming data from the frontend
        data = request.get_json()
        print(f"Received data: {data}")  # Print input from frontend to terminal

        # Get user message
        user_message = data.get('message')
        if not user_message:
            print("No message received from frontend.")
            return jsonify({"reply": "No message received."}), 400

        # Call OpenAI API using the updated syntax
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Use "gpt-3.5-turbo" or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful restaurant chatbot."},
                {"role": "user", "content": user_message},
            ]
        )

        # Extract the chatbot's reply from the response
        bot_reply = response.choices[0].message.content
        print(f"User message: {user_message}")
        print(f"Chatbot reply: {bot_reply}")

        return jsonify({"reply": bot_reply})
    except Exception as e:
        # Log errors to terminal
        print(f"Error occurred: {e}")
        return jsonify({"reply": "An error occurred. Please try again later."}), 500


if __name__ == '__main__':
    app.run(debug=True)
