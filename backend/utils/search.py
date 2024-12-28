import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
import re
from urllib.parse import quote_plus, urljoin
import json
import logging
import traceback
from typing import AsyncGenerator, AsyncIterator


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet

async def generate_search_queries(llm_client, text: str) -> List[str]:
    try:
        prompt = f"""Generate 2-3 search queries to find information about: {text}
        Format: Return only a JSON array of strings, nothing else.
        Example: ["specific query 1", "specific query 2"]"""

        response = await llm_client.complete(prompt)
        logger.info(f"LLM Response for queries: {response}")

        # Clean the response to ensure it's valid JSON
        response = response.strip()
        if not response.startswith('['):
            response = f'["{text}"]'

        queries = json.loads(response)
        return queries if isinstance(queries, list) else [text]
    except Exception as e:
        logger.error(f"Error generating queries: {str(e)}")
        return [text]

async def search_duckduckgo(query: str, max_results: int = 3) -> List[SearchResult]:
    """
    Search DuckDuckGo using the HTML interface
    """
    try:
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # Form data for POST request
        data = {
            'q': query,
            'b': ''
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []

                    # Find all search results
                    for result in soup.find_all('div', class_='result'):
                        try:
                            # Get title and link
                            a_tag = result.find('a', class_='result__a')
                            if not a_tag:
                                continue

                            title = a_tag.get_text(strip=True)
                            url = a_tag.get('href', '')

                            # Get snippet
                            snippet_div = result.find('a', class_='result__snippet')
                            snippet = snippet_div.get_text(strip=True) if snippet_div else ""

                            if title and url:
                                # Clean up URL if needed
                                if url.startswith('/'):
                                    url = f"https://duckduckgo.com{url}"

                                results.append(SearchResult(title, url, snippet))
                                if len(results) >= max_results:
                                    break

                        except Exception as e:
                            logger.error(f"Error processing result: {str(e)}")
                            continue

                    # If no results found with primary method, try alternative parsing
                    if not results:
                        logger.info("Trying alternative parsing method...")
                        for link in soup.find_all('a'):
                            href = link.get('href', '')
                            if (href.startswith('http') and
                                not href.startswith('https://duckduckgo.com') and
                                not href.startswith('https://html.duckduckgo.com')):

                                title = link.get_text(strip=True)
                                if title and len(results) < max_results:
                                    results.append(SearchResult(
                                        title=title,
                                        url=href,
                                        snippet=""
                                    ))

                    # Log the results for debugging
                    logger.info(f"Found {len(results)} results for query: {query}")
                    for r in results:
                        logger.info(f"Title: {r.title[:30]}... URL: {r.url[:50]}...")

                    return results
                else:
                    logger.error(f"Search request failed with status: {response.status}")
                    return []

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return []

    return []


async def fetch_webpage_content(url: str) -> str:
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            ) as response:
                if response.status != 200:
                    return ""

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Remove unwanted elements
                for tag in ['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']:
                    for element in soup.find_all(tag):
                        element.decompose()

                # Try to find the main content
                content = None
                for selector in ['main', 'article', '#content', '.content', 'body']:
                    content = soup.select_one(selector)
                    if content:
                        break

                if content:
                    text = content.get_text(separator=' ', strip=True)
                    return ' '.join(text.split())  # Normalize whitespace
                return ""
    except Exception as e:
        logger.error(f"Error fetching webpage {url}: {str(e)}")
        return ""

async def summarize_search_results(llm_client, query: str, results: List[SearchResult]) -> List[Dict]:
    summaries = []
    for result in results:
        try:
            content = await fetch_webpage_content(result.url)
            if content:
                prompt = f"""Summarize this content (max 3 sentences) in relation to: "{query}"
                Content: {content[:1500]}"""

                summary = await llm_client.complete(prompt)
                summaries.append({
                    "title": result.title,
                    "url": result.url,
                    "summary": summary
                })
        except Exception as e:
            logger.error(f"Error summarizing result: {str(e)}")
            continue

    return summaries

