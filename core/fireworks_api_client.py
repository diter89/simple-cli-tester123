import requests
import json
from tools.shared_console import console
import os

CONFIG = {
    "fireworks": {
        "api_url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "api_key": os.getenv("FIREWORKS_API_KEY"),
        "default_model": "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new", 
        "max_tokens": 4096,
    },
    "huggingface": {
        "api_url": "https://router.huggingface.co/v1/chat/completions",
        "api_key": os.getenv("HF_API_KEY"),
        "default_model": "SentientAGI/Dobby-Mini-Unhinged-Plus-Llama-3.1-8B:featherless-ai",
        "max_tokens": 4096  
    }
}

CURRENT_MODEL = CONFIG["fireworks"]["default_model"] 
CURRENT_PROVIDER = "fireworks"

MODEL_UTAMA = CONFIG["fireworks"]["default_model"]

def generate_response(messages: list, stream: bool = False, model: str = None, temperature: float = 0.7, response_format: dict = None, layanan: str = None, **kwargs):
    
    if layanan is None:
        layanan = CURRENT_PROVIDER
    
    if layanan not in CONFIG:
        error_msg = f"\n[ERROR] Service '{layanan}' is not recognized. Available services: {list(CONFIG.keys())}"
        console.log(f"[bold red]API Client Config Error:[/bold red] {error_msg}")
        yield error_msg
        return

    cfg = CONFIG[layanan]
    api_url = cfg["api_url"]
    api_key = cfg["api_key"]
    
    if model is None:
        model_to_use = CURRENT_MODEL if layanan == CURRENT_PROVIDER else cfg["default_model"]
    else:
        model_to_use = model

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model_to_use,
        "max_tokens": cfg["max_tokens"], 
        "temperature": temperature,
        "messages": messages,
        "stream": stream
    }

    payload.update(kwargs)

    if response_format:
        if layanan == "fireworks":
            payload["response_format"] = response_format
        else:
            console.log(f"[yellow]Warning:[/yellow] Parameter 'response_format' is not supported by service '{layanan}' and will be ignored.")
        
    headers["Accept"] = "text/event-stream" if stream else "application/json"

    try:
        # --- Streaming Mode ---
        if stream:
            with requests.post(api_url, headers=headers, json=payload, stream=True, timeout=60) as response:
                response.raise_for_status()
                for chunk in response.iter_lines():
                    if chunk:
                        decoded_chunk = chunk.decode('utf-8')
                        if decoded_chunk.startswith('data: '):
                            data_str = decoded_chunk[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        
        # --- Non-Streaming Mode ---
        else:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            response_data = response.json()
            yield response_data["choices"][0]["message"]["content"]

    # --- Error Handling ---
    except requests.exceptions.RequestException as e:
        console.log(f"[bold red]{layanan.capitalize()} API Client Error:[/bold red] Failed to connect to API. Details: {e}")
        yield f"\n[ERROR] Sorry, there's a connection problem to {layanan.capitalize()} server. Please try again later."
    except Exception as e:
        console.log(f"[bold red]{layanan.capitalize()} API Client Critical Error:[/bold red] {e}")
        yield f"\n[ERROR] An unexpected error occurred in the system."

def get_current_model_config():
    return {
        "provider": CURRENT_PROVIDER,
        "model": CURRENT_MODEL,
        "config": CONFIG.get(CURRENT_PROVIDER, {}),
        "available_providers": list(CONFIG.keys())
    }

def update_model_config(model_path: str, provider: str):
    global CURRENT_MODEL, CURRENT_PROVIDER
    
    if provider not in CONFIG:
        console.log(f"[red]Error: Provider '{provider}' not available. Available: {list(CONFIG.keys())}[/red]")
        return False
    
    try:
        CURRENT_MODEL = model_path
        CURRENT_PROVIDER = provider
        console.log(f"[green]Model configuration updated: {provider}/{model_path.split('/')[-1]}[/green]")
        return True
    except Exception as e:
        console.log(f"[red]Error updating model config: {e}[/red]")
        return False
