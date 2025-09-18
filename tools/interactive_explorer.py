import json
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.panel import Panel
from rich.markdown import Markdown
from tools.shared_console import console
from tools.wallet_cache_handler import load_from_cache
from core.fireworks_api_client import generate_response
from tools.config_styles import inquirerstyle
from InquirerPy import get_style
from typing import List, Dict, Optional
from tools.lang_utils import detect_target_language_from_messages

def display_asset_details(assets: list):
    output_str = ""
    for i, asset in enumerate(assets, 1):
        output_str += f"\n--- Asset #{i} ---\n"
        output_str += f"Token: [bold]{asset.get('token')}[/bold] on [italic]{asset.get('chain')}[/italic]\n"
        output_str += f"Value (USD): ${asset.get('value_usd', 0):,.4f}\n"
        output_str += f"Amount: {asset.get('holding', 0):.8f}\n"
        
        change = asset.get('change_24h_percent', 0)
        color = "green" if change >= 0 else "red"
        output_str += f"24h Change: [{color}]{change:+.2f}%[/{color}]\n"

    console.log(Panel(output_str.strip(), title="🔍 Selected Asset Details", border_style="yellow"))

def analyze_selected_assets_with_llm(assets: list, target_language: str):
    if not assets:
        return

    console.log("[yellow]... Analyzing selected assets with LLM ...[/yellow]")
    
    assets_summary = json.dumps(assets, indent=2)
    
    prompt = f"""
You are a crypto analyst. Based on the following JSON data, provide a brief and sharp analysis in 1-3 paragraphs for the assets selected by the user from their portfolio. Focus on the most interesting aspects or potential risks.

LANGUAGE: {target_language} (write the entire analysis in this language)

Selected Asset Data:
```json
{assets_summary}
```
"""
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        llm_analysis = "".join(generate_response(messages, temperature=0.1))
        console.print(Panel(Markdown(llm_analysis), title="🧠 Smart Analysis", border_style="cyan"))
    except Exception as e:
        console.log(f"[red]Failed to get LLM analysis: {e}[/red]")

def run_interactive_session(address: str, messages: Optional[List[Dict]] = None):
    raw_data = load_from_cache(address)
    if not raw_data or 'portfolio' not in raw_data:
        console.print("[red]Failed to load cache data for interactive session.[/red]")
        return
    
    portfolio = sorted(raw_data['portfolio'], key=lambda item: item.get('value_usd', 0), reverse=True)

    portfolio_choices = []
    for item in portfolio:
        display_text = f"{item['token']} ({item['chain']}) - ${item.get('value_usd', 0):,.2f}"
        portfolio_choices.append(Choice(value=item, name=display_text))

    portfolio_choices.insert(0, Choice(value="exit_session", name="Continue Chat (Finish Analysis)"))

    target_language = detect_target_language_from_messages(messages)

    while True:
        selected_assets = inquirer.fuzzy(
            message="Select assets to analyze: ",
            choices=portfolio_choices,
            qmark=":",
            amark=":",
            style=get_style(inquirerstyle()),
            max_height="70%",
            border=True,
            multiselect=True,
            instruction="> Press space to select, or choose 'Continue Chat' to exit.",
        ).execute()
        
        if not selected_assets or "exit_session" in selected_assets:
            break

        display_asset_details(selected_assets)
        
        want_analysis = inquirer.confirm(
            message="Perform smart analysis with LLM for these assets?",
            default=True
        ).execute()

        if want_analysis:
            analyze_selected_assets_with_llm(selected_assets, target_language)
            
        console.log("[bold]You can select other assets or 'Continue Chat' to exit.[/bold]")
