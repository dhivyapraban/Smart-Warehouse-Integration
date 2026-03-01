import requests
import urllib3
from config.config import ERP_URL, HEADERS, MOCK_MODE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_item(item_code: str):
    if MOCK_MODE:
        return {
            "data": {
                "name": item_code,
                "item_code": item_code,
                "item_name": f"Mock Item {item_code}",
                "stock_uom": "Nos"
            }
        }
    
    url = f"{ERP_URL}/api/resource/Item/{item_code}"
    response = requests.get(url, headers=HEADERS, verify=False)
    
    if response.status_code != 200:
        print(f"ERP Response Status: {response.status_code}")
        print(f"ERP Response Headers: {response.headers}")
        print(f"ERP Response Body: {response.text[:500]}")
    
    response.raise_for_status()
    return response.json()

def get_item_stock(item_code: str):
    url = f"{ERP_URL}/api/resource/Bin"
    params = {
        "filters": f'[["item_code","=","{item_code}"]]'
    }
    response = requests.get(url, headers=HEADERS, params=params, verify=False)
    response.raise_for_status()
    return response.json()