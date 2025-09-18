import json
import re
import hashlib
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from rich.tree import Tree
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from tools.shared_console import console
from tools.config_styles import custom_colorsUX
from tools.lang_utils import detect_target_language_from_text

try:
    from core.fireworks_api_client import generate_response
except ImportError:
    print("[ERROR] Missing fireworks_api_client")
    def generate_response(messages, **kwargs):
        if kwargs.get('stream'): yield "[FALLBACK] LLM Error"
        else: return ["[FALLBACK] LLM Error"]

try:
    from tools.upgradescraper import brave_search
except ImportError:
    print("[ERROR] Missing brave_search")
    def brave_search(query, limit=4):
        return {'organic_results': []}

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    domain: str
    relevance_score: float
    timestamp: Optional[str] = None
    source_quality: float = 0.5
    final_score: float = 0.0
    intent_match: float = 0.0

class EnhancedSearchPersona:
    def __init__(self):
        self.base_trusted_domains = {
            'github.com': 0.95, 'stackoverflow.com': 0.90, 'docs.python.org': 0.95,
            'readthedocs.io': 0.90, 'pypi.org': 0.90, 'npmjs.com': 0.85,
            'developer.mozilla.org': 0.90, 'w3schools.com': 0.75,
            
            'coinmarketcap.com': 0.85, 'coingecko.com': 0.85, 'coindesk.com': 0.80,
            'binance.com': 0.80, 'coinbase.com': 0.80, 'cointelegraph.com': 0.75,
            'blockchain.com': 0.80, 'kraken.com': 0.80,
            
            'reuters.com': 0.90, 'bloomberg.com': 0.85, 'techcrunch.com': 0.80,
            'wired.com': 0.80, 'arstechnica.com': 0.85, 'theverge.com': 0.75,
            'cnn.com': 0.70, 'bbc.com': 0.85, 'cnbc.com': 0.75,
            
            'arxiv.org': 0.95, 'scholar.google.com': 0.90, 'researchgate.net': 0.85,
            'ieee.org': 0.90, 'acm.org': 0.90, 'nature.com': 0.95,
            
            'sec.gov': 0.90, 'nasdaq.com': 0.85, 'forbes.com': 0.75,
            'wsj.com': 0.85, 'ft.com': 0.85, 'marketwatch.com': 0.70,
            
            'medium.com': 0.60, 'dev.to': 0.70, 'hackernoon.com': 0.60,
            'reddit.com': 0.45, 'quora.com': 0.40, 'youtube.com': 0.50,
            
            'gov': 0.90, '.edu': 0.85, '.org': 0.75,
            
            'wikipedia.org': 0.80
        }
        
        self.intent_patterns = {
            'programming': {
                'keywords': ['library', 'package', 'framework', 'api', 'documentation', 'python', 'javascript', 'npm', 'pip', 'install', 'import', 'code', 'developer', 'programming', 'software', 'github', 'repository', 'version', 'release'],
                'boost_domains': ['github.com', 'readthedocs.io', 'pypi.org', 'npmjs.com', 'stackoverflow.com', 'docs.python.org', 'developer.mozilla.org'],
                'penalty_domains': ['coinmarketcap.com', 'coingecko.com', 'binance.com', 'coinbase.com']
            },
            'crypto': {
                'keywords': ['price', 'trading', 'coin', 'token', 'crypto', 'cryptocurrency', 'bitcoin', 'ethereum', 'blockchain', 'exchange', 'wallet', 'mining', 'defi', 'nft', 'market cap', 'volume'],
                'boost_domains': ['coinmarketcap.com', 'coingecko.com', 'binance.com', 'coinbase.com', 'coindesk.com', 'cointelegraph.com'],
                'penalty_domains': ['github.com', 'readthedocs.io', 'pypi.org']
            },
            'news': {
                'keywords': ['news', 'breaking', 'latest', 'today', 'yesterday', 'report', 'article', 'story', 'journalist', 'media', 'press', 'announcement'],
                'boost_domains': ['reuters.com', 'bloomberg.com', 'techcrunch.com', 'cnn.com', 'bbc.com', 'cnbc.com'],
                'penalty_domains': []
            },
            'academic': {
                'keywords': ['research', 'study', 'paper', 'journal', 'academic', 'university', 'scholar', 'thesis', 'publication', 'peer review', 'citation'],
                'boost_domains': ['arxiv.org', 'scholar.google.com', 'researchgate.net', 'ieee.org', 'acm.org', 'nature.com'],
                'penalty_domains': ['reddit.com', 'quora.com', 'medium.com']
            },
            'business': {
                'keywords': ['company', 'business', 'corporate', 'earnings', 'revenue', 'financial', 'stock', 'market', 'investment', 'ipo', 'merger', 'acquisition'],
                'boost_domains': ['sec.gov', 'nasdaq.com', 'forbes.com', 'wsj.com', 'ft.com', 'bloomberg.com'],
                'penalty_domains': []
            },
            'health': {
                'keywords': ['health', 'medical', 'medicine', 'treatment', 'disease', 'symptom', 'drug', 'clinical', 'patient', 'doctor', 'hospital'],
                'boost_domains': ['nih.gov', 'who.int', 'mayoclinic.org', 'webmd.com', 'healthline.com'],
                'penalty_domains': ['reddit.com', 'quora.com']
            },
            'general': {
                'keywords': [],
                'boost_domains': ['wikipedia.org', 'britannica.com'],
                'penalty_domains': []
            }
        }
        
        self.search_cache = {}
        self.last_search_results = []

    def _detect_target_language_from_text(self, text: str) -> str:
        return detect_target_language_from_text(text)

    def _get_domain_from_url(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return 'unknown'

    def _classify_query_intent(self, query: str) -> str:
        query_lower = query.lower()
        intent_scores = {}
        
        for intent, config in self.intent_patterns.items():
            if intent == 'general':
                continue
                
            keywords = config['keywords']
            matches = sum(1 for keyword in keywords if keyword in query_lower)
            if matches > 0:
                intent_scores[intent] = matches / len(keywords)
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            console.log(f"[cyan]Intent detected:[/cyan] {best_intent} (confidence: {confidence:.2f})")
            return best_intent
        
        console.log("[cyan]Intent detected:[/cyan] general")
        return 'general'

    def _generate_intent_based_queries(self, base_query: str, intent: str, max_queries: int = 4) -> List[str]:
        console.log(f"[cyan]Generating queries for intent:[/cyan] {intent}")
        
        current_year = datetime.now().year
        
        query_templates = {
            'programming': [
                f"{base_query} python library documentation",
                f"{base_query} github repository latest version",
                f"{base_query} python package pypi",
                f"{base_query} API documentation tutorial"
            ],
            'crypto': [
                f"{base_query} price today USD",
                f"{base_query} market cap trading volume",
                f"{base_query} cryptocurrency latest news",
                f"{base_query} coin analysis {current_year}"
            ],
            'news': [
                f"{base_query} latest news {current_year}",
                f"{base_query} breaking news today",
                f"{base_query} news update recent",
                f"{base_query} current events"
            ],
            'academic': [
                f"{base_query} research paper {current_year}",
                f"{base_query} academic study latest",
                f"{base_query} scholarly article research",
                f"{base_query} journal publication"
            ],
            'business': [
                f"{base_query} company financial report {current_year}",
                f"{base_query} business news earnings",
                f"{base_query} stock market analysis",
                f"{base_query} corporate announcement"
            ],
            'health': [
                f"{base_query} medical research latest",
                f"{base_query} health study clinical trial",
                f"{base_query} medical news {current_year}",
                f"{base_query} treatment guidelines"
            ],
            'general': [
                f"{base_query}",
                f"{base_query} {current_year}",
                f"{base_query} latest information",
                f"{base_query} current status"
            ]
        }
        
        queries = query_templates.get(intent, query_templates['general'])
        return queries[:max_queries]

    def _calculate_intent_match_score(self, result: SearchResult, query: str, intent: str) -> float:
        if intent == 'general':
            return 0.0
            
        config = self.intent_patterns.get(intent, {})
        keywords = config.get('keywords', [])
        boost_domains = config.get('boost_domains', [])
        penalty_domains = config.get('penalty_domains', [])
        
        content = f"{result.title} {result.snippet}".lower()
        score = 0.0
        
        keyword_matches = sum(1 for keyword in keywords if keyword in content)
        if keywords:
            score += (keyword_matches / len(keywords)) * 0.5
        
        domain_lower = result.domain.lower()
        for boost_domain in boost_domains:
            if boost_domain in domain_lower:
                score += 0.4
                break
                
        for penalty_domain in penalty_domains:
            if penalty_domain in domain_lower:
                score -= 0.6
                break
        
        return max(-1.0, min(1.0, score))

    def _calculate_source_quality(self, url: str, title: str, snippet: str, intent: str) -> float:
        domain = self._get_domain_from_url(url)
        base_score = self.base_trusted_domains.get(domain, 0.5)
        
        for trusted_domain, score in self.base_trusted_domains.items():
            if trusted_domain in domain and domain != trusted_domain:
                base_score = max(base_score, score * 0.8)
        
        content = f"{title} {snippet}".lower()
        
        quality_indicators = ['official', 'documentation', 'whitepaper', 'announcement', 'research', 'study', 'report', 'guide', 'tutorial']
        spam_indicators = ['click here', 'amazing', 'shocking', 'you won\'t believe', 'one weird trick', 'download now', 'free download']
        
        for indicator in quality_indicators:
            if indicator in content:
                base_score += 0.05
                
        for spam in spam_indicators:
            if spam in content:
                base_score -= 0.3
        
        if intent in self.intent_patterns:
            config = self.intent_patterns[intent]
            if domain in config.get('boost_domains', []):
                base_score += 0.2
            elif domain in config.get('penalty_domains', []):
                base_score -= 0.3
        
        return max(0.1, min(1.0, base_score))

    def _calculate_relevance_score(self, result: SearchResult, query: str, intent: str) -> float:
        query_terms = set(query.lower().split())
        content = f"{result.title} {result.snippet}".lower()
        content_terms = set(content.split())
        
        exact_matches = len(query_terms.intersection(content_terms))
        base_relevance = exact_matches / len(query_terms) if query_terms else 0
        
        semantic_bonus = 0.0
        if intent in self.intent_patterns:
            intent_keywords = self.intent_patterns[intent]['keywords']
            semantic_matches = sum(1 for keyword in intent_keywords if keyword in content)
            if intent_keywords:
                semantic_bonus = (semantic_matches / len(intent_keywords)) * 0.3
        
        title_matches = sum(1 for term in query_terms if term in result.title.lower())
        title_bonus = (title_matches / len(query_terms)) * 0.2 if query_terms else 0
        
        freshness_bonus = 0.0
        current_year = datetime.now().year
        if str(current_year) in content or str(current_year - 1) in content:
            freshness_bonus = 0.1
        
        total_relevance = base_relevance + semantic_bonus + title_bonus + freshness_bonus
        return min(1.0, total_relevance)

    def _calculate_final_score(self, result: SearchResult, query: str, intent: str) -> float:
        relevance_weight = 0.4
        quality_weight = 0.3
        intent_weight = 0.3
        
        final_score = (
            result.relevance_score * relevance_weight +
            result.source_quality * quality_weight +
            result.intent_match * intent_weight
        )
        
        content_lower = f"{result.title} {result.snippet}".lower()
        
        if intent == 'programming' and any(term in content_lower for term in ['coin', 'crypto', 'trading', 'price usd']):
            final_score *= 0.3
        elif intent == 'crypto' and any(term in content_lower for term in ['python library', 'documentation', 'install pip']):
            final_score *= 0.3
        
        return max(0.0, min(1.0, final_score))

    def _enhanced_search_with_validation(self, query: str, intent: str) -> List[SearchResult]:
        console.log(f"[yellow]Searching:[/yellow] '{query}' (intent: {intent})")
        
        try:
            cache_key = hashlib.md5(f"{query}_{intent}".encode()).hexdigest()
            if cache_key in self.search_cache:
                cache_time, cached_results = self.search_cache[cache_key]
                if datetime.now() - cache_time < timedelta(hours=1):
                    return cached_results

            search_response = brave_search(query, limit=5)
            raw_results = search_response.get('organic_results', [])

            if raw_results:
                debug_tree = Tree(f"🔍 RAW DATA VIEWER | Query: '{query}' | Intent: {intent}", style="red bold")
                
                for i, result in enumerate(raw_results, 1):
                    title = result.get('title', '')
                    link = result.get('link', '')
                    snippet = result.get('snippet', '')
                    
                    result_branch = debug_tree.add(f"📄 RESULT #{i}", style="yellow bold")
                    result_branch.add(f"🏷️  Title: {title}", style="white")
                    result_branch.add(f"🔗 Link: {link}", style="blue")
                    result_branch.add(f"📝 Snippet: {snippet}", style="dim white")
                
                console.print(debug_tree)

            if not raw_results:
                return []

            processed_results = []
            for result in raw_results:
                url = result.get('link', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                if not url or len(snippet) < 10:
                    continue
                
                domain = self._get_domain_from_url(url)
                
                search_result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    domain=domain,
                    relevance_score=0.0,
                    source_quality=0.0,
                    intent_match=0.0
                )
                
                search_result.source_quality = self._calculate_source_quality(url, title, snippet, intent)
                search_result.relevance_score = self._calculate_relevance_score(search_result, query, intent)
                search_result.intent_match = self._calculate_intent_match_score(search_result, query, intent)
                search_result.final_score = self._calculate_final_score(search_result, query, intent)
                
                processed_results.append(search_result)
            
            self.search_cache[cache_key] = (datetime.now(), processed_results)
            console.log(f"[green]Found {len(processed_results)} validated results[/green]")
            return processed_results
            
        except Exception as e:
            console.log(f"[red]Search error for '{query}': {e}[/red]")
            return []

    def _synthesize_results(self, all_results: List[SearchResult], user_query: str, intent: str, stream: bool = True):
        if not all_results:
            nores = "Sorry, no relevant information was found. Please try different keywords or search terms."
            if stream:
                yield nores
                return
            return nores

        unique_results = {res.url: res for res in all_results}
        ranked_results = sorted(unique_results.values(), key=lambda x: x.final_score, reverse=True)

        ranking_table = Table(
            title=f"🎯 SIMPLE RE-RANKING RESULTS | Intent: {intent.upper()}",
            title_style="bold cyan",
            border_style="cyan",
            show_header=True,
            header_style=custom_colorsUX()["panel_app"],
            expand=True,
            box=custom_colorsUX()["table_box"],
        )
        
        ranking_table.add_column("#", style="white bold", width=3, justify="center")
        ranking_table.add_column("Final", style="green bold", width=6, justify="center")
        ranking_table.add_column("Rel", style="yellow", width=5, justify="center")
        ranking_table.add_column("Qual", style="blue", width=5, justify="center")
        ranking_table.add_column("Intent", style="magenta", width=6, justify="center")
        ranking_table.add_column("Domain", style="dim white", width=25, justify="left")
        ranking_table.add_column("Title", style="white", justify="left")
        
        for i, res in enumerate(ranked_results[:10], 1):
            ranking_table.add_row(
                f"{i}",
                f"{res.final_score:.2f}",
                f"{res.relevance_score:.2f}",
                f"{res.source_quality:.2f}",
                f"{res.intent_match:.2f}",
                res.domain[:25],
                res.title[:50] + ("..." if len(res.title) > 50 else "")
            )
        
        console.print(ranking_table)

        final_results = ranked_results[:6]

        context_parts = []
        for i, result in enumerate(final_results, 1):
            context_parts.append(f"""
[RESULT {i}]
Title: {result.title}
URL: {result.url}
Domain: {result.domain}
Final Score: {result.final_score:.2f}
Intent Match: {result.intent_match:.2f}
Content: {result.snippet}
""")
        
        combined_context = "\n".join(context_parts)
        
        synthesis_templates = {
            'programming': {
                'instruction': "CRITICAL: Focus on technical details, version information, installation instructions, and official documentation. Use EXACT formatting with bold headers and bullet points. Include code examples if mentioned.",
                'format_example': """
**Library Version**: X.X.X (latest from GitHub/PyPI)

**Installation**: 
- `pip install library-name` (official method)
- `python -m pip install library-name` (alternative)

**Key Features**: 
- Feature 1: Description (GitHub/Docs)
- Feature 2: Description (source)
- Feature 3: Description (source)

**System Requirements**:
- Python version: X.X+ required
- Platform compatibility: Windows/macOS/Linux
- Dependencies: List if mentioned

**Documentation**: 
- Official docs: [URL]
- GitHub repository: [URL] 
- PyPI page: [URL]

**Recent Updates**: 
- Version X.X.X: What changed (GitHub Releases)
- Dropped support: Specify versions (source)
- New features: List improvements (source)
"""
            },
            'crypto': {
                'instruction': "CRITICAL: Aggregate ALL price data from multiple sources. Include current price, 24h volume, market cap, price movements, and trading information. Show price variations between sources. Use EXACT formatting with bold headers.",
                'format_example': """
**Current [Coin] Price**: 
- $X,XXX USD (CoinMarketCap)
- $X,XXX USD (CoinGecko) 
- $X,XXX USD (Coinbase)

**Market Statistics**:
- 24h Trading Volume: $XX billion (source) vs $XX billion (source)
- Market Cap: $X.XX trillion (source) vs $X.XX trillion (source)
- 24h Change: +/-X.XX% (source)
- Current Ranking: #X (CoinMarketCap)

**Trading Information**:
- Most Active Pair: BTC/USDT (volume: $X billion)
- Popular Exchanges: Exchange1, Exchange2 (sources)
- Recent Price Action: Technical analysis and price movements (sources)

**Additional Context**:
- Key developments or news affecting price (if mentioned)
- Price predictions or analyst views (if available)
"""
            },
            'news': {
                'instruction': "Focus on recent events, breaking news, and current developments. Prioritize the most recent information and provide timeline context.",
                'format_example': """
**Breaking News**: Most recent developments
**Timeline**: 
- Today: Event A
- Yesterday: Event B
**Key Details**: Important facts and figures
**Sources**: Multiple news outlets with links
"""
            },
            'academic': {
                'instruction': "Focus on research findings, methodologies, citations, and academic credibility. Highlight peer-reviewed sources.",
                'format_example': """
**Research Findings**: Key discoveries
**Methodology**: How research was conducted
**Publications**: Journal articles and papers
**Citations**: Reference count and impact
"""
            },
            'business': {
                'instruction': "Focus on financial data, business metrics, corporate announcements, and market impact.",
                'format_example': """
**Financial Data**: Revenue, earnings, stock price
**Business Metrics**: Performance indicators
**Recent Announcements**: Corporate news
**Market Impact**: How it affects industry
"""
            },
            'health': {
                'instruction': "Focus on medical research, treatment options, and health recommendations from credible medical sources.",
                'format_example': """
**Medical Research**: Latest findings
**Treatment Options**: Available treatments
**Health Recommendations**: Expert advice
**Credible Sources**: Medical institutions
"""
            },
            'general': {
                'instruction': "Provide a comprehensive overview covering all relevant aspects found in the search results.",
                'format_example': """
**Key Information**: Most important facts
**Details**: Supporting information
**Sources**: Multiple references
"""
            }
        }
        
        template = synthesis_templates.get(intent, synthesis_templates['general'])
        instruction = template['instruction']
        format_example = template['format_example']
        
        compact_context_text = f"{user_query}\n\n" + "\n".join([f"{r.title} {r.snippet}" for r in final_results])
        target_language = self._detect_target_language_from_text(compact_context_text)

        if stream:
            yield f"### 🔎 Intelligent Web Search Analysis\n\n"
            yield f"**Intent:** {intent}\n\n"
            yield f"**Answer Language:** {target_language}\n\n"

        synthesis_prompt = f"""You are an expert information analyst. Create a comprehensive, well-structured response.

SEARCH INTENT: {intent}
SPECIAL INSTRUCTIONS: {instruction}

CRITICAL REQUIREMENTS:
1. **USE MARKDOWN FORMATTING** - Always use **bold headers**, `code blocks`, and proper bullet points
2. **FOLLOW EXACT TEMPLATE STRUCTURE** - Don't deviate from the format example provided
3. **AGGREGATE DATA FROM ALL SOURCES** - Don't just use one source, combine information from multiple sources
4. **SHOW DATA VARIATIONS** - If different sources show different values, display all of them
5. **INCLUDE ALL RELEVANT INFORMATION** - Don't skip important technical details or version info
6. **CITE SOURCES PROPERLY** - Include source names in parentheses (GitHub), (PyPI), etc.
7. **BE COMPREHENSIVE** - Use ALL the valuable data provided, not just the first result
8. **MAINTAIN CLEAN STRUCTURE** - Each section should be clearly separated and well-organized

FORMAT EXAMPLE FOR {intent.upper()}:
{format_example}

SEARCH RESULTS WITH MULTIPLE DATA POINTS:
{combined_context}

USER QUESTION: {user_query}

LANGUAGE: {target_language} (write the entire response in this language)

Generate a structured response that synthesizes ALL relevant information from the search results. Make sure to aggregate data from multiple sources and show variations when they exist."""

        try:
            messages = [
                {"role": "system", "content": "You are a helpful research analyst who provides accurate, well-sourced information."},
                {"role": "user", "content": synthesis_prompt}
            ]
            if stream:
                for chunk in generate_response(messages, stream=True, temperature=0.2):
                    if chunk:
                        yield chunk
                self.last_search_results = final_results
                sources_block = "\n".join([f"- {res.title} ({res.url})" for res in final_results])
                yield f"\n\n---\n\n**Sources:**\n{sources_block}"
                return
            else:
                response = generate_response(messages, stream=False, temperature=0.2)
                if isinstance(response, list):
                    response = "".join(response)
                self.last_search_results = final_results
                body = str(response).strip()
                sources_block = "\n".join([f"- {res.title} ({res.url})" for res in final_results])
                return f"### 🔎 Intelligent Web Search Analysis\n\n{body}\n\n---\n\n**Sources:**\n{sources_block}"
        except Exception as e:
            console.log(f"[red]Synthesis error: {e}[/red]")
            err = f"Error during synthesis. Please try your search again. Technical error: {str(e)}"
            if stream:
                yield err
                return
            return err

    def search_with_context(self, user_query: str, search_query: str, previous_context: Optional[str] = None, stream: bool = True):        
        intent = self._classify_query_intent(search_query)
        
        search_queries = self._generate_intent_based_queries(search_query, intent)
        
        console.log("[blue]Executing parallel searches with intent-aware queries...[/blue]")
        
        all_results = []
        with ThreadPoolExecutor(max_workers=len(search_queries)) as executor:
            future_to_query = {
                executor.submit(self._enhanced_search_with_validation, query, intent): query 
                for query in search_queries
            }
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    console.log(f"[green]Completed search for:[/green] '{query}' - {len(results)} results")
                except Exception as e:
                    console.log(f"[red]Search failed for '{query}': {e}[/red]")

        return self._synthesize_results(all_results, user_query, intent, stream=stream)

    def _answer_from_context(self, user_query: str, previous_context: str) -> Optional[str]:
        return None

_search_persona = EnhancedSearchPersona()

def run_enhanced_search_persona(user_prompt: str, query_for_web: str, previous_context: Optional[str] = None):
    try:
        generator = _search_persona.search_with_context(user_prompt, query_for_web, previous_context, stream=True)
        for chunk in generator:
            yield chunk
    except Exception as e:
        console.log(f"[red]Critical error in search persona: {e}[/red]")
        yield f"Sorry, a critical error occurred during the search. Error: {str(e)}"

def run_search_persona(user_prompt: str, query_for_web: str):
    yield from run_enhanced_search_persona(user_prompt, query_for_web)
