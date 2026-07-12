import requests

# Test API
url = "http://127.0.0.1:8000/api/v1/clients/"
data = {
    "name": "测试客户",
    "phone": "13800138000",
    "gender": "女",
    "age_group": "30-40"
}

print(f"POST {url}")
print(f"Data: {data}")

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
