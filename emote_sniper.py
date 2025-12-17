import requests
import json
import os
from datetime import datetime, timezone
import time
import re

EMOTES_FILE = "EmoteSniper.json"

def get_existing_emotes():
    """Load existing emotes from JSON"""
    if os.path.exists(EMOTES_FILE):
        with open(EMOTES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('data', [])
    return []

def get_existing_ids(emotes):
    """Get set of existing animation IDs"""
    return set(str(emote['id']) for emote in emotes)

def fetch_emote_bundles(cursor=None):
    """Fetch emote bundles from Roblox catalog"""
    url = "https://catalog.roblox.com/v1/search/items"
    
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
        response = requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching catalog: {e}")
    
    return None

def get_bundle_details(bundle_id):
    """Get bundle details to find the emote asset ID"""
    url = f"https://catalog.roblox.com/v1/bundles/{bundle_id}/details"
    
    try:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if response.status_code == 200:
            data = response.json()
            bundle_name = data.get('name', '')
            
            for item in data.get('items', []):
                if item.get('type') == 'Asset':
                    return {
                        'assetId': item.get('id'),
                        'name': bundle_name
                    }
    except Exception as e:
        print(f"Error getting bundle {bundle_id}: {e}")
    
    return None

def get_animation_id_from_asset(asset_id):
    """Get the actual Animation ID from the emote asset"""
    
    try:
        url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, allow_redirects=True, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            match = re.search(r'<url>[^<]*id=(\d+)[^<]*</url>', content)
            if match:
                return match.group(1)
            
            match = re.search(r'rbxassetid://(\d+)', content)
            if match:
                return match.group(1)
    except:
        pass
    
    return str(asset_id)

def main():
    print("=" * 50)
    print(f"EMOTE SNIPER - {datetime.now()}")
    print("=" * 50)
    
    existing_emotes = get_existing_emotes()
    existing_animation_ids = get_existing_ids(existing_emotes)
    
    existing_bundle_ids = set()
    
    print(f"Existing emotes: {len(existing_emotes)}")
    print("")
    
    new_emotes = []
    cursor = None
    pages_to_scan = 15
    
    for page in range(pages_to_scan):
        print(f"[Page {page + 1}/{pages_to_scan}] Scanning catalog...")
        
        result = fetch_emote_bundles(cursor)
        
        if not result or 'data' not in result:
            print("  No data received, stopping.")
            break
        
        items = result.get('data', [])
        print(f"  Found {len(items)} items")
        
        for item in items:
            item_id = str(item.get('id', ''))
            
            if item_id in existing_bundle_ids:
                continue
            
            existing_bundle_ids.add(item_id)
            
            bundle_info = get_bundle_details(item_id)
            
            if bundle_info:
                asset_id = bundle_info['assetId']
                emote_name = bundle_info['name']
                
                animation_id = get_animation_id_from_asset(asset_id)
                
                if animation_id not in existing_animation_ids:
                    new_emote = {
                        "id": int(animation_id),
                        "name": emote_name
                    }
                    
                    new_emotes.append(new_emote)
                    existing_animation_ids.add(animation_id)
                    
                    print(f"    ✓ NEW: {emote_name} (ID: {animation_id})")
            
            time.sleep(0.2)
        
        cursor = result.get('nextPageCursor')
        if not cursor:
            print("  No more pages.")
            break
        
        time.sleep(0.3)
    
    print("")
    print("=" * 50)
    
    # Combine new + existing
    all_emotes = new_emotes + existing_emotes
    
    # Create output in EXACT format like 7yd7
    output = {
        "keyword": None,
        "totalItems": len(all_emotes),
        "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}Z",
        "data": all_emotes
    }
    
    with open(EMOTES_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    if new_emotes:
        print(f"FOUND {len(new_emotes)} NEW EMOTES!")
        for emote in new_emotes:
            print(f"  • {emote['name']} (ID: {emote['id']})")
    else:
        print("No new emotes found.")
    
    print(f"Total emotes saved: {len(all_emotes)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
