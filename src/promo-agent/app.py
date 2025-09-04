import os
import requests
import schedule
import time
import threading
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Configuration ---
CATALOG_READER_URL = os.environ.get("CATALOG_READER_URL")
if not CATALOG_READER_URL:
    raise RuntimeError("CATALOG_READER_URL environment variable not set.")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
if SLACK_WEBHOOK_URL:
    print("Slack webhook URL found. Notifications will be sent to Slack.")
else:
    print("SLACK_WEBHOOK_URL not set. Price drop alerts will only be logged to the console.")

# --- Shared State & Thread Safety ---
# In-memory dictionary to store watched products and their last known prices.
# A lock is used to ensure thread-safe access from the API and background poller.
WATCHED_PRODUCTS = {
    "OLJCESPC7Z": None,  # Running Shoes
    "66VCHSJNUP": None,  # City Bike
    "1YMWWN1N4O": None,  # Kids Tee
}
watchlist_lock = threading.Lock()

# --- Business Logic ---
def send_slack_notification(message: str):
    """Sends a message to the configured Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        return
    try:
        payload = {'text': message}
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("Successfully sent notification to Slack.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack notification: {e}")

def check_product_prices():
    """Polls prices and sends notifications for products in the watchlist."""
    print("--- Background Poller: Checking for price drops... ---")

    with watchlist_lock:
        # Make a copy of the keys to avoid issues with modifying the dict while iterating
        product_ids = list(WATCHED_PRODUCTS.keys())

    for product_id in product_ids:
        try:
            url = f"{CATALOG_READER_URL}/products/{product_id}"
            response = requests.get(url)
            response.raise_for_status()
            product_data = response.json()

            current_price_str = product_data.get('priceUsd', {}).get('units', '0')
            current_price = int(current_price_str)
            product_name = product_data.get('name', 'Unknown Product')

            with watchlist_lock:
                last_price = WATCHED_PRODUCTS.get(product_id)
                print(f"Polling: {product_name} ({product_id}). Current: ${current_price}, Last: ${last_price}")

                if last_price is not None and current_price < last_price:
                    message = (
                        f"🎉 PRICE DROP ALERT! 🎉\n"
                        f"Product: {product_name} ({product_id})\n"
                        f"Old Price: ${last_price}, New Price: ${current_price}"
                    )
                    print("="*50)
                    print(message)
                    print("="*50)
                    send_slack_notification(message)

                WATCHED_PRODUCTS[product_id] = current_price

        except requests.exceptions.RequestException as e:
            print(f"Error fetching product {product_id}: {e}")
        except (KeyError, ValueError) as e:
            print(f"Error parsing price for product {product_id}: {e}")

# --- API Endpoints ---
@app.route('/watchlist', methods=['POST'])
def add_to_watchlist():
    """Adds a product to the watchlist."""
    data = request.get_json()
    if not data or 'product_id' not in data:
        return jsonify({'error': 'product_id is required'}), 400

    product_id = data['product_id']
    with watchlist_lock:
        if product_id not in WATCHED_PRODUCTS:
            WATCHED_PRODUCTS[product_id] = None # Set initial price to None
            print(f"API: Added product {product_id} to watchlist.")
            return jsonify({'message': f'Product {product_id} added to watchlist.'}), 201
        else:
            return jsonify({'message': f'Product {product_id} is already in the watchlist.'}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

# --- Background Scheduler ---
def run_scheduler():
    """Runs the price check scheduler in a loop."""
    print("🚀 Starting background scheduler...")
    schedule.every(1).minutes.do(check_product_prices)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler in a background thread.
# The `daemon=True` flag ensures the thread will exit when the main program exits.
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
print("🚀 Promo Agent API server is running.")
