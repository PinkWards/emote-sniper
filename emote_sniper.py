import requests
import json
import os
from datetime import datetime
import time

CATALOG_URL = "https://catalog.roblox.com/v1/search/items"
EMOTES_FILE = "EmoteSniper.json"

def get_existing_emotes():
    if os.path.exists(EMOTES_FILE):
        with open(EMOTES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('data', [])
    return []

def get_existing_ids(emotes):
    return set(str(emote['id']) for emote in emotes)

def get_emote_name(asset_id):
    url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
    
    try:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code == 200:
            return response.json().get('Name', f'Emote_{asset_id}')
    except:
        pass
    
    return f'Emote_{asset_id}'

def fetch_catalog_page(cursor=None):
    params = {
        "category": "12",
        "limit": 120,
        "salesTypeFilter": "1",
        "sortType": "3",
        "subcategory": "39"
    }
    
    if cursor:
        params["cursor"] = cursor
    
    try:
        response = requests.get(CATALOG_URL, params=params, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error: {e}")
    
    return None

def main():
    print(f"[{datetime.now()}] Starting emote sniper...")
    
    existing_emotes = get_existing_emotes()
    existing_ids = get_existing_ids(existing_emotes)
    
    print(f"Existing emotes: {len(existing_emotes)}")
    
    new_emotes = []
    cursor = None
    
    for page in range(5):
        print(f"Scanning page {page + 1}...")
        
        result = fetch_catalog_page(cursor)
        
        if not result or 'data' not in result:
            print("No data received")
            break
        
        for item in result['data']:
            asset_id = str(item.get('id', ''))
            
            if asset_id and asset_id not in existing_ids:
                name = get_emote_name(asset_id)
                
                new_emote = {
                    "id": int(asset_id),
                    "name": name
                }
                
                new_emotes.append(new_emote)
                existing_ids.add(asset_id)
                
                print(f"  NEW EMOTE: {name} (ID: {asset_id})")
                
                time.sleep(0.2)
        
        cursor = result.get('nextPageCursor')
        if not cursor:
            break
        
        time.sleep(0.5)
    
    if new_emotes:
        print(f"\nFound {len(new_emotes)} new emotes!")
        
        all_emotes = new_emotes + existing_emotes
        
        output = {
            "lastUpdated": datetime.now().isoformat(),
            "totalEmotes": len(all_emotes),
            "data": all_emotes
        }
        
        with open(EMOTES_FILE, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"Total emotes saved: {len(all_emotes)}")
    else:
        print("No new emotes found")
        
        if existing_emotes:
            output = {
                "lastUpdated": datetime.now().isoformat(),
                "totalEmotes": len(existing_emotes),
                "data": existing_emotes
            }
            
            with open(EMOTES_FILE, 'w') as f:
                json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
