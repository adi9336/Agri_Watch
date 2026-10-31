import urllib.request
import urllib.parse
import json
import os
import sys

# Get API key from argument, environment variable, or prompt
api_key = None
if len(sys.argv) > 1:
    api_key = sys.argv[1]
else:
    api_key = os.getenv("DATA_GOV_IN_KEY")

if not api_key:
    api_key = input("Enter your data.gov.in API key: ").strip()

if not api_key:
    print("Error: No API key provided.")
    sys.exit(1)

base_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
params = {
    "api-key": api_key,
    "format": "json",
    "limit": "10",
    "filters[state.keyword]": "Uttar Pradesh",
    "filters[commodity]": "Wheat"
}
url = base_url + "?" + urllib.parse.urlencode(params)
headers = {"User-Agent": "AgriWatch/1.0"}
req = urllib.request.Request(url, headers=headers)

try:
    print(f"Connecting to data.gov.in with your API key...")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("Response Code:", resp.status)
        data = json.loads(resp.read().decode("utf-8"))
        print("Total Records in live feed:", data.get("total"))
        records = data.get("records", [])
        print(f"Fetched {len(records)} live records:\n")
        for r in records:
            print(f"Date: {r.get('arrival_date')} | Mandi: {r.get('market')} ({r.get('district')})")
            print(f"  {r.get('commodity')} ({r.get('variety')}): Modal Rs. {r.get('modal_price')}/Quintal (Range: Rs. {r.get('min_price')} - Rs. {r.get('max_price')})\n")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print("Error:", e)
