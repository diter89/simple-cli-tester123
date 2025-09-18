from tools.shared_console import console
import json
import os
from typing import List, Dict, Optional
from tools.lang_utils import detect_target_language_from_messages

try:
    from tools.tweeter_toolkit.twettgetdesc import TweetScraper
    from tools.tweeter_toolkit.credential import load_credentials
    from core.fireworks_api_client import generate_response
except ImportError as e:
    console.log(f"[red]Import error: {e}[/red]")
    def load_credentials(path): return None
    def generate_response(messages, stream, temperature): return ["Error: LLM client not found."]

VERBOSE = False

def _vlog(message: str):
    if VERBOSE:
        console.log(message)

def validate_credentials(credentials):
    if not credentials:
        return False, "Credentials object is None or empty"
    
    required_fields = ["authorization", "x-csrf-token", "cookie", "user-agent"]
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in credentials:
            missing_fields.append(field)
        elif not credentials[field] or credentials[field].strip() == "":
            empty_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    if empty_fields:
        return False, f"Empty required fields: {', '.join(empty_fields)}"
    
    return True, "All credentials are valid"

def load_and_validate_credentials():
    credential_paths = [
        "result.json",
        "credentials.json", 
        "config/result.json",
        "config/credentials.json",
        os.path.expanduser("~/.twitter_credentials.json")
    ]
    
    _vlog("[yellow]Attempting to load credentials from multiple paths...[/yellow]")
    
    for path in credential_paths:
        if os.path.exists(path):
            _vlog(f"[blue]Trying to load from: {path}[/blue]")
            try:
                credentials = load_credentials(path)
                if credentials:
                    is_valid, message = validate_credentials(credentials)
                    if is_valid:
                        _vlog(f"[green]✓ Valid credentials loaded from: {path}[/green]")
                        return credentials, None
                    else:
                        _vlog(f"[yellow]Invalid credentials in {path}: {message}[/yellow]")
            except Exception as e:
                console.log(f"[red]Error loading {path}: {e}[/red]")
    
    return None, "No valid credentials found in any of the expected paths"

def _detect_target_language(messages: Optional[List[Dict]]) -> str:
    return detect_target_language_from_messages(messages)

def run_generative_commenter(tweet_id: str, messages: Optional[List[Dict]] = None):

    _vlog(f"[green]Persona 'generative_commenter' v2.0 starting to process Tweet ID: {tweet_id}[/green]")
    
    try:
        _vlog("[yellow]Loading and validating Twitter credentials...[/yellow]")
        credentials, error_msg = load_and_validate_credentials()
        
        if not credentials:
            console.log(f"[red]Failed to load valid credentials: {error_msg}[/red]")
            yield f"Sorry, I could not load valid Twitter credentials. Error: `{error_msg}`\n\n"
            yield f"Please ensure your result.json file exists with: authorization, x-csrf-token, cookie, user-agent"
            return
        
        _vlog("[green]✓ All credentials validated successfully[/green]")
        
        _vlog("[yellow]...Fetching tweet content...[/yellow]")
        
        yield f"### 🐦 Twitter Reply Generator\n"
        yield f"**Tweet ID:** {tweet_id}\n\n"
        yield f"**Fetching tweet content...**\n"
        
        try:
            scraper = TweetScraper(
                authorization=credentials["authorization"],
                csrf_token=credentials["x-csrf-token"], 
                cookie=credentials["cookie"],
                user_agent=credentials["user-agent"]
            )
            
            tweet_data = scraper.get_tweet_description(tweet_id)
            
            if tweet_data["status"] != "success":
                error_msg = tweet_data.get("message", "Unknown error")
                console.log(f"[red]Failed to fetch tweet: {error_msg}[/red]")
                yield f"\n❌ **Error:** Could not fetch tweet content. {error_msg}"
                return
            
            tweet_description = tweet_data["description"]
            _vlog("[green]✓ Tweet content fetched successfully[/green]")
            
        except Exception as e:
            console.log(f"[red]Error fetching tweet: {e}[/red]")
            yield f"\n❌ **Error:** Failed to fetch tweet content: {str(e)}"
            return
        
        yield f"\n**Original Tweet:**\n> {tweet_description}\n\n"
        
        _vlog("[yellow]...Generating intelligent reply suggestions...[/yellow]")
        yield f"**Generating reply suggestions...**\n"
        
        target_language = _detect_target_language(messages)
        recent_context = "\n".join([f"{m['role']}: {m['content']}" for m in (messages or [])[-4:]]) if messages else ""
        
        reply_generation_prompt = f"""
        You are a skilled social media engagement specialist. Generate thoughtful, engaging replies to this Twitter/X post.
        
        LANGUAGE: {target_language} (write all replies in this language)
        
        RECENT CONVERSATION CONTEXT (may include user preferences like language):
        ---
        {recent_context}
        ---
        
        ORIGINAL TWEET:
        ---
        {tweet_description}
        ---
        
        INSTRUCTIONS:
        1. Generate exactly 10 different reply options
        2. Each reply should be engaging, conversational, under 280 characters
        3. Vary the tone (supportive, questioning, adding value)
        4. Avoid generic responses
        5. Make replies that spark conversation
        6. Use appropriate language and tone based on LANGUAGE and context
        
        FORMAT:
        1. [First reply]
        2. [Second reply]
        3. [Third reply]
        ... (continue to 10)
        
        GENERATE 10 REPLY OPTIONS:
        """
        
        messages = [{"role": "user", "content": reply_generation_prompt}]
        
        try:
            ai_response = ""
            for chunk in generate_response(messages, stream=True, temperature=0.7):
                if chunk:
                    ai_response += chunk
                    yield chunk
            
            if not ai_response.strip():
                console.log("[red]AI response is empty[/red]")
                yield "\n❌ **Error:** AI failed to generate reply suggestions"
                return
                
        except Exception as e:
            console.log(f"[red]Error generating AI response: {e}[/red]")
            yield f"\n❌ **Error:** Failed to generate suggestions: {str(e)}"
            return
        
        _vlog("[green]✓ Reply suggestions streamed successfully[/green]")
        
        yield f"\n\n---\n\n**📝 How to Use:**\n"
        yield f"1. Choose your preferred reply from the streamed list above\n"
        yield f"2. Copy the text\n"
        yield f"3. Open: https://x.com/anyuser/status/{tweet_id}\n"
        yield f"4. Paste and post manually\n\n"
        yield f"**💡 Tips:** Choose replies that match your voice; consider timing for engagement.\n\n"
        
        _vlog(f"[green]Generative commenter v2.0 successfully processed Tweet ID: {tweet_id}[/green]")
        
        yield f"---\n\n**Source:** https://x.com/anyuser/status/{tweet_id}"
        
    except Exception as e:
        console.log(f"[red]Critical error in generative_commenter persona for Tweet ID '{tweet_id}': {e}[/red]")
        yield f"Sorry, a critical error occurred while processing Tweet ID `{tweet_id}`: {str(e)}"

def run_reply_commentar_persona(tweet_id: str):
    return run_generative_commenter(tweet_id)

# Test function
def main():
    import sys
    
    if len(sys.argv) < 2:
        console.log("[red]Usage: python persona_generative_komentar.py <tweet_id>[/red]")
        console.log("[yellow]Example: python persona_generative_komentar.py 1942670167894548763[/yellow]")
        return
    
    tweet_id = sys.argv[1]
    console.log(f"[blue]Testing generative_commenter persona with Tweet ID: {tweet_id}[/blue]")
    
    for output in run_generative_commenter(tweet_id):
        print(output, end="")

if __name__ == "__main__":
    main()
