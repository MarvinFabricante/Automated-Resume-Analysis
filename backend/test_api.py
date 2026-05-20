import requests

def test_login(email, password):
    url = "http://localhost:8000/auth/login"
    payload = {
        "email": email,
        "password": password
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Testing {email} with {password}: Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"Error connecting: {e}")

test_login("marvin@gmail.com", "password123")
test_login("marvinfabricante630@gmail.com", "password123")
test_login("tyron@gmail.com", "password123")
