import json
from tools.shared_console import console
from rich.panel import Panel
from rich.markdown import Markdown
from typing import List, Dict, Optional
from tools.lang_utils import detect_target_language_from_messages

def _detect_lang_prioritize_last(messages: Optional[List[Dict]]) -> str:
    try:
        if messages:
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    content_lower = (msg.get('content', '') or '').lower()
                    if any(k in content_lower for k in ["bahasa indonesia", "gunakan bahasa indonesia", "tolong jelaskan dalam bahasa indonesia"]):
                        return "indonesian"
                    if any(k in content_lower for k in ["español", "spanish"]):
                        return "spanish"
                    if any(k in content_lower for k in ["français", "french"]):
                        return "french"
                    if any(k in content_lower for k in ["português", "portuguese"]):
                        return "portuguese"
                    if any(k in content_lower for k in ["русский", "russian"]):
                        return "russian"
                    if any(k in content_lower for k in ["हिंदी", "hindi"]):
                        return "hindi"
                    if any(k in content_lower for k in ["العربية", "arabic"]):
                        return "arabic"
                    if any(k in content_lower for k in ["বাংলা", "bengali", "bangla"]):
                        return "bengali"
                    if any(k in content_lower for k in ["中文", "汉语", "mandarin", "chinese", "zh-cn"]):
                        return "chinese"
                    if any(k in content_lower for k in ["اردو", "urdu"]):
                        return "urdu"
                    break
    except Exception:
        pass
    return detect_target_language_from_messages(messages)

from tools.searchAddrsClean import SearchAddrsInfo
from core.fireworks_api_client import generate_response
from tools.wallet_cache_handler import save_to_cache


def create_intelligent_summary(result_dict: dict, top_n_assets=15) -> dict:

    portfolio = result_dict.get('portfolio', [])
    holdings_by_chain = result_dict.get('holdings_by_chain', {})

    sorted_assets = sorted(portfolio, key=lambda item: item.get('value_usd', 0), reverse=True)
    sorted_chains = sorted(
        holdings_by_chain.items(), 
        key=lambda item: item[1].get('total_value_usd', 0), 
        reverse=True
    )

    summary = {
        "overall_metrics": {
            "total_portfolio_value_usd": sum(item.get('value_usd', 0) for item in portfolio),
            "distinct_token_count": len(portfolio),
            "total_chain_count": len(holdings_by_chain)
        },
        "top_chains_by_value": {
            chain: value['total_value_usd']
            for chain, value in sorted_chains
        },
        "top_assets_by_value": [
            {
                "token": asset['token'],
                "chain": asset['chain'],
                "value_usd": asset.get('value_usd', 0),
            }
            for asset in sorted_assets[:top_n_assets]
        ]
    }
    return summary

def create_analysis_prompt(summary_json: str, address: str, target_language: str) -> str:

    prompt = f"""
You are an expert crypto portfolio analyst and professional trader. Your tone is sharp, insightful, and professional, delivered in {target_language}.

**CRITICAL VALUE FORMATTING INSTRUCTIONS:**
- All `value_usd` numbers in the JSON are EXACT USD dollar amounts (NOT millions, thousands, or any other unit)
- If you see `"value_usd": 2.79`, display it as exactly `$2.79` (NOT $2.79M, NOT $2.79K)
- If you see `"value_usd": 0.13`, display it as exactly `$0.13`
- DO NOT add any suffixes like M (millions), K (thousands), or B (billions) to these values
- These are small portfolio values - display them as-is with proper dollar formatting
- Example formatting: $2.79, $0.13, $0.02, $0.00

You will be given an **intelligent summary** of a crypto wallet's holdings, highlighting only the most significant assets and chain presence.
Your task is to analyze this summary and generate a concise, insightful report in Markdown format.

**Address:** `{address}`

**Intelligent Wallet Summary (JSON):**
```json
{summary_json}```

**Your Report Structure (Use Markdown Headers and Rich Formatting):**

# 📊 Executive Summary
*   State total portfolio value using EXACT dollar amounts from the data.
*   Give 1-2 sentences conclusion about this wallet's characteristics.

## 📈 Asset Allocation & Diversification
*   Present top 5 assets in Markdown table format with EXACT values (no M/K suffixes).
*   Based on `distinct_token_count` and value distribution, comment on diversification level.

## 🌐 Ecosystem Focus (Chain Presence)
*   Identify dominant blockchain from `top_chains_by_value`.
*   Explain what this means.

## ⚖️ Risk Profile
*   Based on `top_assets_by_value` composition, give brief assessment of risk profile (Low, Medium, High) and explain why.

## 🔍 Interesting Observations (Trader Insight)
*   Use `distinct_token_count` and `total_chain_count` to provide insights.
*   If there are interesting assets in Top 15, mention them.

# 📌 Brief Recommendations
* Give 1-2 actionable recommendations.

**REMEMBER: Use exact USD values from the JSON data - no M/K/B suffixes!**
LANGUAGE: {target_language} (write the entire report in this language)
"""
    return prompt

