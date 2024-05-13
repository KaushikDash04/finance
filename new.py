import requests

url = 'https://api.upstox.com/v2/login/authorization/token'
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
}

data = {
    'code': '{your_code}',
    'client_id': 'd823030c-839c-416d-8ee9-a08fef5fa42d',
    'client_secret': 'd6jdncrzm8',
    'redirect_uri': 'https://finance-ofkr.onrender.com/',
    'grant_type': 'authorization_code',
}

response = requests.post(url, headers=headers, data=data)

print(response.status_code)
print(response.json())
