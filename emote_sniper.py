import requests
import json
import os
from datetime import datetime, timezone
import time
import random

EMOTES_FILE = "EmoteSniper.json"

# Multiple proxies for reliability (if one fails, try another)
PROXIES = [
    "https://catalog.roproxy.com",
    "https://catalog.roproxy.cc", 
    "https://catalogapi.roproxy.com",
    "https://catalog.roblox.com"  # Fallback to official API
]

# Different sort types to catch all emotes
SORT_TYPES = [
    {"name": "Recently Updated", "sort": "3"},
    {"name": "Most Favorited", "sort": "1"},
    {"name": "Bestselling", "sort": "2"},
    {"name": "Price Low to High", "sort": "4"},
    {"name": "Price High to Low", "sort": "5"}
]

# Limits per request (30 is max for most proxies)
ITEMS_PER_PAGE = 30
MAX_PAGES_PER_SORT = 100  # Scan up to 100 pages per sort type
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 0.3  # Seconds

class EmoteSniper:
    def __init__(self):
        self.existing_emotes = []
        self.existing_ids = set()
        self.new_emotes = []
        self.all_fetched_ids = set()
        self.working_proxy = None
        self.stats = {
            "pages_scanned": 0,
            "api_calls": 0,
            "errors": 0
        }
    
    def load_existing_emotes(self):
        """Load existing emotes from JSON file"""
        if os.path.exists(EMOTES_FILE):
            try:
                with open(EMOTES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_emotes = data.get('data', [])
                    self.existing_ids = set(str(e['id']) for e in self.existing_emotes)
                    print(f"📦 Loaded {len(self.existing_emotes)} existing emotes")
            except Exception as e:
                print(f"⚠ Error loading existing emotes: {e}")
                self.existing_emotes = []
                self.existing_ids = set()
        else:
            print("📦 No existing database found, starting fresh")
    
    def test_proxy(self, proxy_url):
        """Test if a proxy is working"""
        test_url = f"{proxy_url}/v1/search/items/details?Category=12&Subcategory=39&Limit=1"
        
        try:
            response = requests.get(test_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return True
        except:
            pass
        
        return False
    
    def find_working_proxy(self):
        """Find a working proxy from the list"""
        print("\n🔌 Testing proxies...")
        
        for proxy in PROXIES:
            print(f"  Testing {proxy}...", end=" ")
            if self.test_proxy(proxy):
                print("✅ Working!")
                self.working_proxy = proxy
                return True
            else:
                print("❌ Failed")
        
        print("❌ No working proxy found!")
        return False
    
    def fetch_page(self, sort_type, cursor=None):
        """Fetch a page of emotes"""
        if not self.working_proxy:
            return None
        
        url = f"{self.working_proxy}/v1/search/items/details"
        params = {
            "Category": "12",
            "Subcategory": "39",
            "Limit": str(ITEMS_PER_PAGE),
            "salesTypeFilter": "1",
            "SortType": sort_type
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            self.stats["api_calls"] += 1
            
            response = requests.get(url, params=params, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9"
            }, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("  ⚠ Rate limited, waiting 5 seconds...")
                time.sleep(5)
                return self.fetch_page(sort_type, cursor)  # Retry
            else:
                print(f"  ⚠ HTTP {response.status_code}")
                self.stats["errors"] += 1
                
        except requests.exceptions.Timeout:
            print("  ⚠ Request timeout")
            self.stats["errors"] += 1
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            self.stats["errors"] += 1
        
        return None
    
    def process_item(self, item):
        """Process a single emote item"""
        try:
            emote_id = str(item.get('id', ''))
            
            if not emote_id or emote_id == '0':
                return None
            
            # Skip if already exists
            if emote_id in self.existing_ids:
                return None
            
            # Skip if already fetched in this run
            if emote_id in self.all_fetched_ids:
                return None
            
            emote_name = item.get('name', '').strip()
            
            if not emote_name:
                emote_name = f"Emote_{emote_id}"
            
            # Clean the name
            emote_name = emote_name.replace('\n', ' ').replace('\r', '').strip()
            
            self.all_fetched_ids.add(emote_id)
            
            return {
                "id": int(emote_id),
                "name": emote_name
            }
            
        except Exception as e:
            print(f"    ⚠ Error processing item: {e}")
            return None
    
    def scan_sort_type(self, sort_info):
        """Scan all pages for a specific sort type"""
        sort_name = sort_info["name"]
        sort_type = sort_info["sort"]
        
        print(f"\n🔍 Scanning: {sort_name}")
        print("-" * 50)
        
        cursor = None
        pages_scanned = 0
        emotes_found = 0
        
        while pages_scanned < MAX_PAGES_PER_SORT:
            pages_scanned += 1
            self.stats["pages_scanned"] += 1
            
            # Progress indicator
            if pages_scanned % 10 == 0:
                print(f"  📄 Page {pages_scanned}... ({emotes_found} new found so far)")
            
            result = self.fetch_page(sort_type, cursor)
            
            if not result:
                print(f"  ❌ Failed at page {pages_scanned}")
                break
            
            items = result.get('data', [])
            
            if not items:
                print(f"  ✓ No more items (scanned {pages_scanned} pages)")
                break
            
            for item in items:
                emote_data = self.process_item(item)
                if emote_data:
                    self.new_emotes.append(emote_data)
                    emotes_found += 1
                    print(f"    ✨ NEW: {emote_data['name']} (ID: {emote_data['id']})")
            
            # Get next page cursor
            cursor = result.get('nextPageCursor')
            
            if not cursor:
                print(f"  ✓ Reached end (scanned {pages_scanned} pages)")
                break
            
            # Delay between requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        print(f"  📊 Found {emotes_found} new emotes from {sort_name}")
        return emotes_found
    
    def save_emotes(self):
        """Save all emotes to JSON file"""
        # Combine: new emotes first, then existing
        all_emotes = self.new_emotes + self.existing_emotes
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_emotes = []
        
        for emote in all_emotes:
            emote_id = str(emote['id'])
            if emote_id not in seen_ids:
                seen_ids.add(emote_id)
                unique_emotes.append(emote)
        
        # Create output in exact format
        output = {
            "keyword": None,
            "totalItems": len(unique_emotes),
            "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}Z",
            "data": unique_emotes
        }
        
        # Save with UTF-8 encoding
        with open(EMOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return len(unique_emotes)
    
    def run(self):
        """Main sniper function"""
        start_time = time.time()
        
        print("=" * 60)
        print("  🎀 PINKWARDS EMOTE SNIPER v2.0")
        print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Load existing emotes
        self.load_existing_emotes()
        
        # Find working proxy
        if not self.find_working_proxy():
            print("\n❌ Cannot proceed without a working proxy!")
            return
        
        print(f"\n🌐 Using proxy: {self.working_proxy}")
        
        # Scan each sort type
        total_new = 0
        for sort_info in SORT_TYPES:
            found = self.scan_sort_type(sort_info)
            total_new += found
            
            # Small delay between sort types
            time.sleep(1)
        
        # Results
        print("\n" + "=" * 60)
        print("  📊 RESULTS")
        print("=" * 60)
        
        if self.new_emotes:
            print(f"\n🎉 Found {len(self.new_emotes)} NEW emotes!")
            print("-" * 40)
            
            # Show first 30 new emotes
            for emote in self.new_emotes[:30]:
                print(f"  • {emote['name']} (ID: {emote['id']})")
            
            if len(self.new_emotes) > 30:
                print(f"  ... and {len(self.new_emotes) - 30} more!")
        else:
            print("\nℹ No new emotes found")
        
        # Save to file
        total_saved = self.save_emotes()
        
        # Stats
        elapsed = time.time() - start_time
        
        print("\n" + "-" * 40)
        print("  📈 STATISTICS")
        print("-" * 40)
        print(f"  • Total emotes in database: {total_saved}")
        print(f"  • New emotes added: {len(self.new_emotes)}")
        print(f"  • Pages scanned: {self.stats['pages_scanned']}")
        print(f"  • API calls made: {self.stats['api_calls']}")
        print(f"  • Errors: {self.stats['errors']}")
        print(f"  • Time elapsed: {elapsed:.1f} seconds")
        print("=" * 60)


def main():
    sniper = EmoteSniper()
    sniper.run()


if __name__ == "__main__":
    main()