def run_wallet_analysis_persona(address: str, messages: Optional[List[Dict]] = None):
    
    try:
        searcher = SearchAddrsInfo()
        raw_data_dict = searcher.query(address)

        if not raw_data_dict or not isinstance(raw_data_dict, dict) or not raw_data_dict.get('portfolio'):
            return {
                "report_markdown": f"No portfolio data found for address `{address}`.", 
                "cache_ready": False
            }
 
        save_to_cache(address, raw_data_dict)

        intelligent_summary = create_intelligent_summary(raw_data_dict)
        summary_json_str = json.dumps(intelligent_summary, indent=2, ensure_ascii=False)

        target_language = _detect_lang_prioritize_last(messages)
        analysis_prompt = create_analysis_prompt(summary_json_str, address, target_language)
        messages = [{"role": "user", "content": analysis_prompt}]
        
        trader_analysis_md = "".join(generate_response(messages, temperature=0.2))

        final_report = f"# 📈 Trader Analysis Report for `{address}`\n\n{trader_analysis_md}"
        

        return {
            "report_markdown": final_report,
            "address": address,
            "cache_ready": True
        }

    except Exception as e:
        console.log(f"[red]Error in wallet_analyzer persona for '{address}': {e}[/red]")
        return {
            "report_markdown": f"Sorry, an internal error occurred while analyzing address `{address}`.",
            "cache_ready": False
        }

def run_wallet_analysis_persona_stream(address: str, messages: Optional[List[Dict]] = None):
    try:
        yield f"# 📈 Trader Analysis Report for `{address}`\n\n"

        searcher = SearchAddrsInfo()
        raw_data_dict = searcher.query(address)

        if not raw_data_dict or not isinstance(raw_data_dict, dict) or not raw_data_dict.get('portfolio'):
            console.log(f"[red]No portfolio data for: {address}[/red]")
            yield f"[yellow]No portfolio data found for address `{address}`.[/yellow]"
            return

        save_to_cache(address, raw_data_dict)

        intelligent_summary = create_intelligent_summary(raw_data_dict)
        summary_json_str = json.dumps(intelligent_summary, indent=2, ensure_ascii=False)

        max_chars = 12000
        if len(summary_json_str) > max_chars:
            summary_json_str = summary_json_str[:max_chars] + "\n...[truncated]..."

        target_language = _detect_lang_prioritize_last(messages)
        analysis_prompt = create_analysis_prompt(summary_json_str, address, target_language)
        messages = [{"role": "user", "content": analysis_prompt}]

        try:
            for chunk in generate_response(messages, stream=True, temperature=0.2):
                if not chunk:
                    continue
                yield chunk if isinstance(chunk, str) else str(chunk)
        except Exception as stream_err:
            console.log(f"[red]Streaming error: {stream_err}[/red]")
            yield "\n\n[red]Streaming terminated due to an internal error.[/red]"
            return

        console.log(f"[green]Streaming analysis completed for: {address}[/green]")
        yield "\n\n---\n\nAnalysis complete."

    except Exception as e:
        console.log(f"[red]Error in wallet_analyzer (stream) for '{address}': {e}[/red]")
        yield f"Sorry, an internal error occurred while analyzing address `{address}`."
