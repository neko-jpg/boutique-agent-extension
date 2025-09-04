import os
import requests
import json
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- Configuration ---
CATALOG_READER_URL = os.environ.get("CATALOG_READER_URL")
if not CATALOG_READER_URL:
    raise RuntimeError("CATALOG_READER_URL environment variable not set.")

try:
    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except KeyError:
    raise RuntimeError("GOOGLE_API_KEY environment variable not set.")


# --- Tool Definition: Functions to interact with the catalog-reader ---

def search_products(query: str) -> str:
    """
    Searches for products based on a query string.
    Args:
        query: The search term (e.g., "black shoes", "kitchenware").
    Returns:
        A JSON string representing a list of products found.
    """
    print(f"TOOL: Searching for products with query: {query}")
    try:
        response = requests.post(f"{CATALOG_READER_URL}/products:search", json={"query": query})
        response.raise_for_status()
        return json.dumps(response.json())
    except requests.exceptions.RequestException as e:
        return f"Error searching for products: {e}"

# Note: The get_product_details tool is available but the prompt will guide the model
# to primarily use the search_products tool for efficiency.
def get_product_details(product_id: str) -> str:
    """
    Gets the detailed information for a single product by its ID.
    Args:
        product_id: The unique identifier of the product.
    Returns:
        A JSON string representing the product's details.
    """
    print(f"TOOL: Getting details for product ID: {product_id}")
    try:
        response = requests.get(f"{CATALOG_READER_URL}/products/{product_id}")
        response.raise_for_status()
        return json.dumps(response.json())
    except requests.exceptions.RequestException as e:
        return f"Error getting product details: {e}"


# --- Generative AI Model Setup ---

SYSTEM_PROMPT = """
You are an expert shopping assistant for the "Online Boutique".
Your primary goal is to help users find products by using the `search_products` tool.
You must respond with a valid JSON object and nothing else.

## Your instructions:
1.  When you receive a query from a user, call the `search_products` tool with a relevant search term from the user's query.
2.  The tool will return a JSON string containing a list of products. You need to process this list.
3.  Your final response to the user MUST be a single JSON object. This object must have one key: "suggestions".
4.  The value of "suggestions" must be a list of JSON objects, where each object represents a product you recommend.
5.  For each product, you must extract the `id`, `name`, and `priceUsd` object from the tool's response.
6.  You must create a new JSON object for each product with the following keys: `sku`, `name`, `price`, `why`.
7.  The `sku` in your output is the `id` from the tool's response.
8.  The `name` in your output is the `name` from the tool's response.
9.  The `price` in your output must be a number, which you will take from the `units` field of the `priceUsd` object.
10. The `why` field is the most important. It must be a short, helpful, and friendly sentence explaining why the product is a good match for the user's original query.

## Example:
IF the user query is "I need some comfortable shoes"
AND you call `search_products("comfortable shoes")`
AND the tool returns this JSON string:
```json
[
  {
    "id": "OLJCESPC7Z",
    "name": "Running Shoes",
    "description": "Comfortable and stylish running shoes.",
    "picture": "...",
    "priceUsd": {
      "currencyCode": "USD",
      "units": "120",
      "nanos": 750000000
    },
    "categories": ["footwear", "running"]
  }
]
```

THEN your final response to the user MUST be this exact JSON object:
```json
{
  "suggestions": [
    {
      "sku": "OLJCESPC7Z",
      "name": "Running Shoes",
      "price": 120,
      "why": "These running shoes are a great choice as they are described as both comfortable and stylish, perfect for your needs."
    }
  ]
}
```
Now, begin.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-pro-latest',
    tools=[search_products, get_product_details],
    system_instruction=SYSTEM_PROMPT
)

# --- Flask API Endpoint ---

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Request body must be JSON with a 'query' field."}), 400

    user_query = data['query']
    print(f"API: Received query: {user_query}")

    chat = model.start_chat(enable_automatic_function_calling=True)

    try:
        response = chat.send_message(user_query)
        # The model should directly return the JSON string as instructed.
        # We need to find the JSON block in the response, as the model might add backticks.
        response_text = response.text.strip()
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise json.JSONDecodeError("No JSON object found in response", response_text, 0)

        json_str = response_text[json_start:json_end]
        final_json_response = json.loads(json_str)
        return jsonify(final_json_response)

    except (json.JSONDecodeError, Exception) as e:
        error_message = f"Failed to get a valid JSON response from the model. Error: {e}. Raw response: {response.text if 'response' in locals() else 'N/A'}"
        print(f"API ERROR: {error_message}")
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
