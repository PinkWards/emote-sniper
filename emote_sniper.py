import requests
import json
import os
from datetime import datetime, timezone
import time
import random

EMOTES_FILE = "EmoteSniper.json"

# Updated working proxies and direct APIs
PROXIES = [
    # RoProxy alternatives
    "https://catalog.roproxy.com",
    "https://catalog.roproxy.cc",
    
    # Direct Roblox APIs (sometimes work)
    "https://catalog.roblox.com",
    "https://apis.roblox.com/catalog-api",
    
    # Other proxies
    "https://roblox-api.xyz/catalog",
    "https://api.roblox.plus/catalog"
]

# Different User Agents to avoid blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Roblox/WinInet",
    "RobloxStudio/WinInet"
]

BASE_ENDPOINT = "/v1/search/items/details"

API_CONFIGS = [
    {
        "name": "🆕 Recently Updated",
        "params": {"Category": "12", "Subcategory": "39", "Limit": "30", "SortType": "3"}
    },
    {
        "name": "⭐ Most Favorited", 
        "params": {"Category": "12", "Subcategory": "39", "Limit": "30", "SortType": "1"}
    },
    {
        "name": "💰 Bestselling",
        "params": {"Category": "12", "Subcategory": "39", "Limit": "30", "SortType": "2"}
    },
    {
        "name": "📋 All Emotes",
        "params": {"Category": "12", "Subcategory": "39", "Limit": "30"}
    }
]

MAX_PAGES_PER_CONFIG = 200
REQUEST_TIMEOUT = 45
DELAY_BETWEEN_REQUESTS = 1.0  # Increased delay
MAX_RETRIES = 3


