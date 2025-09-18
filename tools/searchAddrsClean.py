# ------------------- CUSTOM PAYLOAD -------------------
# NOTE: This header is a simple example of engineering.
# The cookie value and some headers are intentionally filled
# with fake data to demonstrate that this endpoint may only
# require structure validation, not actual session validation.
# ------------------------------------------------------------

import requests
import json

class SearchAddrsInfo:
    def __init__(self):
        self.base_url = "https://api.arkm.com/balances/address/"
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.117 Mobile Safari/537.36 Mozila.Android/11.12.0 (Xiaomi M2101K6G; Android 13; SDK 33; HIGH)",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': "\"Android\"",
            'sec-ch-ua': "\"Android WebView\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
            'x-timestamp': "1755327505",
            'sec-ch-ua-mobile': "?1",
            'origin': "https://intel.arkm.com",
            'x-requested-with': "com.termux",
            'sec-fetch-site': "same-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://intel.arkm.com/",
            'accept-language': "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
            'priority': "u=1, i",
            'Cookie': "_ga=test123; _fbp=test123; _clck=test123; _gcl_au=test123 ;arkham_is_authed=true;device_id%test123; arkham_platform_session=test123-92f4-453a-aedd-test123ue234", 
        }

    def query(self, address):
        """Query address information from the API and return simplified raw data."""
        try:
            url = f"{self.base_url}{address}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = json.loads(response.text)

            simplified_data = {
                "portfolio": [],
                "holdings_by_chain": {}, 
            }

            for chain, tokens in data.get('balances', {}).items():
                for token in tokens:
                    simplified_data["portfolio"].append({
                        "chain": chain,
                        "token": token.get('name', 'N/A'),
                        "price_usd": token.get('price', 0),
                        "holding": token.get('balance', 0),
                        "value_usd": token.get('usd', 0),
                        "change_24h_percent": token.get('priceChange24hPercent', 0)
                    })

            for chain, value in data.get('totalBalance', {}).items():
                value_24h_ago = data.get('totalBalance24hAgo', {}).get(chain, 0)
                if value > 0 or value_24h_ago > 0:
                    simplified_data["holdings_by_chain"][chain] = {
                        "total_value_usd": value,
                        "value_24h_ago_usd": value_24h_ago
                    }

            return simplified_data

        except requests.RequestException as e:
            return {"error": f"Error fetching data: {str(e)}"}
        except json.JSONDecodeError as e:
            return {"error": f"Error decoding JSON: {str(e)}"}

# Example usage
if __name__ == "__main__":
    searcher = SearchAddrsInfo()
    result = searcher.query("0x545E0844FF0680cd70dE36b986fcE7e7C44c6cFb")
    print(json.dumps(result, indent=2))

