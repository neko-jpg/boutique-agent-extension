from flask import Flask, request, jsonify, g
import os
import requests
import jwt
from functools import wraps
import datetime

app = Flask(__name__)

# Load the secret key from an environment variable.
# IMPORTANT: In production, this must be a long, random, and securely stored string.
# The default value is insecure and for local development only.
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-insecure-local-dev-key')

RECOMMENDATION_AGENT_URL = os.environ.get("RECOMMENDATION_AGENT_URL", "http://localhost:8081")

# --- JWT Authentication Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check for token in the 'Authorization' header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decode the token using the secret key
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Store the user data in Flask's g object for this request
            g.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)

    return decorated


@app.route('/v1/chat', methods=['POST'])
@token_required
def chat():
    # The user's identity is retrieved from the token by the decorator
    user_id = g.user['user_id']

    data = request.get_json()
    if not data or 'q' not in data:
        return jsonify({"error": "Query 'q' is required."}), 400

    query = data['q']

    try:
        # Forward the request to the recommendation-agent
        response = requests.post(
            f"{RECOMMENDATION_AGENT_URL}/recommend",
            json={"query": query, "userId": user_id}
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to recommendation agent: {e}"}), 503


# --- Token Generation Endpoint (for testing) ---
@app.route('/v1/auth/token', methods=['POST'])
def get_token():
    data = request.get_json()
    if not data or 'userId' not in data:
        return jsonify({'message': 'userId is required in the request body'}), 400

    user_id = data['userId']

    # Create a token that expires in 30 minutes
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
