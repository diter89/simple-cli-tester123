import os
import time
import pickle
import requests
import random
from datetime import datetime
from urllib.parse import quote
from typing import Dict, Optional
from bs4 import BeautifulSoup
from faker import Faker


from tools.shared_console import console

faker = Faker()

CACHE_DIR = ".search_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

PROXIES_LIST = [
    "23.95.150.145:6114:initditer89:initditer89",
    "45.38.107.97:6014:initditer89:initditer89",
    "45.43.186.39:6257:initditer89:initditer89",
    "64.137.96.74:6641:initditer89:initditer89",
    "107.172.163.27:6543:initditer89:initditer89",
    "136.0.207.84:6661:initditer89:initditer89",
    "142.147.128.93:6593:initditer89:initditer89",
    "154.203.43.247:5536:initditer89:initditer89",
    "198.23.239.134:6540:initditer89:initditer89",
    "216.10.27.159:6837:initditer89:initditer89"
]

def generate_headers() -> Dict[str, str]:
    return {
        "User-Agent": faker.user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9,id-ID;q=0.8",
        "X-Forwarded-For": faker.ipv4_public(),
        "Connection": "keep-alive"
    }

def get_random_proxy() -> Dict[str, str]:
    proxy = random.choice(PROXIES_LIST)
    ip, port, username, password = proxy.split(":")
    proxy_url = f"http://{username}:{password}@{ip}:{port}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }

def get_cache_key(query: str) -> str:
    return str(hash(query))

def load_from_cache(cache_key: str) -> Optional[Dict]:
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                cached = pickle.load(f)
            fetched_at = cached["searchParameters"].get("fetched_at")
            if isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at)
            if (datetime.now() - fetched_at).total_seconds() < 24 * 3600:
                console.log(f"Loaded cached results for query hash: [cyan]{cache_key}[/cyan]")
                return cached
    except Exception as e:
        console.log(f"[bold red]Error loading cache:[/bold red] {str(e)}")
    return None

def save_to_cache(cache_key: str, data: Dict) -> None:
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    try:
        data["searchParameters"]["fetched_at"] = data["searchParameters"]["fetched_at"].isoformat()
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        console.log(f"Saved results to cache: [dim]{cache_file}[/dim]")
    except Exception as e:
        console.log(f"[bold red]Error saving cache:[/bold red] {str(e)}")

def clean_text(text: str) -> str:
    return ' '.join(text.strip().split()) if text else ""

def fetch_search_page(url: str, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None) -> requests.Response:
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15.0, allow_redirects=True)
        response.raise_for_status()
        console.log(f":link: Successfully fetched URL: [link={url}]{url}[/link]")
        return response
    except requests.exceptions.RequestException as e:
        console.log(f"[bold red]Request Error:[/bold red] {str(e)}")
        raise
    except Exception as e:
        console.log(f"[bold red]General Error:[/bold red] {str(e)}")
        raise

def brave_search(query: str, limit: int = 12,filter_domain: Optional[str] = None) -> Dict:
    cache_key = get_cache_key(query)
    if cached_result := load_from_cache(cache_key):
        return cached_result

    headers = generate_headers()
    encoded_query = quote(query)
    url = f"https://search.brave.com/search?q={encoded_query}"
    start = time.time()
    
    proxies = get_random_proxy()
    
    try:
        response = fetch_search_page(url, headers, proxies=proxies)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        console.log(f"[bold red]Failed to fetch search page:[/bold red] {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "searchParameters": {
                "query": query,
                "engine": "brave",
                "gl": "id",
                "hl": "id-id",
                "type": "search",
                "fetched_at": datetime.now().isoformat(),
                "latency_ms": int((time.time() - start) * 1000)
            },
            "organic_results": [],
            "debug": {
                "user_agent": headers["User-Agent"],
                "ip": headers["X-Forwarded-For"],
                "result_count": 0
            }
        }

    organic_results = []
    for item in soup.find_all("div", class_=["snippet", "news-snippet", "video-snippet", "card"]):
        if len(organic_results) >= limit:
            break

        a_tag = item.find("a", href=True)
        if not a_tag or not a_tag['href'].startswith(("http://", "https://")):
            continue

        result_url = a_tag['href']
        if filter_domain and filter_domain not in result_url:
            continue

        title_elem = item.find("div", class_=["title", "snippet-title"]) or a_tag
        title = clean_text(title_elem.get_text(strip=True)) if title_elem else ""
        snippet_elem = item.find("div", class_=["snippet-content", "description", "snippet-description"])
        snippet = clean_text(snippet_elem.get_text(strip=True)) if snippet_elem else clean_text(item.get_text(separator=' ', strip=True))

        date_elem = item.find("span", class_=["age", "date", "time", "snippet-age"])
        date = clean_text(date_elem.get_text(strip=True)) if date_elem else None

        if len(snippet) < 30 or len(title) < 5:
            continue

        result = {
            "position": len(organic_results) + 1,
            "title": title,
            "link": result_url,
            "snippet": snippet,
            "domain": result_url.split("/")[2]
        }
        if date:
            result["date"] = date

        organic_results.append(result)

    result_data = {
        "status": "success",
        "searchParameters": {
            "query": query,
            "engine": "brave",
            "gl": "id",
            "hl": "id-id",
            "type": "search",
            "fetched_at": datetime.now(),
            "latency_ms": int((time.time() - start) * 1000)
        },
        "organic_results": organic_results,
        "debug": {
            "user_agent": headers["User-Agent"],
            "ip": headers["X-Forwarded-For"],
            "result_count": len(organic_results)
        }
    }

    save_to_cache(cache_key, result_data)
    return result_data
