import requests
import json
import os
from datetime import datetime, timezone
import time

EMOTES_FILE = "EmoteSniper.json"

# Multiple proxies for reliability
PROXIES = [
    "https://catalog.roproxy.com",
    "https://catalog.roproxy.cc",
    "https://catalogapi.roproxy.com",
    "https://catalog.roproxy.live",
    "https://catalog.roproxy.eu",
    "https://games.roproxy.com",
    "https://catalog.roblox.com"  # Official fallback
]

# Base endpoint
BASE_ENDPOINT = "/v1/search/items/details"

# All API configurations to scan
API_CONFIGS = [
    # Sort Types
    {
        "name": "🆕 Recently Updated",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "3"
        }
    },
    {
        "name": "⭐ Most Favorited",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "1"
        }
    },
    {
        "name": "💰 Bestselling",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "2"
        }
    },
    {
        "name": "💵 Price Low to High",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "4"
        }
    },
    {
        "name": "💎 Price High to Low",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "5"
        }
    },
    
    # Creator Types
    {
        "name": "🏢 Roblox Official Emotes",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "CreatorType": "1",
            "SortType": "3"
        }
    },
    {
        "name": "👤 UGC Emotes",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "CreatorType": "2",
            "SortType": "3"
        }
    },
    
    # Bundle Types
    {
        "name": "📦 Emote Bundles",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "3",
            "IncludeNotForSale": "false"
        }
    },
    
    # Free Emotes
    {
        "name": "🆓 Free Emotes",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "MaxPrice": "0",
            "SortType": "3"
        }
    },
    
    # Price Ranges
    {
        "name": "💲 Cheap Emotes (1-100 Robux)",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "MinPrice": "1",
            "MaxPrice": "100",
            "SortType": "3"
        }
    },
    {
        "name": "💲💲 Mid-Price Emotes (101-500 Robux)",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "MinPrice": "101",
            "MaxPrice": "500",
            "SortType": "3"
        }
    },
    {
        "name": "💲💲💲 Premium Emotes (500+ Robux)",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "MinPrice": "500",
            "SortType": "3"
        }
    },
    
    # All Emotes (no filters)
    {
        "name": "📋 All Emotes (Default)",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30"
        }
    },
    
    # Relevance Sort
    {
        "name": "🔍 Relevance Sort",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "salesTypeFilter": "1",
            "SortType": "0"
        }
    },
    
    # Include Not For Sale (Limited/Offsale)
    {
        "name": "🔒 Limited/Offsale Emotes",
        "params": {
            "Category": "12",
            "Subcategory": "39",
            "Limit": "30",
            "IncludeNotForSale": "true",
            "SortType": "3"
        }
    }
]

