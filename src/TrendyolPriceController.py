import os
import requests
import mysql.connector
from datetime import datetime
from typing import List, Dict
import pytz
from dotenv import load_dotenv
import json
import pandas as pd
from pandas import DataFrame
from zeep import Client

class TrendyolPriceController:
    """
    A controller class for automating product tracking and price updates 
    between Trendyol and Hepsiburada, with MySQL storage and pandas-based analysis.

    Responsibilities:
    - Fetch and store product listings from Trendyol API
    - Update product prices on Trendyol
    - Monitor update statuses using batch IDs
    - Load historical data from MySQL into pandas DataFrames
    - Match and merge product data between Trendyol and Hepsiburada
    """
    def __init__(self) -> None:
        """
        Initializes the TrendyolPriceController by:
        - Loading environment variables from .env
        - Setting up API headers
        - Establishing a MySQL database connection
        - Preparing an SQL query for inserting product data
        """
        load_dotenv()  # Load credentials from .env
        
        self.api_key: str = os.getenv("API_KEY")
        self.seller_id: str = os.getenv("SELLER_ID")
        self.mysql_user: str = os.getenv("MYSQL_USER")
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD")
        self.mysql_database: str = os.getenv("MYSQL_DATABASE")
        self.uye_kodu: str = os.getenv("UYE_KODU")
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
        """
        Returns the current timestamp as a string in Europe/Istanbul timezone.

        Returns:
            str: Timestamp formatted as '%Y-%m-%d %H:%M:%S'
        """
        turkey_tz = pytz.timezone("Europe/Istanbul")
        return datetime.now(turkey_tz).strftime('%Y-%m-%d %H:%M:%S')

    def fetch_all_products(self) -> List[Dict]:
        """
        Fetches all active, non-archived products from the Trendyol API 
        using pagination.

        Returns:
            List[Dict]: A list of product dictionaries with attributes 
                        like barcode, title, salePrice, etc.
        Raises:
            Exception: If the initial API request fails.
        """
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
        """
        Inserts a list of product dictionaries into the MySQL `priceTracking` table
        with Turkish timezone timestamps.

        Args:
            products (List[Dict]): List of Trendyol product dictionaries
        """
        print(f"\n✅ Inserting {len(products)} products into the database...\n")

        for product in products:
            barcode = product.get("barcode")
            title = product.get("title")
            price = product.get("salePrice")
            created_at = self.get_turkey_time()

            self.cursor.execute(self.insert_query, (barcode, title, price, created_at))

        self.conn.commit()
        print("\n✅ All products inserted successfully.\n")


    def store_fake_data(self, products: List[Dict]) -> None:
        """
        Inserts a list of product dictionaries into the MySQL `priceTracking` table
        with Turkish timezone timestamps.

        Args:
            products (List[Dict]): List of Trendyol product dictionaries
        """
        print(f"\n✅ Inserting {len(products)} products into the database...\n")

        for product in products:
            barcode = product.get("barcode")
            title = product.get("title")
            price = product.get("salePrice")
            # created_at = self.get_turkey_time()
            for i in range(1, 31):
                created_at = f"2025-04-{i} 00:00:01"
                self.cursor.execute(self.insert_query, (barcode, title, price, created_at))

            # self.cursor.execute(self.insert_query, (barcode, title, price, created_at))
            # print(f"📦 {barcode} | {title} | {price} TL")

        self.conn.commit()
        print("\n✅ All products inserted successfully.\n")

    def update_product_price(self, barcode: str, sale_price: float, list_price: float) -> tuple[str, bool]:
        """
        Sends a price update request to the Trendyol API for a single product.

        Args:
            barcode (str): The product's barcode.
            sale_price (float): New sale price to update.
            list_price (float): New list price to update.

        Returns:
            tuple[str, bool]: (batch_id, success status)
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
        
    def fetch_data_by_range(self, days: int) -> DataFrame:
        """
        Fetches data from the MySQL `priceTracking` table for the last `days` days.

        Args:
            days (int): Number of days to look back.

        Returns:
            pandas.DataFrame: DataFrame containing the filtered data.
        """

        query = f"""
            SELECT * FROM priceTracking
            WHERE created_at >= CURDATE() - INTERVAL {days-1} DAY
            AND created_at < CURDATE() + INTERVAL 1 DAY;
        """

        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        df = pd.DataFrame(columns=["id", "barcode", "title", "price", "created_at"])

        for row in rows:
            df.loc[len(df)] = [row[0], row[1], row[2], row[3], row[4]]

        return df
    
    def fetch_data_by_month_year(self, month: int, year: int) -> DataFrame:
        """
        Fetches data from the MySQL `priceTracking` table for a specific month and year.

        Args:
            month (int): Month to filter.
            year (int): Year to filter.

        Returns:
            pandas.DataFrame: DataFrame containing the filtered data.
        """

        query = f"""
            SELECT * FROM priceTracking
            WHERE MONTH(created_at) = {month} AND YEAR(created_at) = {year};
        """

        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if rows == []:
            raise Exception(f"No data found for {month}/{year}")
            return None
        
        df = pd.DataFrame(columns=["id", "barcode", "title", "price", "created_at"])

        for row in rows:
            df.loc[len(df)] = [row[0], row[1], row[2], row[3], row[4]]

        return df


    def check_batch_status(self, batch_id: str) -> bool:
        """
        Checks the status of a submitted price update batch via Trendyol's API.

        Args:
            batch_id (str): The ID returned from a price update request.

        Returns:
            bool: True if all updates succeeded, False otherwise.
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
        
    def loadDF(self) -> DataFrame:
        """
        Loads all entries from the MySQL `priceTracking` table into a pandas DataFrame.

        Returns:
            pandas.DataFrame: The full price tracking table
        """
        
        query = "SELECT * FROM priceTracking"
        df = pd.read_sql(query, self.conn)
        return df

    def matchingProducts(self, dfTrendyol: DataFrame, dfHepsiburada: DataFrame) -> DataFrame:
        """
        Matches products between Trendyol and Hepsiburada DataFrames using 
        various identifiers (barcode, title, etc.). Merges results into a 
        unified DataFrame with common structure.

        Args:
            dfTrendyol (DataFrame): DataFrame containing Trendyol product data.
            dfHepsiburada (DataFrame): DataFrame containing Hepsiburada product data.

        Returns:
            DataFrame: A new merged DataFrame with columns:
                       ["stockID", "HBID", "productName", "price", "stock"]
        """
        # Create empty DataFrame with desired columns
        new_df = pd.DataFrame(columns=["stockID", "HBID", "productName", "price", "stock"])
        hepsi_matched = set()
        trend_matched = set()

        for i in range(len(dfTrendyol)):
            matched = False
            for j in range(len(dfHepsiburada)):
                if (
                    (dfTrendyol.iloc[i, 0] == dfHepsiburada.iloc[j, 0]) or
                    (dfTrendyol.iloc[i, 0] == dfHepsiburada.iloc[j, 5]) or
                    (dfTrendyol.iloc[i, 1] == dfHepsiburada.iloc[j, 0]) or
                    (dfTrendyol.iloc[i, 1] == dfHepsiburada.iloc[j, 5]) or
                    (dfTrendyol.iloc[i, 2] == dfHepsiburada.iloc[j, 0]) or
                    (dfTrendyol.iloc[i, 2] == dfHepsiburada.iloc[j, 5])
                ):
                    # Save matched indexes
                    hepsi_matched.add(j)
                    trend_matched.add(i)

                    # Add Trendyol match
                    stockID = dfTrendyol.iloc[i, 0]
                    productName = dfTrendyol.iloc[i, 3]
                    price = dfTrendyol.iloc[i, 4]
                    stock = dfTrendyol.iloc[i, 5]
                    hb = dfHepsiburada.iloc[j, 1]
                    new_df.loc[len(new_df)] = [stockID, hb, productName, price, stock]
                    matched = True
                    break

            if not matched:
                # Trendyol unmatched
                stockID = dfTrendyol.iloc[i, 0]
                productName = dfTrendyol.iloc[i, 3]
                price = dfTrendyol.iloc[i, 4]
                stock = dfTrendyol.iloc[i, 5]
                hb = dfHepsiburada.iloc[j, 1]
                new_df.loc[len(new_df)] = [stockID, hb, productName, price, stock]

        # Add Hepsiburada entries that were not matched
        for k in range(len(dfHepsiburada)):
            if k not in hepsi_matched:
                stockID = dfHepsiburada.iloc[k, 0]
                productName = dfHepsiburada.iloc[k, 2]
                price = dfHepsiburada.iloc[k, 3]
                stock = dfHepsiburada.iloc[k, 4]
                hb = dfHepsiburada.iloc[k, 1]
                new_df.loc[len(new_df)] = [stockID, hb, productName, price, stock]
        
        return new_df
        
    def get_price_category(self, barcode: str, new_price: float) -> str:
        """
        Determines which lowest-price category (1-week, 2-week, or 1-month) 
        the given price belongs to based on historical data.

        Args:
            barcode (str): Product's barcode.
            new_price (float): New price to evaluate.

        Returns:
            str: One of "1-week-low", "2-week-low", "1-month-low", or "none".
        """
        week_low = self.get_min_price_last_days(barcode, 7)
        two_week_low = self.get_min_price_last_days(barcode, 14)
        month_low = self.get_min_price_last_days(barcode, 30)

        if new_price <= week_low:
            return "1-week-low"
        elif new_price <= two_week_low:
            return "2-week-low"
        elif new_price <= month_low:
            return "1-month-low"
        else:
            return "none"
    
    def ticimax_siparis(self) -> List[int]:
        """
        Fetches order IDs from the Bey Organik WSDL service.
        
        Returns:
            List[int]: A list of order IDs.
        """

        WSDL_URL = "https://www.beyorganik.com/Servis/SiparisServis.svc?wsdl"

        client = Client(WSDL_URL)

        web_siparis_filtre = {
            "EntegrasyonAktarildi": -1,
            "EntegrasyonParams": {
                "AlanDeger": "",
                "Deger": "",
                "EntegrasyonKodu": "",
                "EntegrasyonParamsAktif": False,
                "TabloAlan": "",
                "Tanim": ""
            },
            "IptalEdilmisUrunler": False,
            "FaturaNo": "",
            "OdemeDurumu": 1,
            "OdemeTipi": -1,
            # TODO: different type siparis status filter and should be removed
            # "SiparisDurumu": -1,  # filtreleme yok
            "SiparisID": -1,
            "SiparisKaynagi": "",
            "SiparisKodu": "",
            "StrSiparisDurumu": "Siparişiniz Alındı",
            "TedarikciID": -1,
            "UyeID": -1,
            "SiparisNo": "",
            "UyeTelefon": ""
        }

        web_sayfalama = {
            "BaslangicIndex": 0,
            "KayitSayisi": 1000,
            "SiralamaDegeri": "SiparisTarihi",
            "SiralamaYonu": "Asc"
        }

        result = client.service.SelectSiparis(self.uye_kodu, web_siparis_filtre, web_sayfalama)
        siparisList = []
        count = 0
        for siparis in result:
            siparisList.append(siparis.ID)
            count += 1
        print(f"Toplam {count} sipariş bulundu.")

        return siparisList
    
    def ticimax_urun_siparis(self, siparisList: List[int]) -> Dict:
        """
        Fetches product details for a list of order IDs from the Bey Organik WSDL service.
        Args:
            siparisList (List[int]): List of order IDs to fetch products for.
        Returns:
            Dict: A dictionary mapping product barcodes to a list containing 
                  quantity and product name.
        """

        WSDL_URL = "https://www.beyorganik.com/Servis/SiparisServis.svc?wsdl"
        client = Client(WSDL_URL)

        tum_urunler = {}

        for siparis_id in siparisList:
            siparis_id = int(siparis_id) 
            try:
                urunler = client.service.SelectSiparisUrun(self.uye_kodu, siparis_id, False)

                for urun in urunler:
                    if urun.Barkod not in tum_urunler.keys():
                        tum_urunler[urun.Barkod] = [int(urun.Adet), urun.UrunAdi]
                    else:
                        tum_urunler[urun.Barkod][0] += int(urun.Adet)

            except Exception as e:
                print(f"Hata - Sipariş ID: {siparis_id} → {e}")

        return tum_urunler
    
    def close(self) -> None:
        """
        Closes the MySQL connection and cursor gracefully.
        """
        self.cursor.close()
        self.conn.close()

    def run(self) -> None:
        """
        Main entrypoint to fetch products from Trendyol and store them in MySQL.
        Automatically closes the connection after completion.
        """
        try:
            products = self.fetch_all_products()
            self.store_products(products)
        finally:
            self.close()