import requests
from bs4 import BeautifulSoup
import argparse
import json
import time
import random
from urllib.parse import urlparse
from rich import print as rprint 
from tools.shared_console import console

try:
    import trafilatura
except ImportError:
    trafilatura = None

MINIMUM_CONTENT_LENGTH = 3000 


def get_random_headers():
    user_agents = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"'
    }

def test_proxy(proxy_config):
    try:
        console.log(f"[yellow]Testing proxy: {proxy_config['https']}[/yellow]")
        test_response = requests.get(
            "https://httpbin.org/ip", 
            proxies=proxy_config, 
            headers=get_random_headers(),
            timeout=10
        )
        if test_response.status_code == 200:
            console.log("[green]✓ Proxy is working![/green]")
            return True
        else:
            console.log(f"[red]✗ Proxy returned status: {test_response.status_code}[/red]")
            return False
    except Exception as e:
        console.log(f"[red]✗ Proxy test failed: {str(e)}[/red]")
        return False

def clean_text(text):
    return ' '.join(text.strip().split())

def make_request_with_fallback(url: str):
    primary_proxy = {
        "http": "http://initditer89:initditer89@45.43.186.39:6257",
        "https": "http://initditer89:initditer89@45.43.186.39:6257"
    }
    
    console.log("[cyan]Strategy 1: Trying with primary proxy...[/cyan]")
    if test_proxy(primary_proxy):
        try:
            response = requests.get(url, headers=get_random_headers(), proxies=primary_proxy, timeout=20)
            response.raise_for_status()
            console.log("[green]✓ Primary proxy request successful![/green]")
            return response
        except Exception as e:
            console.log(f"[yellow]Primary proxy request failed: {e}[/yellow]")
    
    console.log("[cyan]Strategy 2: Trying direct connection...[/cyan]")
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(url, headers=get_random_headers(), timeout=20)
        response.raise_for_status()
        console.log("[green]✓ Direct connection successful![/green]")
        return response
    except Exception as e:
        console.log(f"[yellow]Direct connection failed: {e}[/yellow]")
    
    console.log("[cyan]Strategy 3: Trying with session and enhanced headers...[/cyan]")
    try:
        session = requests.Session()
        enhanced_headers = get_random_headers()
        enhanced_headers.update({
            "Referer": f"https://{urlparse(url).netloc}/",
            "Origin": f"https://{urlparse(url).netloc}"
        })
        session.headers.update(enhanced_headers)
        time.sleep(random.uniform(2, 4))
        response = session.get(url, timeout=25)
        response.raise_for_status()
        console.log("[green]✓ Session request successful![/green]")
        return response
    except Exception as e:
        console.log(f"[red]All strategies failed. Last error: {e}[/red]")
        return None 

def scrape_manual(url: str) -> dict:
    console.log(f"Starting scrape for URL: {url}")
    response = make_request_with_fallback(url)
    
    if not response:
        return {"error": "All fetching strategies failed. Could not retrieve content from the URL."}

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string.strip() if soup.title else "(no title)"
    
    console.log("[yellow]Trying Layer 1: BeautifulSoup...[/yellow]")
    content = ""
    try:
        main_selectors = ["article", "main", "[role='main']", ".content", ".post-content", 
                         ".entry-content", ".article-content", "#content", ".main-content"]
        
        main_content_area = next((soup.select_one(s) for s in main_selectors if soup.select_one(s)), soup.body)
        
        if main_content_area:
            for unwanted in main_content_area(["script", "style", "nav", "header", "footer", "aside", "form"]):
                unwanted.decompose()
            
            paragraphs = main_content_area.find_all(["p", "h2", "h3", "h4", "li", "div"])
            content_list = [clean_text(p.get_text()) for p in paragraphs if len(p.get_text(strip=True)) > 25]
            content = "\n".join(content_list)
        
        if len(content) > MINIMUM_CONTENT_LENGTH:
            console.log("[green]Layer 1 (BeautifulSoup) successfully found significant content.[/green]")
            return {"title": title, "content": content, "source": url, "domain": urlparse(url).netloc}
        else:
            console.log(f"[yellow]Layer 1 only found {len(content)} characters, below threshold {MINIMUM_CONTENT_LENGTH}.[/yellow]")

    except Exception as e:
        console.log(f"[red]Error in Layer 1: {e}[/red]")

    console.log("[cyan]Activating Layer 2: Trafilatura...[/cyan]")

    if not trafilatura:
        console.log("[red]Trafilatura is not installed. Returning best result from Layer 1.[/red]")
        return {
            "title": title,
            "content": content if content else "Scraping failed and Trafilatura not available.",
            "source": url,
            "domain": urlparse(url).netloc
        }
        
    try:
        trafilatura_content = trafilatura.extract(html_content, include_comments=False, include_tables=True)
        
        if trafilatura_content and len(trafilatura_content) > len(content):
            console.log("[green]Layer 2 (Trafilatura) found better content.[/green]")
            return {"title": title, "content": trafilatura_content, "source": url, "domain": urlparse(url).netloc}
        else:
            console.log("[yellow]Layer 2 did not find better content. Returning Layer 1 result.[/yellow]")
            return {
                "title": title,
                "content": content or "Failed to extract main content from this page.",
                "source": url,
                "domain": urlparse(url).netloc
            }
            
    except Exception as e:
        rprint(f"[red]Error in Layer 2: {e}[/red]")
        return {
            "title": title,
            "content": content if content else f"Total scraping failure. Last error: {e}",
            "source": url,
            "domain": urlparse(url).netloc
        }