# Settings
MAX_PAGES_PER_CONFIG = 100
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 0.3
DELAY_BETWEEN_CONFIGS = 1


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
            "errors": 0,
            "configs_scanned": 0
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
        test_url = f"{proxy_url}{BASE_ENDPOINT}"
        test_params = {"Category": "12", "Subcategory": "39", "Limit": "1"}
        
        try:
            response = requests.get(
                test_url,
                params=test_params,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                },
                timeout=10
            )
            
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
            print(f"  Testing {proxy}...", end=" ", flush=True)
            if self.test_proxy(proxy):
                print("✅ Working!")
                self.working_proxy = proxy
                return True
            else:
                print("❌ Failed")
        
        print("❌ No working proxy found!")
        return False
    
    def fetch_page(self, params, cursor=None):
        """Fetch a page of emotes"""
        if not self.working_proxy:
            return None
        
        url = f"{self.working_proxy}{BASE_ENDPOINT}"
        
        # Copy params and add cursor if provided
        request_params = params.copy()
        if cursor:
            request_params["cursor"] = cursor
        
        try:
            self.stats["api_calls"] += 1
            
            response = requests.get(
                url,
                params=request_params,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                print("\n  ⚠ Rate limited, waiting 10 seconds...")
                time.sleep(10)
                return self.fetch_page(params, cursor)  # Retry
            
            elif response.status_code == 503:
                print("\n  ⚠ Service unavailable, trying different proxy...")
                # Try to find another working proxy
                old_proxy = self.working_proxy
                self.working_proxy = None
                
                for proxy in PROXIES:
                    if proxy != old_proxy and self.test_proxy(proxy):
                        self.working_proxy = proxy
                        print(f"  Switched to: {proxy}")
                        return self.fetch_page(params, cursor)
                
                self.working_proxy = old_proxy  # Fallback to original
                self.stats["errors"] += 1
                return None
            
            else:
                print(f"\n  ⚠ HTTP {response.status_code}")
                self.stats["errors"] += 1
                
        except requests.exceptions.Timeout:
            print("\n  ⚠ Request timeout")
            self.stats["errors"] += 1
        except requests.exceptions.ConnectionError:
            print("\n  ⚠ Connection error")
            self.stats["errors"] += 1
        except Exception as e:
            print(f"\n  ⚠ Error: {e}")
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
            
            # Remove extra whitespace
            emote_name = ' '.join(emote_name.split())
            
            self.all_fetched_ids.add(emote_id)
            
            return {
                "id": int(emote_id),
                "name": emote_name
            }
            
        except Exception as e:
            return None
    
    def scan_config(self, config):
        """Scan all pages for a specific API configuration"""
        config_name = config["name"]
        params = config["params"]
        
        print(f"\n🔍 {config_name}")
        print("-" * 55)
        
        cursor = None
        pages_scanned = 0
        emotes_found = 0
        consecutive_empty = 0
        
        while pages_scanned < MAX_PAGES_PER_CONFIG:
            pages_scanned += 1
            self.stats["pages_scanned"] += 1
            
            # Progress indicator every 10 pages
            if pages_scanned % 10 == 0:
                print(f"  📄 Page {pages_scanned}... ({emotes_found} new)", flush=True)
            
            result = self.fetch_page(params, cursor)
            
            if not result:
                print(f"  ❌ Failed at page {pages_scanned}")
                break
            
            items = result.get('data', [])
            
            if not items:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    print(f"  ✓ No more items (page {pages_scanned})")
                    break
                continue
            else:
                consecutive_empty = 0
            
            # Process items
            for item in items:
                emote_data = self.process_item(item)
                if emote_data:
                    self.new_emotes.append(emote_data)
                    emotes_found += 1
                    print(f"    ✨ NEW: {emote_data['name']} (ID: {emote_data['id']})")
            
            # Get next page cursor
            cursor = result.get('nextPageCursor')
            
            if not cursor:
                print(f"  ✓ End reached (page {pages_scanned})")
                break
            
            # Delay between requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        self.stats["configs_scanned"] += 1
        
        if emotes_found > 0:
            print(f"  📊 Found {emotes_found} new emotes!")
        else:
            print(f"  📊 No new emotes from this endpoint")
        
        return emotes_found
    
    def remove_duplicates(self, emotes):
        """Remove duplicate emotes while preserving order"""
        seen_ids = set()
        unique_emotes = []
        
        for emote in emotes:
            emote_id = str(emote['id'])
            if emote_id not in seen_ids:
                seen_ids.add(emote_id)
                unique_emotes.append(emote)
        
        return unique_emotes
    
    def save_emotes(self):
        """Save all emotes to JSON file"""
        # Combine: new emotes first, then existing
        all_emotes = self.new_emotes + self.existing_emotes
        
        # Remove duplicates
        unique_emotes = self.remove_duplicates(all_emotes)
        
        # Create output in exact format like 7yd7
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
    
    def print_banner(self):
        """Print startup banner"""
        print("")
        print("╔════════════════════════════════════════════════════════╗")
        print("║          🎀 PINKWARDS EMOTE SNIPER v3.0 🎀             ║")
        print("║                                                        ║")
        print(f"║  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                            ║")
        print("╚════════════════════════════════════════════════════════╝")
    
    def print_results(self, total_saved, elapsed):
        """Print final results"""
        print("")
        print("╔════════════════════════════════════════════════════════╗")
        print("║                    📊 RESULTS                          ║")
        print("╚════════════════════════════════════════════════════════╝")
        
        if self.new_emotes:
            print(f"\n🎉 Found {len(self.new_emotes)} NEW emotes!")
            print("-" * 55)
            
            # Show first 50 new emotes
            for i, emote in enumerate(self.new_emotes[:50]):
                print(f"  {i+1:3}. {emote['name']} (ID: {emote['id']})")
            
            if len(self.new_emotes) > 50:
                print(f"\n  ... and {len(self.new_emotes) - 50} more!")
        else:
            print("\nℹ No new emotes found this run")
        
        print("")
        print("╔════════════════════════════════════════════════════════╗")
        print("║                   📈 STATISTICS                        ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"  • Total emotes in database: {total_saved:,}")
        print(f"  • New emotes added: {len(self.new_emotes):,}")
        print(f"  • API configs scanned: {self.stats['configs_scanned']}")
        print(f"  • Pages scanned: {self.stats['pages_scanned']:,}")
        print(f"  • API calls made: {self.stats['api_calls']:,}")
        print(f"  • Errors encountered: {self.stats['errors']}")
        print(f"  • Time elapsed: {elapsed:.1f} seconds")
        print("")
        print("═" * 58)
    
    def run(self):
        """Main sniper function"""
        start_time = time.time()
        
        self.print_banner()
        
        # Load existing emotes
        self.load_existing_emotes()
        
        # Find working proxy
        if not self.find_working_proxy():
            print("\n❌ Cannot proceed without a working proxy!")
            print("Please try again later or check your internet connection.")
            return
        
        print(f"\n🌐 Using proxy: {self.working_proxy}")
        print(f"📋 Scanning {len(API_CONFIGS)} different API endpoints...")
        
        # Scan each API configuration
        for i, config in enumerate(API_CONFIGS):
            print(f"\n[{i+1}/{len(API_CONFIGS)}]", end="")
            self.scan_config(config)
            
            # Delay between configs
            if i < len(API_CONFIGS) - 1:
                time.sleep(DELAY_BETWEEN_CONFIGS)
        
        # Save results
        total_saved = self.save_emotes()
        
        # Print results
        elapsed = time.time() - start_time
        self.print_results(total_saved, elapsed)


def main():
    sniper = EmoteSniper()
    sniper.run()


if __name__ == "__main__":
    main()
