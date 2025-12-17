import requests
import json
import os
from datetime import datetime
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
            
            # Find the emote asset in the bundle
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
    """
    Get the actual Animation ID from the emote asset.
    This is the ID that works with HumanoidDescription:SetEmotes()
    """
    
    # Method 1: Try to get from asset delivery
    try:
        url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, allow_redirects=True, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Look for animation ID in the content
            # Pattern: <url>http://www.roblox.com/asset/?id=XXXXXXXXXX</url>
            match = re.search(r'<url>[^<]*id=(\d+)[^<]*</url>', content)
            if match:
                animation_id = match.group(1)
                print(f"    Found animation ID: {animation_id}")
                return animation_id
            
            # Alternative pattern: rbxassetid://XXXXXXXXXX
            match = re.search(r'rbxassetid://(\d+)', content)
            if match:
                animation_id = match.group(1)
                print(f"    Found animation ID (alt): {animation_id}")
                return animation_id
    except Exception as e:
        print(f"    Method 1 failed: {e}")
    
    # Method 2: Try product info API
    try:
        url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Sometimes the asset ID itself is the animation ID
            if data.get('AssetTypeId') == 61:  # 61 = Emote
                print(f"    Using asset ID as animation ID: {asset_id}")
                return str(asset_id)
    except Exception as e:
        print(f"    Method 2 failed: {e}")
    
    # Fallback: return the asset ID
    print(f"    Fallback to asset ID: {asset_id}")
    return str(asset_id)

def main():
    print("=" * 50)
    print(f"EMOTE SNIPER - {datetime.now()}")
    print("=" * 50)
    
    # Load existing emotes
    existing_emotes = get_existing_emotes()
    existing_animation_ids = get_existing_ids(existing_emotes)
    
    # Also track bundle IDs we've already processed
    existing_bundle_ids = set()
    for emote in existing_emotes:
        if 'bundleId' in emote:
            existing_bundle_ids.add(str(emote['bundleId']))
    
    print(f"Existing emotes: {len(existing_emotes)}")
    print(f"Existing animation IDs: {len(existing_animation_ids)}")
    print("")
    
    new_emotes = []
    cursor = None
    pages_to_scan = 10
    
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
            item_type = item.get('itemType', '')
            
            # Skip if we already have this bundle
            if item_id in existing_bundle_ids:
                continue
            
            # Get bundle details
            print(f"  Checking: {item.get('name', 'Unknown')} (ID: {item_id})")
            
            bundle_info = get_bundle_details(item_id)
            
            if bundle_info:
                asset_id = bundle_info['assetId']
                emote_name = bundle_info['name']
                
                # Get the actual animation ID
                animation_id = get_animation_id_from_asset(asset_id)
                
                # Check if we already have this animation ID
                if animation_id not in existing_animation_ids:
                    new_emote = {
                        "id": int(animation_id),
                        "name": emote_name
                    }
                    
                    new_emotes.append(new_emote)
                    existing_animation_ids.add(animation_id)
                    existing_bundle_ids.add(item_id)
                    
                    print(f"    ✓ NEW EMOTE: {emote_name}")
                    print(f"      Animation ID: {animation_id}")
                else:
                    print(f"    - Already exists")
            
            # Rate limiting
            time.sleep(0.3)
        
        # Check for next page
        cursor = result.get('nextPageCursor')
        if not cursor:
            print("  No more pages.")
            break
        
        time.sleep(0.5)
    
    print("")
    print("=" * 50)
    
    if new_emotes:
        print(f"FOUND {len(new_emotes)} NEW EMOTES!")
        print("")
        
        for emote in new_emotes:
            print(f"  • {emote['name']} (ID: {emote['id']})")
        
        # Add new emotes to the beginning of the list
        all_emotes = new_emotes + existing_emotes
        
        # Save to file
        output = {
            "lastUpdated": datetime.now().isoformat(),
            "totalEmotes": len(all_emotes),
            "data": all_emotes
        }
        
        with open(EMOTES_FILE, 'w') as f:
            json.dump(output, f, indent=2)
        
        print("")
        print(f"Saved! Total emotes: {len(all_emotes)}")
    else:
        print("No new emotes found.")
        
        # Still update the lastUpdated timestamp
        if existing_emotes:
            output = {
                "lastUpdated": datetime.now().isoformat(),
                "totalEmotes": len(existing_emotes),
                "data": existing_emotes
            }
            
            with open(EMOTES_FILE, 'w') as f:
                json.dump(output, f, indent=2)
    
    print("=" * 50)

if __name__ == "__main__":
    main()
