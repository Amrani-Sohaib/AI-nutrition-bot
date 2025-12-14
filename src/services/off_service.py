import aiohttp
from typing import Optional, Dict, Any

async def search_product(query: str) -> Optional[Dict[str, Any]]:
    """
    Searches Open Food Facts for a product by name.
    """
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                products = data.get("products", [])
                if products:
                    product = products[0]
                    return {
                        "name": product.get("product_name", "Unknown"),
                        "calories": product.get("nutriments", {}).get("energy-kcal_100g", 0),
                        "protein": product.get("nutriments", {}).get("proteins_100g", 0),
                        "carbs": product.get("nutriments", {}).get("carbohydrates_100g", 0),
                        "fats": product.get("nutriments", {}).get("fat_100g", 0),
                        "unit": "100g"
                    }
    return None

async def get_product_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """
    Fetches product details using a barcode.
    """
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == 1:
                    product = data.get("product", {})
                    return {
                        "name": product.get("product_name", "Unknown"),
                        "calories": product.get("nutriments", {}).get("energy-kcal_100g", 0),
                        "protein": product.get("nutriments", {}).get("proteins_100g", 0),
                        "carbs": product.get("nutriments", {}).get("carbohydrates_100g", 0),
                        "fats": product.get("nutriments", {}).get("fat_100g", 0),
                        "unit": "100g"
                    }
    return None
