import requests
import os

# Carica le API key da variabili d'ambiente
BREACH_API_KEY = os.getenv("BREACH_API_KEY")
TRUECALLER_API_KEY = os.getenv("TRUECALLER_API_KEY")

def breachdirectory_lookup(email):
    url = f"https://breachdirectory.p.rapidapi.com/?func=auto&term={email}"
    headers = {
        "X-RapidAPI-Key": BREACH_API_KEY,
        "X-RapidAPI-Host": "rohan-patra-breachdirectory.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Status code {response.status_code}"}

def truecaller_lookup(phone):
    url = f"https://truecaller-data2.p.rapidapi.com/search?phone={phone}"
    headers = {
        "X-RapidAPI-Key": TRUECALLER_API_KEY,
        "X-RapidAPI-Host": "do3t-truecaller-data2.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Status code {response.status_code}"}

# Esempio di utilizzo
if __name__ == "__main__":
    email = "esempio@email.com"
    phone = "+391234567890"
    print(breachdirectory_lookup(email))
    print(truecaller_lookup(phone))
