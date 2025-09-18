from rich.table import Table
from rich.prompt import Prompt
from rich import box 
from tools.shared_console import console
import core.fireworks_api_client as fw_client

# Manual input model list - easy to maintain
AVAILABLE_MODELS = {
    "fireworks": [
        {
            "id": 1,
            "name": "dobby-unhinged-llama-3-3-70b-new",
            "full_path": "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
            "description": "Unhinged Personality - Casual Chat",
            "category": "Chat"
        },
        {
            "id": 2, 
            "name": "gpt-oss-120b",
            "full_path": "accounts/fireworks/models/gpt-oss-120b",
            "description": "Large Model - General Purpose",
            "category": "General"
        },
        {
            "id": 3,
            "name": "kimi-k2-instruct",
            "full_path": "accounts/fireworks/models/kimi-k2-instruct", 
            "description": "Instruction Following - Analytical",
            "category": "Analysis"
        },
        {
            "id": 4,
            "name": "dobby-mini-unhinged-plus-8b",
            "full_path": "accounts/sentientfoundation-serverless/models/dobby-mini-unhinged-plus-llama-3-1-8b",
            "description": "Mini Unhinged - Fast & Efficient",
            "category": "Fast"
        }
    ],
    "huggingface": [
        {
            "id": 5,
            "name": "dobby-mini-unhinged-hf",
            "full_path": "SentientAGI/Dobby-Mini-Unhinged-Plus-Llama-3.1-8B:featherless-ai",
            "description": "HuggingFace Hosted - Alternative Provider",
            "category": "Alternative"
        }
    ]
}

def show_model_selection():
    """Display rich table for model selection and handle user choice"""
    console.print()
    
    table = Table(title="🤖 [bold cyan]Available Models[/bold cyan]", show_header=True, header_style="bold magenta",expand=True,box=box.SQUARE_DOUBLE_HEAD)
    table.add_column("ID", style="cyan", no_wrap=True, justify="center")
    table.add_column("Provider", style="magenta", justify="center")
    table.add_column("Model Name", style="green")
    table.add_column("Category", style="yellow", justify="center")
    table.add_column("Description", style="white")
    
    current_model = getattr(fw_client, 'CURRENT_MODEL', fw_client.CONFIG["fireworks"]["default_model"])
    current_provider = getattr(fw_client, 'CURRENT_PROVIDER', "fireworks")
    
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            model_name = model["name"]
            if model["full_path"] == current_model and provider == current_provider:
                model_name = f"[bold green]● {model['name']}[/bold green] [dim](current)[/dim]"
            
            table.add_row(
                str(model["id"]),
                provider.title(),
                model_name,
                model["category"],
                model["description"]
            )
    
    console.print(table)
    console.print()
    
    try:
        choice = Prompt.ask(
            "[bold cyan]Select model ID[/bold cyan] [dim](or 'c' to cancel)[/dim]",
            default="c"
        )
        
        if choice.lower() == 'c':
            console.print("[yellow]Model selection cancelled.[/yellow]")
            return None
            
        model_id = int(choice)
        return get_model_by_id(model_id)
        
    except ValueError:
        console.print("[red]Invalid input. Please enter a valid model ID.[/red]")
        return None
    except KeyboardInterrupt:
        console.print("[yellow]Model selection cancelled.[/yellow]")
        return None

def get_model_by_id(model_id):
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            if model["id"] == model_id:
                return {
                    "provider": provider,
                    "model_path": model["full_path"],
                    "name": model["name"],
                    "category": model["category"],
                    "description": model["description"]
                }
    return None

def update_current_model(model_info):
    if not model_info:
        return False
        
    try:
        fw_client.CURRENT_MODEL = model_info["model_path"]
        fw_client.CURRENT_PROVIDER = model_info["provider"]
        
        console.print()
        console.print(f"✅ [bold green]Model successfully updated![/bold green]")
        console.print(f"📋 [cyan]Name:[/cyan] [white]{model_info['name']}[/white]")
        console.print(f"📡 [cyan]Provider:[/cyan] [magenta]{model_info['provider'].title()}[/magenta]") 
        console.print(f"🏷️  [cyan]Category:[/cyan] [yellow]{model_info['category']}[/yellow]")
        console.print(f"📝 [cyan]Description:[/cyan] [dim]{model_info['description']}[/dim]")
        console.print()
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error updating model:[/bold red] {e}")
        return False

def get_current_model_info():
    """Get info about currently selected model"""
    current_model = getattr(fw_client, 'CURRENT_MODEL', fw_client.CONFIG["fireworks"]["default_model"])
    current_provider = getattr(fw_client, 'CURRENT_PROVIDER', "fireworks")
    
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            if model["full_path"] == current_model and provider == current_provider:
                return {
                    "name": model["name"],
                    "provider": provider,
                    "category": model["category"],
                    "description": model["description"]
                }
    
    return {
        "name": "Unknown Model",
        "provider": current_provider,
        "category": "Unknown",
        "description": current_model
    }
