import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from tools.shared_console import console
from .fireworks_api_client import generate_response, MODEL_UTAMA


@dataclass
class RouterDecision:
    tool: str
    query: Optional[str]
    confidence: float
    reasoning: str
    use_context: bool = False
    previous_results: Optional[str] = None


class AdvancedRouter:
    def __init__(self):
        self.conversation_memory: List[Dict] = []
        self.last_search_context: Optional[str] = None

    def _extract_conversation_context(self, messages: List[Dict]) -> Tuple[str, bool]:
        if not messages:
            return "", False
        recent_messages = [msg for msg in messages if msg.get('role') != 'system'][-8:]
        context_parts: List[str] = []
        has_search_results = False

        for msg in recent_messages:
            role = "User" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '') or ""
            if (
                msg.get('role') == 'assistant'
                and any(
                    indicator in content
                    for indicator in [
                        'Source:', 'Sumber:', '# Key Points',
                        'Address Analysis Report', 'Web Page Summary', '```'
                    ]
                )
            ):
                has_search_results = True
                self.last_search_context = content
            if len(content) > 200:
                content = content[:200] + "..."
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts), has_search_results

    def _llm_intent_classification(self, user_input: str, context: str, has_search_results: bool) -> Optional[RouterDecision]:
        classification_prompt = """You are an expert conversation router. Determine the user's intent and select the correct tool. Always return strict JSON.

CONVERSATION CONTEXT (recent messages):
---
{}
---

CURRENT USER INPUT:
"{}"

TOOLS & INTENTS:
1) GENERAL_CHAT
   - Greetings, thanks, chit-chat, or summarizing the current conversation.

2) MEMORY_RECALL
   - User asks if you remember a specific topic from distant past sessions.

3) CONTEXT_ANSWER
   - Follow-up questions about the last answer or the shown results/sources.

4) CODE_GENERATOR
   - Requests to write, modify, or explain code.

5) READLE
   - Read and summarize content from a URL. If chosen, include the URL in suggested_query.

6) ADDRESS_ANALYSIS
   - Analyze a crypto address. The address may be EVM (0x...), BTC (1..., 3..., bc1...), Solana-like, etc.
   - IMPORTANT: Extract the most likely address string from the input and return it in suggested_query, without adding commentary.

7) FRESH_SEARCH
   - New questions that require online search or fresh data.

8) GENERATE_X_REPLY
   - Generate and post replies to X/Twitter posts. User provides tweet ID or tweet URL.
   - Extract the tweet ID from URLs or use provided ID directly in suggested_query.
   - Examples: "reply to this tweet: 1234567890", "generate reply for https://x.com/user/status/1234567890"


RESPONSE FORMAT (STRICT JSON):
{{
  "intent": "GENERAL_CHAT",
  "confidence": 0.0,
  "reasoning": "short explanation",
  "suggested_query": "string to pass to the tool"
}}

VALID INTENTS: GENERAL_CHAT, MEMORY_RECALL, CONTEXT_ANSWER, CODE_GENERATOR, READLE, ADDRESS_ANALYSIS, FRESH_SEARCH, GENERATE_X_REPLY

NOTES:
- Do not include markdown in the JSON. No backticks. No extra keys.
- If intent is READLE, suggested_query should be the URL only.
- If intent is ADDRESS_ANALYSIS, suggested_query should be the extracted address only.
- If intent is GENERATE_X_REPLY, suggested_query should be the tweet ID only.
- If intent is CONTEXT_ANSWER and there are previous results available, set intent accordingly.
""".format(context, user_input)

        messages = [
            {"role": "system", "content": "You are a precise intent classifier. Always return strict JSON."},
            {"role": "user", "content": classification_prompt},
        ]

        try:
            response_generator = generate_response(
                messages,
                stream=False,
                model=MODEL_UTAMA,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            response_text = "".join(response_generator)
            if not response_text or "[ERROR]" in response_text:
                return None
            
            result = json.loads(response_text)

            intent = result.get("intent")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            suggested_query = result.get("suggested_query", user_input)

            tool_map = {
                "MEMORY_RECALL": "memory_recall",
                "CODE_GENERATOR": "code_generator",
                "READLE": "readle",
                "CONTEXT_ANSWER": "context_answer",
                "ADDRESS_ANALYSIS": "address_analyzer",
                "FRESH_SEARCH": "web_search",
                "GENERAL_CHAT": "general_chat",
                "GENERATE_X_REPLY": "generative_commenter",
            }

            actual_tool = tool_map.get(intent, "general_chat")

            use_context_flag = False
            previous_results_data = None

            query = suggested_query
            if intent == "CONTEXT_ANSWER" and has_search_results:
                use_context_flag = True
                previous_results_data = self.last_search_context
                query = user_input
            elif intent in ["CODE_GENERATOR", "GENERAL_CHAT"]:
                query = user_input
            elif intent == "GENERATE_X_REPLY":
                if "x.com" in suggested_query or "twitter.com" in suggested_query:
                    import re
                    tweet_id_match = re.search(r'/status/(\d+)', suggested_query)
                    if tweet_id_match:
                        query = tweet_id_match.group(1)
                    else:
                        query = suggested_query
                else:
                    query = suggested_query.strip()

            return RouterDecision(
                tool=actual_tool,
                query=query,
                confidence=confidence,
                reasoning=f"LLM: {reasoning}",
                use_context=use_context_flag,
                previous_results=previous_results_data,
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            debug_text = response_text if 'response_text' in locals() else 'No response'
            console.log(f"[yellow]LLM classification failed: {e}[/yellow]\nResponse: {debug_text}")
            return None
        except Exception as e:
            console.log(f"[red]LLM error: {e}[/red]")
            return None

    def route_with_advanced_intelligence(self, user_input: str, conversation_history: List[Dict]) -> Dict:
        console.log("[cyan]Advanced Router analyzing intent (LLM-based)...[/cyan]")
        context, has_search_results = self._extract_conversation_context(conversation_history)

        llm_decision = self._llm_intent_classification(user_input, context, has_search_results)
        if llm_decision and llm_decision.confidence >= 0.6:
            console.log(f"[green]LLM Decision:[/green] {llm_decision.tool} (confidence: {llm_decision.confidence:.2f})")
            console.log(f"[dim]   Reasoning: {llm_decision.reasoning}[/dim]")
            return llm_decision.__dict__

        console.log("[yellow]LLM confidence low or failed. Falling back to GENERAL_CHAT.[/yellow]")
        fallback = RouterDecision(
            tool="general_chat",
            query=user_input,
            confidence=0.5,
            reasoning="Fallback: LLM classification unavailable or low confidence",
            use_context=False,
            previous_results=None,
        )
        return fallback.__dict__


_advanced_router = AdvancedRouter()

def route_with_advanced_intelligence(user_input: str, conversation_history: List[Dict]) -> Dict:
    return _advanced_router.route_with_advanced_intelligence(user_input, conversation_history)


def route_with_context(user_input: str, conversation_history: List[Dict]) -> Dict:
    return route_with_advanced_intelligence(user_input, conversation_history)
