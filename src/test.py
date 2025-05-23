from TrendyolPriceController import TrendyolPriceController

TrendyolPriceController = TrendyolPriceController()
# products = TrendyolPriceController.fetch_all_products()
# TrendyolPriceController.store_products(products=products)
# TrendyolPriceController.close()''

result = TrendyolPriceController.update_product_price("8682125485126",399.90, 399.90)
if result[1]:
  mm = TrendyolPriceController.check_batch_status(result[0])
  if mm:
    print("✅ Price updated successfully.")
  else:
    print("❌ Some items failed to update.")
else:
  print("❌ Failed to update price.")