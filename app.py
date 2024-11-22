from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import os
import spacy
from keybert import KeyBERT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load SpaCy and KeyBERT models
nlp = spacy.load("en_core_web_sm")
keybert_model = KeyBERT()

# Define categories
categories = {
    "Ingredients": [],
    "Flavor Enhancers and Sauces": [],
    "Dish type/category": [],
    "Uniquely Created Dish Names by FAN": [],
    "Preparation Technique": [],
    "Dietary Information and Allergens": [],
    "Cuisine Type": [],
    "Other": []
}

def extract_terms(text):
    doc = nlp(text)
    terms = []
    seen_terms = set()

    # Extract compound noun phrases first
    for chunk in doc.noun_chunks:
        compound_phrase = chunk.text.lower()
        terms.append(compound_phrase)
        seen_terms.update(compound_phrase.split())

    # Add single words not in compound phrases
    for token in doc:
        if token.pos_ in {"NOUN", "ADJ"}:
            term = token.text.lower()
            if term not in seen_terms:
                terms.append(term)
                seen_terms.add(term)

    return terms


def classify_terms(terms):
    category_list = ", ".join(categories.keys())
    formatted_terms = ', '.join(f'"{term}"' for term in terms)
    prompt = (
        f"I have the following list of terms: {formatted_terms}. "
        f"Please categorize each term into one of these specific categories: {category_list}. "
        f"If a term doesn't match any, label it as 'Other'. "
        f"Please provide each term and its category in the following format: 'term - category'."
    )

    # OpenAI API call
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that categorizes terms into specific known categories."},
            {"role": "user", "content": prompt}
        ]
    )

    # Parse API response
    if response.choices and response.choices[0].message:
        return response.choices[0].message.content.strip().split("\n")
    else:
        return []


def categorize_extracted_terms(classifications):
    # Clear previous categories
    for key in categories:
        categories[key] = []

    # Categorize terms
    for line in classifications:
        line = line.replace('"', '').replace(",", "").replace(".", "").strip()
        if " - " in line:
            term, category = [part.strip() for part in line.split(" - ", 1)]
            if category in categories:
                categories[category].append(term)
            else:
                categories["Other"].append(term)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({"reply": "No message received."}), 400

        # Step 1: Extract terms
        terms = extract_terms(user_message)

        # Step 2: Classify terms using OpenAI
        classification_result = classify_terms(terms)

        # Step 3: Categorize terms
        categorize_extracted_terms(classification_result)

        # Prepare response
        response = {
            "Extracted Terms": terms,
            "Categorized Terms": categories
        }

        return jsonify({"reply": response})

    except Exception as e:
        return jsonify({"reply": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
