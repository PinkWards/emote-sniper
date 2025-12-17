import requests
import json
import os
from datetime import datetime, timezone
import time

EMOTES_FILE = "EmoteSniper.json"

# Using roproxy APIs (better than direct Roblox API)
APIS = [
    {
        "name": "Latest Emotes",
        "url": "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30&salesTypeFilter=1&SortType=3"
    },
    {
        "name": "All Emotes",
        "url": "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30"
    }
]

def get_existing_emotes():
    """Load existing emotes from JSON"""
    if os.path.exists(EMOTES_FILE):
        try:
            with open(EMOTES_FILE, 'r') as f:
                data = json.load(f)
                return data.get('data', [])
        except:
            return []
    return []

def get_existing_ids(emotes):
    """Get set of existing emote IDs"""
    return set(str(emote['id']) for emote in emotes)

def fetch_emotes_from_api(base_url, cursor=None):
    """Fetch emotes from roproxy API"""
    url = base_url
    if cursor:
        url += f"&cursor={cursor}"
    
    try:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  API returned status: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return None

def extract_emote_data(item):
    """Extract emote ID and name from API response item"""
    
    # The roproxy API returns detailed info
    emote_id = item.get('id')
    emote_name = item.get('name', f'Emote_{emote_id}')
    
    # Clean up the name (remove extra spaces, etc.)
    emote_name = emote_name.strip()
    
    return {
        "id": int(emote_id),
        "name": emote_name
    }

def main():
    print("=" * 60)
    print(f"  🎀 PINKWARDS EMOTE SNIPER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Load existing emotes
    existing_emotes = get_existing_emotes()
    existing_ids = get_existing_ids(existing_emotes)
    
    print(f"\n📦 Existing emotes in database: {len(existing_emotes)}")
    
    new_emotes = []
    all_fetched_ids = set()
    
    # Scan using both APIs
    for api in APIS:
        print(f"\n🔍 Scanning: {api['name']}")
        print("-" * 40)
        
        cursor = None
        pages_scanned = 0
        max_pages = 50  # Scan up to 50 pages per API
        
        while pages_scanned < max_pages:
            pages_scanned += 1
            print(f"  [Page {pages_scanned}] Fetching...")
            
            result = fetch_emotes_from_api(api['url'], cursor)
            
            if not result:
                print("  ❌ No response, stopping this API")
                break
            
            items = result.get('data', [])
            
            if not items:
                print("  ✓ No more items")
                break
            
            print(f"  Found {len(items)} items")
            
            for item in items:
                try:
                    emote_data = extract_emote_data(item)
                    emote_id = str(emote_data['id'])
                    
                    # Skip if we already have this emote
                    if emote_id in existing_ids:
                        continue
                    
                    # Skip if we already fetched this emote in this run
                    if emote_id in all_fetched_ids:
                        continue
                    
                    all_fetched_ids.add(emote_id)
                    new_emotes.append(emote_data)
                    
                    print(f"    ✨ NEW: {emote_data['name']} (ID: {emote_id})")
                    
                except Exception as e:
                    print(f"    ⚠ Error processing item: {e}")
                    continue
            
            # Check for next page
            cursor = result.get('nextPageCursor')
            if not cursor:
                print("  ✓ Reached last page")
                break
            
            # Small delay to be nice to the API
            time.sleep(0.5)
    
    # Combine new + existing emotes
    print("\n" + "=" * 60)
    
    if new_emotes:
        print(f"🎉 FOUND {len(new_emotes)} NEW EMOTES!")
        print("-" * 40)
        for emote in new_emotes[:20]:  # Show first 20
            print(f"  • {emote['name']} (ID: {emote['id']})")
        if len(new_emotes) > 20:
            print(f"  ... and {len(new_emotes) - 20} more!")
    else:
        print("ℹ No new emotes found")
    
    # Merge: new emotes first, then existing
    all_emotes = new_emotes + existing_emotes
    
    # Remove duplicates (keep first occurrence)
    seen_ids = set()
    unique_emotes = []
    for emote in all_emotes:
        if str(emote['id']) not in seen_ids:
            seen_ids.add(str(emote['id']))
            unique_emotes.append(emote)
    
    # Create output in exact format like 7yd7
    output = {
        "keyword": None,
        "totalItems": len(unique_emotes),
        "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}Z",
        "data": unique_emotes
    }
    
    # Save to file
    with open(EMOTES_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print("-" * 40)
    print(f"💾 Saved {len(unique_emotes)} total emotes to {EMOTES_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