async def retry_with_backoff(func, *args,  max_retries=3, initial_delay=1, **kwargs):
    """Retry a function with exponential backoff"""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)  # Pass both args and kwargs to the function
        except Exception as e:
            last_exception = e
            if attempt == max_retries - 1:
                break

            await asyncio.sleep(delay)
            delay *= 2

    logger.error(f"All retries failed: {str(last_exception)}")
    return []

class WebSearchEnhancer:
    def __init__(self, llm_client, max_tokens_per_chunk=800):
        self.llm_client = llm_client
        self.max_tokens_per_chunk = max_tokens_per_chunk


    def __aiter__(self):
        return self

    async def chunk_summaries(self, summaries: List[Dict]) -> List[List[Dict]]:
        """Break summaries into smaller chunks"""
        chunks = []
        current_chunk = []
        current_length = 0

        for summary in summaries:
            # Rough estimate of tokens (characters/4 is a rough approximation)
            summary_length = len(str(summary)) // 4

            if current_length + summary_length > self.max_tokens_per_chunk:
                if current_chunk:  # Add current chunk if not empty
                    chunks.append(current_chunk)
                current_chunk = [summary]
                current_length = summary_length
            else:
                current_chunk.append(summary)
                current_length += summary_length

        if current_chunk:  # Add the last chunk
            chunks.append(current_chunk)

        return chunks

    async def generate_partial_response(self, user_query: str, summaries_chunk: List[Dict],
                                      previous_response: str = "") -> str:
        prompt = f"""Based on these summaries, continue answering: "{user_query}"

        Previous response: {previous_response}

        Additional Information:
        {json.dumps(summaries_chunk, indent=2)}

        Instructions:
        1. Continue the response naturally
        2. Use [n] to cite sources
        3. Be concise and relevant
        4. If this is a continuation, make it flow smoothly"""

        return await self.llm_client.complete(prompt)



    async def enhance_response(self, user_query: str, context: list = None) -> AsyncGenerator[str, None]:
        try:
            yield "Searching the web for information...\n\n"

            # Generate search queries
            search_queries = await generate_search_queries(self.llm_client, user_query)
            yield f"Generated search queries:\n" + "\n".join(f"- {q}" for q in search_queries) + "\n\n"

            # Track all references for the final response
            all_references = []
            processed_urls = set()

            # Process each search query
            for query in search_queries[:3]:
                yield f"Searching for: {query}...\n"

                results = await retry_with_backoff(search_duckduckgo, query, max_retries=2, initial_delay=1, max_results=2)
                if not results:
                    yield f"No results found for '{query}'\n"
                    continue

                # Process each result one by one
                for result in results:
                    if result.url in processed_urls:
                        continue

                    processed_urls.add(result.url)
                    yield f"Reading: {result.title}...\n"

                    try:
                        content = await fetch_webpage_content(result.url)
                        if not content:
                            continue

                        # Add to references
                        ref_id = len(all_references) + 1
                        all_references.append({
                            "id": ref_id,
                            "title": result.title,
                            "url": result.url
                        })

                        # Generate summary for this specific result
                        prompt = f"""Summarize this content (2-3 sentences) in relation to: "{user_query}"
                        Content: {content[:1500]}"""

                        summary = await self.llm_client.complete(prompt)
                        if summary:
                            yield f"\nSummary [{ref_id}]: {summary}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing result: {str(e)}")
                        continue

            # Generate final conclusion
            if all_references:
                conclude_prompt = f"""Write a brief concluding paragraph about {user_query} based on the information above."""
                conclusion = await self.llm_client.complete(conclude_prompt)
                yield f"\nConclusion: {conclusion}\n\n"

                # Add references
                yield "\nReferences:\n" + "\n".join(
                    f"[{ref['id']}] [{ref['title']}]({ref['url']})"
                    for ref in all_references
                )
            else:
                yield "\nNo relevant information found."

        except Exception as e:
            logger.error(f"Error in enhance_response: {traceback.format_exc()}")
            yield f"Error: {str(e)}"