class EmoteSniper:
    def __init__(self):
        self.existing_emotes = []
        self.existing_ids = set()
        self.new_emotes = []
        self.all_fetched_ids = set()
        self.working_proxy = None
        self.session = None
        self.stats = {
            "pages_scanned": 0,
            "api_calls": 0,
            "errors": 0,
            "configs_scanned": 0,
            "items_processed": 0
        }
    
    def create_session(self):
        """Create a requests session with retry capability"""
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        })
        
        return self.session
    
    def get_random_user_agent(self):
        """Get a random user agent"""
        return random.choice(USER_AGENTS)
    
    def load_existing_emotes(self):
        """Load existing emotes from JSON file"""
        if os.path.exists(EMOTES_FILE):
            try:
                with open(EMOTES_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        data = json.loads(content)
                        self.existing_emotes = data.get('data', [])
                        self.existing_ids = set(str(e['id']) for e in self.existing_emotes)
                        print(f"📦 Loaded {len(self.existing_emotes)} existing emotes")
                    else:
                        print("📦 Empty database, starting fresh")
            except Exception as e:
                print(f"⚠ Error loading: {e}")
        else:
            print("📦 No database found, starting fresh")
    
    def test_proxy(self, proxy_url):
        """Test if a proxy is working with multiple attempts"""
        test_urls = [
            f"{proxy_url}/v1/search/items/details?Category=12&Subcategory=39&Limit=1",
            f"{proxy_url}/v1/search/items?Category=12&Subcategory=39&Limit=1"
        ]
        
        for test_url in test_urls:
            for attempt in range(2):
                try:
                    response = self.session.get(
                        test_url,
                        headers={"User-Agent": self.get_random_user_agent()},
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    print(f" [HTTP {response.status_code}]", end="")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if 'data' in data:
                                return True
                        except:
                            pass
                    
                    time.sleep(1)
                    
                except requests.exceptions.SSLError:
                    print(" [SSL Error]", end="")
                except requests.exceptions.ConnectionError:
                    print(" [Connection Error]", end="")
                except requests.exceptions.Timeout:
                    print(" [Timeout]", end="")
                except Exception as e:
                    print(f" [{type(e).__name__}]", end="")
        
        return False
    
    def test_alternative_api(self):
        """Test alternative API endpoints that might work"""
        
        alternative_endpoints = [
            {
                "name": "Roblox Economy API",
                "url": "https://economy.roblox.com/v1/assets/3360689775/details",
                "check": lambda r: "Name" in r.json() if r.status_code == 200 else False
            },
            {
                "name": "Roblox Catalog API v2",
                "url": "https://catalog.roblox.com/v2/search/items/details?Category=12&Subcategory=39&Limit=1",
                "check": lambda r: r.status_code == 200
            },
            {
                "name": "Roblox Games API",
                "url": "https://games.roblox.com/v1/games?universeIds=1",
                "check": lambda r: r.status_code == 200
            }
        ]
        
        print("\n🔧 Testing alternative APIs...")
        
        for endpoint in alternative_endpoints:
            print(f"  Testing {endpoint['name']}...", end=" ", flush=True)
            try:
                response = self.session.get(
                    endpoint['url'],
                    headers={"User-Agent": self.get_random_user_agent()},
                    timeout=10
                )
                
                if endpoint['check'](response):
                    print("✅ Working!")
                    return endpoint['name']
                else:
                    print(f"❌ Failed (HTTP {response.status_code})")
            except Exception as e:
                print(f"❌ Error: {type(e).__name__}")
        
        return None
    
    def find_working_proxy(self):
        """Find a working proxy"""
        print("\n🔌 Testing proxies...")
        
        for proxy in PROXIES:
            print(f"  Testing {proxy}...", end="", flush=True)
            if self.test_proxy(proxy):
                print(" ✅ Working!")
                self.working_proxy = proxy
                return True
            else:
                print(" ❌ Failed")
            
            time.sleep(0.5)
        
        return False
    
    def fetch_emotes_alternative(self):
        """Alternative method: Fetch known emote IDs from a public source"""
        print("\n🔄 Trying alternative method: Fetching from public emote lists...")
        
        # Known public emote list sources
        public_sources = [
            "https://raw.githubusercontent.com/7yd7/sniper-Emote/refs/heads/test/EmoteSniper.json",
            "https://raw.githubusercontent.com/7yd7/sniper-Emote/test/EmoteSniper.json",
            "https://raw.githubusercontent.com/7yd7/sniper-Emote/main/EmoteSniper.json"
        ]
        
        for source in public_sources:
            print(f"  Trying {source[:60]}...", end=" ", flush=True)
            try:
                response = self.session.get(
                    source,
                    headers={"User-Agent": self.get_random_user_agent()},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    emotes = data.get('data', [])
                    
                    if emotes:
                        print(f"✅ Got {len(emotes)} emotes!")
                        return emotes
                    else:
                        print("❌ Empty data")
                else:
                    print(f"❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {type(e).__name__}")
        
        return None
    
    def fetch_page(self, params, cursor=None):
        """Fetch a page of emotes"""
        if not self.working_proxy:
            return None
        
        url = f"{self.working_proxy}{BASE_ENDPOINT}"
        
        request_params = params.copy()
        if cursor:
            request_params["cursor"] = cursor
        
        for retry in range(MAX_RETRIES):
            try:
                self.stats["api_calls"] += 1
                
                response = self.session.get(
                    url,
                    params=request_params,
                    headers={"User-Agent": self.get_random_user_agent()},
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 429:
                    wait_time = 10 * (retry + 1)
                    print(f"\n  ⚠ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 403:
                    print(f"\n  ⚠ Forbidden (IP blocked?)")
                    self.stats["errors"] += 1
                    return None
                
                else:
                    self.stats["errors"] += 1
                    time.sleep(2)
                    
            except Exception as e:
                self.stats["errors"] += 1
                time.sleep(2)
        
        return None
    
    def process_item(self, item):
        """Process a single emote item"""
        self.stats["items_processed"] += 1
        
        try:
            emote_id = item.get('id') or item.get('assetId') or item.get('productId')
            
            if not emote_id:
                return None
            
            emote_id = str(emote_id)
            
            if emote_id == '0' or emote_id == '':
                return None
            
            if emote_id in self.existing_ids:
                return None
            
            if emote_id in self.all_fetched_ids:
                return None
            
            emote_name = item.get('name', '').strip()
            
            if not emote_name:
                emote_name = f"Emote_{emote_id}"
            
            emote_name = ' '.join(emote_name.split())
            
            self.all_fetched_ids.add(emote_id)
            
            return {
                "id": int(emote_id),
                "name": emote_name
            }
            
        except:
            return None
    
    def scan_config(self, config):
        """Scan all pages for a specific API configuration"""
        config_name = config["name"]
        params = config["params"]
        
        print(f"\n🔍 {config_name}")
        print("-" * 50)
        
        cursor = None
        pages_scanned = 0
        emotes_found = 0
        empty_pages = 0
        
        while pages_scanned < MAX_PAGES_PER_CONFIG:
            pages_scanned += 1
            self.stats["pages_scanned"] += 1
            
            if pages_scanned % 20 == 0:
                print(f"  📄 Page {pages_scanned}... ({emotes_found} new)")
            
            result = self.fetch_page(params, cursor)
            
            if not result:
                print(f"  ❌ Failed at page {pages_scanned}")
                break
            
            items = result.get('data', [])
            
            if not items:
                empty_pages += 1
                if empty_pages >= 3:
                    print(f"  ✓ No more items (page {pages_scanned})")
                    break
                continue
            else:
                empty_pages = 0
            
            for item in items:
                emote_data = self.process_item(item)
                if emote_data:
                    self.new_emotes.append(emote_data)
                    emotes_found += 1
                    
                    if emotes_found <= 5:
                        print(f"    ✨ NEW: {emote_data['name']} (ID: {emote_data['id']})")
                    elif emotes_found == 6:
                        print(f"    ... (hiding rest)")
            
            cursor = result.get('nextPageCursor')
            
            if not cursor:
                print(f"  ✓ End reached (page {pages_scanned})")
                break
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        self.stats["configs_scanned"] += 1
        print(f"  📊 Found {emotes_found} new emotes!")
        
        return emotes_found
    
    def save_emotes(self):
        """Save all emotes to JSON file"""
        all_emotes = self.new_emotes + self.existing_emotes
        
        seen_ids = set()
        unique_emotes = []
        
        for emote in all_emotes:
            emote_id = str(emote['id'])
            if emote_id not in seen_ids:
                seen_ids.add(emote_id)
                unique_emotes.append(emote)
        
        output = {
            "keyword": None,
            "totalItems": len(unique_emotes),
            "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}Z",
            "data": unique_emotes
        }
        
        with open(EMOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(unique_emotes)} emotes to {EMOTES_FILE}")
        
        return len(unique_emotes)
    
    def run(self):
        """Main sniper function"""
        start_time = time.time()
        
        print("")
        print("╔════════════════════════════════════════════════════════╗")
        print("║          🎀 PINKWARDS EMOTE SNIPER v4.0 🎀             ║")
        print(f"║  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                            ║")
        print("╚════════════════════════════════════════════════════════╝")
        
        # Create session
        self.create_session()
        
        # Load existing
        self.load_existing_emotes()
        
        # Try to find working proxy
        proxy_found = self.find_working_proxy()
        
        if proxy_found:
            # Use proxy method
            print(f"\n🌐 Using proxy: {self.working_proxy}")
            
            for i, config in enumerate(API_CONFIGS):
                print(f"\n[{i+1}/{len(API_CONFIGS)}]", end="")
                self.scan_config(config)
                time.sleep(1)
        else:
            # Fallback: Use alternative method
            print("\n⚠ No proxies working, trying alternative method...")
            
            external_emotes = self.fetch_emotes_alternative()
            
            if external_emotes:
                print(f"\n📥 Processing {len(external_emotes)} emotes from external source...")
                
                for item in external_emotes:
                    emote_data = self.process_item(item)
                    if emote_data:
                        self.new_emotes.append(emote_data)
                
                print(f"✅ Found {len(self.new_emotes)} new emotes!")
            else:
                print("\n❌ All methods failed!")
                print("   The database will remain unchanged.")
                print("   This might be due to:")
                print("   - GitHub Actions IP is blocked by Roblox")
                print("   - All proxy services are down")
                print("   - Network issues")
                
                # Still save to update timestamp
                self.save_emotes()
                return False
        
        # Save
        total_saved = self.save_emotes()
        
        # Stats
        elapsed = time.time() - start_time
        
        print("")
        print("╔════════════════════════════════════════════════════════╗")
        print("║                   📊 FINAL STATS                       ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"  • Before: {len(self.existing_emotes):,} emotes")
        print(f"  • After:  {total_saved:,} emotes")
        print(f"  • NEW:    {len(self.new_emotes):,} emotes")
        print(f"  • Time:   {elapsed:.1f} seconds")
        print("═" * 58)
        
        return len(self.new_emotes) > 0


def main():
    sniper = EmoteSniper()
    sniper.run()


if __name__ == "__main__":
    main()
