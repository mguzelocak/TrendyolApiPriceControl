import os
import requests
import mysql.connector
from datetime import datetime
from typing import List, Dict
import pytz
from dotenv import load_dotenv
import json

class TrendyolPriceController:
    def __init__(self) -> None:
        load_dotenv()  # Load credentials from .env
        
        self.api_key: str = os.getenv("API_KEY")
        self.seller_id: str = os.getenv("SELLER_ID")
        self.mysql_user: str = os.getenv("MYSQL_USER")
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD")
        self.mysql_database: str = os.getenv("MYSQL_DATABASE")
        self.page_size: int = 200

        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }

        self.conn = mysql.connector.connect(
            host="localhost",
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database
        )
        self.cursor = self.conn.cursor()

        self.insert_query: str = """
            INSERT INTO priceTracking (barcode, title, price, created_at)
            VALUES (%s, %s, %s, %s)
        """

    def get_turkey_time(self) -> str:
        """Returns current time in Turkey timezone as string"""
        turkey_tz = pytz.timezone("Europe/Istanbul")
        return datetime.now(turkey_tz).strftime('%Y-%m-%d %H:%M:%S')

    def fetch_all_products(self) -> List[Dict]:
        """Fetch all products from Trendyol API with pagination"""
        products: List[Dict] = []
        current_page = 0
        url = f"https://apigw.trendyol.com/integration/product/sellers/{self.seller_id}/products?page={current_page}&size={self.page_size}&archived=false&onSale=true"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f"Initial request failed: {response.status_code}\n{response.text}")

        json_data = response.json()
        products += json_data.get("content", [])
        total_pages = json_data.get("totalPages", 0)

        while current_page < total_pages:
            current_page += 1
            paged_url = f"https://apigw.trendyol.com/integration/product/sellers/{self.seller_id}/products?page={current_page}&size={self.page_size}&archived=false&onSale=true"
            response = requests.get(paged_url, headers=self.headers)
            if response.status_code == 200:
                products += response.json().get("content", [])
            else:
                print(f"Warning: Failed to fetch page {current_page}. Status {response.status_code}")
                break

        return products

    def store_products(self, products: List[Dict]) -> None:
        """Insert products into MySQL with Turkish timestamp"""
        print(f"\n✅ Inserting {len(products)} products into the database...\n")

        for product in products:
            barcode = product.get("barcode")
            title = product.get("title")
            price = product.get("salePrice")
            created_at = self.get_turkey_time()

            self.cursor.execute(self.insert_query, (barcode, title, price, created_at))
            print(f"📦 {barcode} | {title} | {price} TL")

        self.conn.commit()
        print("\n✅ All products inserted successfully.\n")


    def update_product_price(self, barcode: str, sale_price: float, list_price: float) -> tuple[str, bool]:
        """
        Send a price update to Trendyol. Returns (barcode, salePrice, batch_id, success).
        """
        data = {
            "items": [
                {
                    "barcode": barcode,
                    "salePrice": sale_price,
                    "listPrice": list_price
                }
            ]
        }

        print(f"🔁 Sending price update for {barcode} ({sale_price} TL)...")
        url = f"https://apigw.trendyol.com/integration/inventory/sellers/{self.seller_id}/products/price-and-inventory"
        response = requests.post(url, headers=self.headers, data=json.dumps(data))

        if response.status_code == 200:
            batch_id = response.json().get("batchRequestId")
            return batch_id, True
        else:
            return "", False
        
    def check_batch_status(self, batch_id: str) -> bool:
        """
        Check the status of a price update batch. Returns True if all items are successful.
        """

        url = f"https://apigw.trendyol.com/integration/product/sellers/{self.seller_id}/products/batch-requests/{{batch_id}}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            result = response.json()
            print(f"📦 Batch status for {batch_id}:")
            all_success = True
            for item in result.get("items", []):
                barcode = item["requestItem"].get("barcode")
                status = item["status"]
                print(f"   → {barcode}: {status}")
                if status != "SUCCESS":
                    all_success = False
                    print("     ❌ Reason(s):", item.get("failureReasons", []))
            return all_success
        else:
            print("❌ Failed to retrieve batch status.")
            print("Status Code:", response.status_code)
            print(response.text)
            return False
        
    def close(self) -> None:
        """Close DB connection cleanly"""
        self.cursor.close()
        self.conn.close()


    def run(self) -> None:
        """Main entrypoint to run the entire process"""
        try:
            products = self.fetch_all_products()
            self.store_products(products)
        finally:
            self.close()