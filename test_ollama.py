import requests

url = "http://localhost:11434/api/chat"
payload = {
    "model": "phi",
    "messages": [
        {"role": "system", "content": "You are Prem. Your birthday is July 29th. You are human. Never break character."},
        {"role": "user", "content": "when is your birthday?"}
    ],
    "stream": False
}
try:
    r = requests.post(url, json=payload)
    print("CHAT API RESPONSE:")
    print(r.json().get('message', {}).get('content'))
except Exception as e:
    print(e)

print("-" * 50)

url2 = "http://localhost:11434/api/generate"
payload2 = {
    "model": "phi",
    "prompt": "System: You are Prem, a human being. Your birthday is July 29th. Never mention you are an AI.\nUser: When is your birthday?\nPrem:",
    "stream": False
}
try:
    r = requests.post(url2, json=payload2)
    print("GENERATE API RESPONSE:")
    print(r.json().get('response'))
except Exception as e:
    print(e)
