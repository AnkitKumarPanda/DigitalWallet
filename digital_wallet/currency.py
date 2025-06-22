import requests

def get_conversion_rate(to_currency):
    # Directly using your provided API key
    api_key = 'cur_live_elUISbZVuo0zBhPSctmqXm8KC8hJ9tpa6ub90XUB'
    url = f"https://api.currencyapi.com/v3/latest?apikey={api_key}&base_currency=INR"

    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            try:
                return data['data'][to_currency]['value']
            except KeyError:
                print(f"Currency '{to_currency}' not found in API response.")
                return None
        else:
            print(f"Currency API returned status code: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching currency rate: {e}")
        return None
