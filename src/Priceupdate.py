import requests
import json
import time
import os
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Load environment variables from .env file (API keys, DB creds, etc.)
# -------------------------------------------------------------------
load_dotenv()

# GEREKLİ BİLGİLER
api_key = os.getenv("API_KEY")
seller_id = os.getenv("SELLER_ID")
url_update = f"https://apigw.trendyol.com/integration/inventory/sellers/{seller_id}/products/price-and-inventory"
url_result_template = f"https://apigw.trendyol.com/integration/product/sellers/{seller_id}/products/batch-requests/{{batch_id}}"

headers = {
    "Content-Type": "application/json",
    "Authorization": api_key
}

# GÜNCELLENECEK ÜRÜN VERİSİ
data = {
    "items": [
        {
            "barcode": "8682125482126",
            "salePrice": 355.99,
            "listPrice": 356.99
        }
    ]
}

# 1️⃣ GÜNCELLEME İSTEĞİ GÖNDER
print("Stok ve fiyat güncellemesi gönderiliyor...")
response = requests.post(url_update, headers=headers, data=json.dumps(data))

if response.status_code == 200:
    batch_id = response.json().get("batchRequestId")
    print(f"İşlem başarıyla gönderildi. BatchRequestId: {batch_id}")
else:
    print("İstek başarısız oldu.")
    print("Status Code:", response.status_code)
    print("Hata Mesajı:", response.text)
    exit()

# 2️⃣ BİRA BEKLE VE SONUCU KONTROL ET
print("İşlem sonucu kontrol ediliyor...")
time.sleep(3)  # Çok hızlı sorgu atma, sistem işlemiyor olabilir

url_result = url_result_template.format(batch_id=batch_id)
result_response = requests.get(url_result, headers=headers)

if result_response.status_code == 200:
    result = result_response.json()
    print("Toplu işlem durumu:")
    print(result)
    for item in result.get("items", []):
        barcode = item["requestItem"].get("barcode")
        status = item["status"]
        print(f"  📦 {barcode} ➝ {status}")
        if item["failureReasons"]:
            print("     ❌ Hatalar:", item["failureReasons"])
else:
    print("Sonuç sorgulamada hata oluştu.")
    print("Status Code:", result_response.status_code)
    print("Hata Mesajı:", result_response.text)