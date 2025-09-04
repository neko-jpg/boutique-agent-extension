import os
import requests
import schedule
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
CATALOG_READER_URL = os.environ.get("CATALOG_READER_URL")
if not CATALOG_READER_URL:
    raise RuntimeError("CATALOG_READER_URL environment variable not set.")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
if SLACK_WEBHOOK_URL:
    print("Slack webhook URL found. Notifications will be sent to Slack.")
else:
    print("SLACK_WEBHOOK_URL not set. Price drop alerts will only be logged to the console.")

# In a real application, this would be stored in a persistent database (e.g., Redis, Firestore)
# We are using a simple in-memory dictionary for this demo.
# The key is the product_id, the value is the last known price.
WATCHED_PRODUCTS = {
    "OLJCESPC7Z": None,  # Running Shoes
    "66VCHSJNUP": None,  # City Bike
    "1YMWWN1N4O": None,  # Kids Tee
}

def send_slack_notification(message: str):
    """Sends a message to the configured Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        return # Do nothing if the webhook is not configured

    try:
        payload = {'text': message}
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("Successfully sent notification to Slack.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack notification: {e}")

def check_product_prices():
    """
    Checks the prices of products in the WATCHED_PRODUCTS list.
    If a price has dropped, it prints a notification and sends it to Slack.
    """
    print("--- Checking for price drops... ---")
    for product_id, last_price in WATCHED_PRODUCTS.items():
        try:
            # Call the catalog-reader service to get the latest product details
            url = f"{CATALOG_READER_URL}/products/{product_id}"
            response = requests.get(url)
            response.raise_for_status()
            product_data = response.json()

            # Extract the current price
            current_price_str = product_data.get('priceUsd', {}).get('units', '0')
            current_price = int(current_price_str)
            product_name = product_data.get('name', 'Unknown Product')

            print(f"Checking product: {product_name} ({product_id}). Current price: ${current_price}")

            if last_price is not None and current_price < last_price:
                # Price has dropped
                message = (
                    f"🎉 PRICE DROP ALERT! 🎉\n"
                    f"Product: {product_name} ({product_id})\n"
                    f"Old Price: ${last_price}, New Price: ${current_price}"
                )
                print("="*50)
                print(message)
                print("="*50)
                send_slack_notification(message)

            # Update the last known price with the current price
            WATCHED_PRODUCTS[product_id] = current_price

        except requests.exceptions.RequestException as e:
            print(f"Error fetching product {product_id}: {e}")
        except (KeyError, ValueError) as e:
            print(f"Error parsing price for product {product_id}: {e}")

def main():
    print("🚀 Promo Agent started. Will check for price drops every minute.")
    # Run the job once at the start
    check_product_prices()

    # Schedule the job to run every minute
    schedule.every(1).minutes.do(check_product_prices)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
