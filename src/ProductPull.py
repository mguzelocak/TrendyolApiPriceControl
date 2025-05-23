import requests
import mysql.connector
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Load environment variables from .env file (API keys, DB creds, etc.)
# -------------------------------------------------------------------
load_dotenv()

# Read sensitive credentials from environment variables
api_key = os.getenv("API_KEY")
seller_id = os.getenv("SELLER_ID")
mysql_user = os.getenv("MYSQL_USER")
mysql_password = os.getenv("MYSQL_PASSWORD")
mysql_database = os.getenv("MYSQL_DATABASE")

# -------------------------------------------------------------------
# Set up request parameters for Trendyol product listing API
# -------------------------------------------------------------------
size = 200  # Max number of products per page (Trendyol limit is 200)
url = f"https://apigw.trendyol.com/integration/product/sellers/{seller_id}/products?page=0&size={size}&archived=false&onSale=true"

headers = {
    "Content-Type": "application/json",
    "Authorization": api_key
}

# -------------------------------------------------------------------
# Connect to MySQL database
# -------------------------------------------------------------------
conn = mysql.connector.connect(
    host="localhost",
    user=mysql_user,
    password=mysql_password,
    database=mysql_database
)
cursor = conn.cursor()

# SQL insert statement for saving product data
insert_query = """
    INSERT INTO priceTracking (barcode, title, price, created_at)
    VALUES (%s, %s, %s, %s)
"""

# -------------------------------------------------------------------
# Step 1: Send initial request to Trendyol to get product list
# -------------------------------------------------------------------
response = requests.get(url, headers=headers)

if response.status_code == 200:
    products = response.json().get("content", [])
    pages = response.json().get("totalPages", 0)
    current_page = 0

    # ----------------------------------------------------------------
    # Step 2: Loop through all pages to get the full product list
    # ----------------------------------------------------------------
    while current_page <= pages:
        current_page += 1
        paged_url = f"https://apigw.trendyol.com/integration/product/sellers/{seller_id}/products?page={current_page}&size={size}&archived=false&onSale=true"
        response = requests.get(paged_url, headers=headers)

        if response.status_code == 200:
            products += response.json().get("content", [])
        else:
            print("❌ Failed to fetch products.")
            print("Status Code:", response.status_code)
            print(response.text)
            break

    print(f"✅ {len(products)} products fetched. Inserting into database...\n")

    # ----------------------------------------------------------------
    # Step 3: Loop through all products and insert into MySQL table
    # ----------------------------------------------------------------
    for product in products:
        barcode = product.get("barcode")
        title = product.get("title")
        price = product.get("salePrice")

        # Use Turkey time zone for created_at timestamp
        turkey_tz = pytz.timezone("Europe/Istanbul")
        now_in_tr = datetime.now(turkey_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Insert the product into MySQL
        cursor.execute(insert_query, (barcode, title, price, now_in_tr))

        # Optional: Print each inserted product
        print(f"📦 {barcode} | {title} | {price} TL")

    conn.commit()
    print("\n✅ All products inserted successfully.")

else:
    print("❌ Failed to fetch products on initial request.")
    print("Status Code:", response.status_code)
    print(response.text)

# -------------------------------------------------------------------
# Close MySQL connection
# -------------------------------------------------------------------
cursor.close()
conn.close()