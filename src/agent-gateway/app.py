from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

RECOMMENDATION_AGENT_URL = os.environ.get("RECOMMENDATION_AGENT_URL", "http://localhost:8081")

@app.route('/v1/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'q' not in data:
        return jsonify({"error": "Query 'q' is required."}), 400

    query = data['q']
    user_id = data.get('userId', 'anonymous') # Default user_id

    try:
        # Forward the request to the recommendation-agent
        response = requests.post(
            f"{RECOMMENDATION_AGENT_URL}/recommend",
            json={"query": query, "user_id": user_id}
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to recommendation agent: {e}"}), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
