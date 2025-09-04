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

# In a real application, this would be stored in a persistent database (e.g., Redis, Firestore)
# We are using a simple in-memory dictionary for this demo.
# The key is the product_id, the value is the last known price.
WATCHED_PRODUCTS = {
    "OLJCESPC7Z": None,  # Running Shoes
    "66VCHSJNUP": None,  # City Bike
    "1YMWWN1N4O": None,  # Kids Tee
}

def check_product_prices():
    """
    Checks the prices of products in the WATCHED_PRODUCTS list.
    If a price has dropped, it prints a notification.
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
            # The price is in the 'priceUsd' object under the 'units' key
            current_price_str = product_data.get('priceUsd', {}).get('units', '0')
            current_price = int(current_price_str)

            print(f"Checking product: {product_data.get('name')} ({product_id}). Current price: ${current_price}")

            if last_price is not None:
                # If we have a last known price, check for a drop
                if current_price < last_price:
                    print("="*50)
                    print(f"🎉 PRICE DROP ALERT! 🎉")
                    print(f"Product: {product_data.get('name')} ({product_id})")
                    print(f"Old Price: ${last_price}, New Price: ${current_price}")
                    print("="*50)

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
