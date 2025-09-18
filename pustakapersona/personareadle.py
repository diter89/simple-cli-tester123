from tools.shared_console import console
try:
    from tools.readle import scrape_manual
    from core.fireworks_api_client import generate_response
except ImportError:
    def scrape_manual(url: str): return {"error": "Core function not found."}
    def generate_response(messages, stream, temperature): return ["Error: LLM client not found."]
from typing import List, Dict, Optional
from tools.lang_utils import detect_target_language_from_messages

VERBOSE = False

def _vlog(message: str):
    if VERBOSE:
        console.log(message)


def _detect_target_language(messages: Optional[List[Dict]]) -> str:
    return detect_target_language_from_messages(messages)

def run_readle_persona(url: str, messages: Optional[List[Dict]] = None):
    _vlog(f"[green]Persona 'readle' v2.0 starting to process URL: {url}[/green]")
    
    try:
        scraped_data = scrape_manual(url)
        if not scraped_data or 'error' in scraped_data or not scraped_data.get('content'):
            error_message = scraped_data.get('error', 'Content could not be extracted.')
            console.log(f"[red]Readle scrape failed for {url}: {error_message}[/red]")
            yield f"Sorry, I could not fetch data from that URL. Error: `{error_message}`"
            return
        
        _vlog(f"[yellow]...Scraping successful. Now generating intelligent summary...[/yellow]")
        
        title = scraped_data.get('title', 'No Title')
        raw_content = scraped_data.get('content', '')
        target_language = _detect_target_language(messages)
        summarization_prompt = f"""
        You are a highly skilled business and technology analyst.
        Your task is to read raw text extracted from a web page and transform it into a clear, insightful, and easy-to-understand summary.
        
        RAW TEXT FROM WEBSITE:
        ---
        {raw_content}
        ---
        
        INSTRUCTIONS:
        1. Identify and extract the most important data points (e.g.: funding, investors, founders, core technology).
        2. Rewrite these points into a brief narrative format that flows well.
        3. Provide a brief conclusion or analysis about what this data means (e.g.: "This shows strong growth...").
        4. Don't just copy the raw text.
        5. LANGUAGE: {target_language} (write the summary in this language)
        
        YOUR ANALYSIS RESULT:
        """
        
        messages = [{"role": "user", "content": summarization_prompt}]

        yield f"### 📖 Intelligent Analysis from Web Page\n\n"
        yield f"**Title:** {title}\n\n"
        yield f"**Analytical Summary:**\n"

        for chunk in generate_response(messages, stream=True, temperature=0.2):
            if chunk:
                yield chunk

        _vlog(f"[green]Readle v2.0 successfully summarized {url}[/green]")

        yield f"\n\n---\n\n**Source:** {url}"
        
    except Exception as e:
        console.log(f"[red]Critical error in readle persona for '{url}': {e}[/red]")
        yield f"Sorry, a critical error occurred while running readle persona: {str(e)}"
