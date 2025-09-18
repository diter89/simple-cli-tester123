import requests
from bs4 import BeautifulSoup
import argparse
import json
from urllib.parse import urlparse
from rich import print as rprint 
from tools.shared_console import console


try:
    import trafilatura
except ImportError:
    trafilatura = None

MINIMUM_CONTENT_LENGTH = 30000


def clean_text(text):
    return ' '.join(text.strip().split())

def scrape_manual(url: str) -> dict:
    # proxies down
    """
    proxies = {
        "http": "http://initditer89:initditer89@45.43.186.39:6257",
        "https": "http://initditer89:initditer89@45.43.186.39:6257"
    }
    """

    headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    }

    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        html_content = res.text
    except requests.RequestException as e:
        console.log(f"[red] Failed to fetch URL: {e}[/red]")
        return {"error": str(e)}

    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string.strip() if soup.title else "(no title)"
    
    console.log("[yellow]Trying Layer 1: BeautifulSoup...[/yellow]")
    content = ""
    try:
        main_content_area = soup.find("article") or soup.find("main") or soup.body
        
        if main_content_area:
            paragraphs = main_content_area.find_all(["p", "h2", "h3", "li"])
            content_list = [clean_text(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > 10]
            content = "\n".join(content_list)
        
        if len(content) > MINIMUM_CONTENT_LENGTH:
            console.log("[green]Layer 1 (BeautifulSoup) successfully found significant content.[/green]")
            return {
                "title": title,
                "content": content,
                "source": url,
                "domain": urlparse(url).netloc
            }
        else:
            console.log(f"[yellow]Layer 1 only found {len(content)} characters, below threshold {MINIMUM_CONTENT_LENGTH}.[/yellow]")

    except Exception as e:
        console.log(f"[red]Error in Layer 1: {e}[/red]")

    console.log("[cyan]Activating Layer 2: Trafilatura...[/cyan]")

    if not trafilatura:
        console.log("[red]Trafilatura is not installed. Please run 'pip install trafilatura'. Returning best result from Layer 1.[/red]")
        return {
            "title": title,
            "content": content if content else "Scraping failed and Trafilatura not available.",
            "source": url,
            "domain": urlparse(url).netloc
        }
        
    try:
        trafilatura_content = trafilatura.extract(html_content, include_comments=False, include_tables=False)
        
        if trafilatura_content and len(trafilatura_content) > MINIMUM_CONTENT_LENGTH:
            console.log("[green]Layer 2 (Trafilatura) successfully found significant content.[/green]")
            return {
                "title": title,
                "content": trafilatura_content,
                "source": url,
                "domain": urlparse(url).netloc
            }
        else:
            console.log("[red]Layer 2 also failed to find significant content. Returning best available result.[/red]")
            final_content = content if len(content) > len(trafilatura_content or "") else trafilatura_content
            return {
                "title": title,
                "content": final_content or "Failed to extract main content from this page.",
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


