import requests
import json
import os
from datetime import datetime, timezone

EMOTES_FILE = "EmoteSniper.json"

# Source databases to sync from
SOURCES = [
    "https://raw.githubusercontent.com/7yd7/sniper-Emote/refs/heads/test/EmoteSniper.json",
    "https://raw.githubusercontent.com/7yd7/sniper-Emote/test/EmoteSniper.json",
    "https://raw.githubusercontent.com/7yd7/sniper-Emote/main/EmoteSniper.json"
]

def load_existing():
    """Load existing emotes"""
    if os.path.exists(EMOTES_FILE):
        try:
            with open(EMOTES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('data', [])
        except:
            pass
    return []

def fetch_from_source(url):
    """Fetch emotes from a source URL"""
    try:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
    except Exception as e:
        print(f"  Error: {e}")
    
    return None

def main():
    print("╔════════════════════════════════════════════════════════╗")
    print("║       🎀 PINKWARDS EMOTE SNIPER (Simple Mode) 🎀       ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    # Load existing
    existing = load_existing()
    existing_ids = set(str(e['id']) for e in existing)
    print(f"\n📦 Existing emotes: {len(existing)}")
    
    # Fetch from sources
    new_emotes = []
    
    for source in SOURCES:
        print(f"\n🔍 Fetching from source...")
        print(f"   {source[:60]}...")
        
        emotes = fetch_from_source(source)
        
        if emotes:
            print(f"   ✅ Got {len(emotes)} emotes!")
            
            for emote in emotes:
                emote_id = str(emote.get('id', ''))
                
                if emote_id and emote_id not in existing_ids:
                    existing_ids.add(emote_id)
                    new_emotes.append({
                        "id": int(emote_id),
                        "name": emote.get('name', f'Emote_{emote_id}')
                    })
            
            break  # Success, no need to try other sources
        else:
            print(f"   ❌ Failed")
    
    # Combine
    all_emotes = new_emotes + existing
    
    # Remove duplicates
    seen = set()
    unique = []
    for e in all_emotes:
        if str(e['id']) not in seen:
            seen.add(str(e['id']))
            unique.append(e)
    
    # Save
    output = {
        "keyword": None,
        "totalItems": len(unique),
        "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "data": unique
    }
    
    with open(EMOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'═' * 50}")
    print(f"📊 RESULTS:")
    print(f"   • Before: {len(existing)} emotes")
    print(f"   • After:  {len(unique)} emotes")
    print(f"   • NEW:    {len(new_emotes)} emotes")
    print(f"{'═' * 50}")

if __name__ == "__main__":
    main()
