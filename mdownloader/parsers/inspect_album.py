import requests
import json
import re

def extract_album_id(url: str):
    match = re.search(r'/album/.*?/(\d+)', url)
    return match.group(1) if match else None

url = "https://music.apple.com/us/album/frieren-beyond-journeys-end-original-soundtrack/1739445636"
album_id = extract_album_id(url)
api_url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"

response = requests.get(api_url)
data = response.json()

print(json.dumps(data, indent=2))
