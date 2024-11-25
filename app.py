# Standard library imports
import os
import json

# Third-party library imports
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import spacy
from keybert import KeyBERT
from dotenv import load_dotenv
from pymongo import MongoClient
from fuzzywuzzy import fuzz, process

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

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['1024_FAN_RSyst']
synonyms_collection = db['term_synonyms']
allergens_collection = db['allergens']
menu_items_collection = db['menu_items']
ingredients_collection = db['ingredients']
menu_items_ingredients_collection = db['menu_items_ingredients']
flavors_collection = db['flavors_and_sauces']
menu_items_flavors_collection = db['menu_items_flavors_and_sauces']
cuisine_types_collection = db['cuisine_types']
menu_items_cuisine_types_collection = db['menu_items_cuisine_types']
preparation_techniques_collection = db['preparation_techniques']
menu_items_preparation_collection = db['menu_items_preparation_techniques']

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

# Define category mappings
category_mappings = {
    "Ingredients": ("ingredients", "name"),
    "Flavor Enhancers and Sauces": ("flavors_and_sauces", "name"),
    "Dish type/category": ("menu_items", "category"),
    "Uniquely Created Dish Names by FAN": ("menu_items", "name"),
    "Preparation Technique": ("preparation_techniques", "technique_name"),
    "Dietary Information and Allergens": ("allergens", ["allergen_type", "allergen_subtype"]),
    "Cuisine Type": ("menu_items_cuisine_types", "cuisine_type_id"),
    "Other": ("other_collection", "other_field")
}

### Helper Functions

# Extract terms from user input using SpaCy
def extract_terms(text):
    doc = nlp(text)
    terms = []
    seen_terms = set()

    for chunk in doc.noun_chunks:
        compound_phrase = chunk.text.lower()
        terms.append(compound_phrase)
        seen_terms.update(compound_phrase.split())

    for token in doc:
        if token.pos_ in {"NOUN", "ADJ"}:
            term = token.text.lower()
            if term not in seen_terms:
                terms.append(term)
                seen_terms.add(term)

    return terms

# Classify extracted terms into categories
def classify_terms(terms):
    category_list = ", ".join(categories.keys())
    formatted_terms = ', '.join(f'"{term}"' for term in terms)
    prompt = (
        f"I have the following list of terms: {formatted_terms}. "
        f"Please categorize each term into one of these specific categories: {category_list}. "
        f"If a term doesn't match any, label it as 'Other'. "
        f"Please provide each term and its category in the following format: 'term - category'."
    )

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that categorizes terms into specific known categories."},
            {"role": "user", "content": prompt}
        ]
    )

    if response.choices and response.choices[0].message:
        classifications = response.choices[0].message.content.strip().split("\n")
        return classifications
    else:
        return []

# Get synonyms for a given term from MongoDB
def get_synonyms(term):
    entry = synonyms_collection.find_one({"original_term": term})
    if entry and "synonyms" in entry:
        return entry["synonyms"]
    return []

# Map terms to their main form using synonyms
def get_terms_with_main_mapping(collection_name, fields, lookup_collection=None, lookup_field=None):
    synonym_to_main = {}
    terms = set()

    for field in fields if isinstance(fields, list) else [fields]:
        field_terms = db[collection_name].distinct(field) if not lookup_collection else db[lookup_collection].distinct(lookup_field)
        terms.update(field_terms)

    for main_term in terms:
        synonym_to_main[main_term] = main_term
        synonyms = get_synonyms(main_term)
        for synonym in synonyms:
            synonym_to_main[synonym] = main_term

    return list(synonym_to_main.keys()), synonym_to_main

# Fuzzy match helper function with adjustable threshold
def fuzzy_match(term, options, threshold=70):
    matches = process.extractBests(term, options, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
    return [matches[0][0]] if matches else []

# Process extracted terms and match them against categories using fuzzy matching
def process_categories(categories):
    results = {category: [] for category in categories}

    for category, terms in categories.items():
        if category in category_mappings:
            collection_name, fields = category_mappings[category]
            if category == "Cuisine Type":
                lookup_collection, lookup_field = "cuisine_types", "cuisine_type"
                cuisine_terms, synonym_to_main = get_terms_with_main_mapping(collection_name, fields, lookup_collection, lookup_field)
            else:
                cuisine_terms, synonym_to_main = get_terms_with_main_mapping(collection_name, fields)

            for main_term in terms:
                fuzzy_matches = fuzzy_match(main_term, cuisine_terms, threshold=70)
                main_terms_matched = {synonym_to_main.get(match) for match in fuzzy_matches if synonym_to_main.get(match)}

                for term in main_terms_matched:
                    if term not in results[category]:
                        results[category].append(term)

    return results

# Categorize extracted terms based on classifications
def categorize_extracted_terms(classifications):
    for key in categories:
        categories[key] = []

    for line in classifications:
        if " - " in line:
            term, category = line.split(" - ", 1)
            term = term.strip()
            category = category.strip()
            if category in categories:
                categories[category].append(term)
            else:
                categories["Other"].append(term)

# Retrieve menu items based on matched results
def retrieve_menu_items_based_on_final_results(final_results):
    include_menu_item_ids = None
    exclude_menu_item_ids = set()

    if "Dish type/category" in final_results:
        category_names = final_results["Dish type/category"]
        category_menu_items = set(doc["id"] for doc in menu_items_collection.find({"category": {"$in": category_names}}, {"id": 1}))
        include_menu_item_ids = category_menu_items if include_menu_item_ids is None else include_menu_item_ids.intersection(category_menu_items)

    # Additional filtering logic (e.g., allergens, ingredients) goes here

    if include_menu_item_ids is None:
        final_include_criteria = {"id": {"$nin": list(exclude_menu_item_ids)}}
    else:
        final_include_criteria = {"id": {"$in": list(include_menu_item_ids)}}
        if exclude_menu_item_ids:
            final_include_criteria["id"]["$nin"] = list(exclude_menu_item_ids)

    matching_menu_items = list(menu_items_collection.find(final_include_criteria, {"name": 1, "category": 1, "_id": 0}))
    return matching_menu_items

### Flask Routes

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

        terms = extract_terms(user_message)
        classifications = classify_terms(terms)
        categorize_extracted_terms(classifications)
        matched_results = process_categories(categories)

        # Fetch recommended dishes
        recommendations = retrieve_menu_items_based_on_final_results(matched_results)

        response = {
            "Extracted Terms": terms,
            "Categorized Terms": categories,
            "Matched Results": matched_results,
            "Recommendations": recommendations
        }

        return jsonify({"reply": response})
    except Exception as e:
        return jsonify({"reply": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
