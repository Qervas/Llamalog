import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, AsyncGenerator
import re
from urllib.parse import quote_plus, urljoin
import json
import logging
import traceback
from typing import AsyncGenerator, AsyncIterator
from cachetools import TTLCache
from urllib.parse import urlparse
from .content_extractor import ContentExtractor




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
        timeout = aiohttp.ClientTimeout(total=30.0)
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
                content_extractor = ContentExtractor()
                extracted_content = await content_extractor.extract_content(html, url)

                # Combine relevant content
                final_content = []

                if extracted_content['title']:
                    final_content.append(f"Title: {extracted_content['title']}")

                if extracted_content['metadata'].get('description'):
                    final_content.append(f"\nDescription: {extracted_content['metadata']['description']}")

                if extracted_content['main_content']:
                    final_content.append(f"\nContent:\n{extracted_content['main_content']}")

                return '\n'.join(final_content)
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
    def __init__(self, llm_client, max_tokens_per_chunk=4096):
        self.llm_client = llm_client
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.max_content_length = 100000
        self.search_config = {
            "max_queries": 3,
            "max_results_per_query": 3,
            "max_retries": 2,
            "initial_delay": 1
        }
        # Cache for webpage content with 1-hour TTL
        self.content_cache = TTLCache(maxsize=100, ttl=3600)

    async def calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query."""
        # Simple TF-IDF-like scoring
        query_terms = set(query.lower().split())
        content_lower = content.lower()

        # Calculate term frequency
        term_freq = sum(content_lower.count(term) for term in query_terms)

        # Normalize by content length
        score = term_freq / (len(content_lower.split()) + 1)

        # Boost if query terms appear in first paragraph
        first_para = content_lower.split('\n')[0]
        if any(term in first_para for term in query_terms):
            score *= 1.5

        return score

    def extract_structured_info(self, content: str) -> Dict[str, any]:
        """Extract structured information from content."""
        info = {
            "dates": [],
            "numbers": [],
            "entities": [],
            "key_points": []
        }

        # Extract dates using regex
        date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
        info["dates"] = re.findall(date_pattern, content)

        # Extract numbers and statistics
        number_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:percent|million|billion|trillion))?\b'
        info["numbers"] = re.findall(number_pattern, content)

        # Extract potential key points (sentences with important indicators)
        sentences = re.split(r'[.!?]+', content)
        info["key_points"] = [s.strip() for s in sentences if any(indicator in s.lower() for indicator in
                            ["important", "significant", "key", "main", "crucial", "essential"])]

        return info

    async def process_search_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Process search results in parallel with relevance scoring."""
        async def process_result(result):
            try:
                if result.url in self.content_cache:
                    content = self.content_cache[result.url]
                else:
                    content = await fetch_webpage_content(result.url)
                    if content:
                        self.content_cache[result.url] = content

                if not content:
                    return None

                # Calculate relevance score
                relevance = await self.calculate_relevance_score(content, query)

                # Extract structured information
                structured_info = self.extract_structured_info(content)

                return {
                    "url": result.url,
                    "title": result.title,
                    "content": content,
                    "relevance": relevance,
                    "structured_info": structured_info,
                    "domain": urlparse(result.url).netloc
                }
            except Exception as e:
                logger.error(f"Error processing result {result.url}: {str(e)}")
                return None

        tasks = [process_result(result) for result in results]
        processed_results = await asyncio.gather(*tasks)

        # Filter out None results and sort by relevance
        valid_results = [r for r in processed_results if r is not None]
        return sorted(valid_results, key=lambda x: x["relevance"], reverse=True)

    async def enhance_response(self, user_query: str, context: list = None) -> AsyncGenerator[str, None]:
        try:
            yield "*🔍 Initiating web search...*\n\n"

            # Generate search queries
            search_queries = await generate_search_queries(self.llm_client, user_query)
            for query in search_queries:
                yield f"- `{query}`\n"
                await asyncio.sleep(0.05)

            yield "\n"

            all_references = []
            processed_urls = set()

            for query in search_queries[:3]:
                yield f"*🌐 Searching: {query}*\n"
                await asyncio.sleep(0.2)

                results = await retry_with_backoff(
                    search_duckduckgo,
                    query,
                    max_retries=2,
                    initial_delay=1,
                    max_results=3
                )

                if not results:
                    yield f"No results found for this query.\n"
                    continue

                for result in results:
                    if result.url in processed_urls:
                        continue

                    processed_urls.add(result.url)
                    yield f"*📄 Reading:* [{result.title}]({result.url})\n"

                    try:
                        content = await fetch_webpage_content(result.url)
                        if not content:
                            continue

                        ref_id = len(all_references) + 1
                        all_references.append({
                            "id": ref_id,
                            "title": result.title,
                            "url": result.url
                        })

                        yield f"\n*💡 Key information [{ref_id}]:*\n"

                        summary_prompt = f"""Summarize this content about "{user_query}".
                        Write in Markdown format with proper sections and formatting.

                        Requirements:
                        - Use proper Markdown headings (##, ###)
                        - Break into clear sections
                        - Use bullet points where appropriate
                        - Maintain proper Markdown formatting
                        - Be precise and factual
                        - Focus on key information"""

                        # Stream by Markdown blocks
                        buffer = ""
                        markdown_block = ""

                        async for chunk in self.stream_markdown_content(
                            self.llm_client.stream_complete(
                                summary_prompt,
                                system_prompt="You are a precise research assistant. Format responses in clear, well-structured Markdown."
                            )
                        ):
                            yield chunk

                            # Look for complete Markdown blocks or sentences
                            while True:
                                # Check for Markdown headings
                                heading_match = re.search(r'^(#{1,6}[^#\n]+)\n', buffer)
                                if heading_match:
                                    end = heading_match.end()
                                    yield buffer[:end]
                                    buffer = buffer[end:]
                                    continue

                                # Check for bullet points
                                bullet_match = re.search(r'^([*-]\s+[^\n]+)\n', buffer)
                                if bullet_match:
                                    end = bullet_match.end()
                                    yield buffer[:end]
                                    buffer = buffer[end:]
                                    continue

                                # Check for complete sentences
                                sentence_match = re.search(r'([.!?])\s+(?=[A-Z])', buffer)
                                if sentence_match:
                                    end = sentence_match.end()
                                    yield buffer[:end]
                                    buffer = buffer[end:]
                                    continue

                                break

                            await asyncio.sleep(0.02)

                        if buffer:  # Flush remaining content
                            yield buffer

                        yield "\n\n"

                    except Exception as e:
                        logger.error(f"Error processing result: {str(e)}")
                        continue

            if all_references:
                yield "\n*🎯 Final Analysis:*\n"

                conclusion_prompt = f"""Provide a comprehensive answer about "{user_query}" based on the gathered information.
                Write in Markdown format with proper sections.

                Requirements:
                - Use proper Markdown headings
                - Break into clear sections
                - Use bullet points where appropriate
                - Cite sources using [n]
                - Maintain proper formatting
                - Be clear and precise"""

                # Stream by Markdown blocks
                buffer = ""
                async for chunk in self.stream_markdown_content(
                    self.llm_client.stream_complete(
                        conclusion_prompt,
                        system_prompt="You are an expert analyst. Format responses in clear, well-structured Markdown."
                    )
                ):
                    yield chunk

                    # Look for complete Markdown blocks or sentences
                    while True:
                        # Check for Markdown headings
                        heading_match = re.search(r'^(#{1,6}[^#\n]+)\n', buffer)
                        if heading_match:
                            end = heading_match.end()
                            yield buffer[:end]
                            buffer = buffer[end:]
                            continue

                        # Check for bullet points
                        bullet_match = re.search(r'^([*-]\s+[^\n]+)\n', buffer)
                        if bullet_match:
                            end = bullet_match.end()
                            yield buffer[:end]
                            buffer = buffer[end:]
                            continue

                        # Check for complete sentences
                        sentence_match = re.search(r'([.!?])\s+(?=[A-Z])', buffer)
                        if sentence_match:
                            end = sentence_match.end()
                            yield buffer[:end]
                            buffer = buffer[end:]
                            continue

                        break

                    await asyncio.sleep(0.02)

                if buffer:
                    yield buffer

                # Add references
                yield "\n\n---\n*📚 Sources:*\n"
                for ref in all_references:
                    yield f"[{ref['id']}] [{ref['title']}]({ref['url']})\n"
                    await asyncio.sleep(0.1)
            else:
                yield "\n\n*⚠️ No relevant information found. Try rephrasing your question.*"

        except Exception as e:
            logger.error(f"Error in enhance_response: {traceback.format_exc()}")
            yield f"*❌ Error: {str(e)}*"

    def create_summary_prompt(self, query: str, result: Dict) -> str:
        """Create an optimized summary prompt using structured information."""
        return f"""Summarize the relevant information about "{query}" from this source.

    Content: {result['content'][:self.max_content_length]}

    Key Data Points:
    - Dates mentioned: {', '.join(result['structured_info']['dates'][:3])}
    - Key statistics: {', '.join(result['structured_info']['numbers'][:3])}
    - Important points: {'; '.join(result['structured_info']['key_points'][:3])}

    Format your response with proper Markdown spacing and structure:

    ## Main Topic

    Provide a brief overview here.

    ### Key Points

    - First important point
    - Second important point
    - Third important point

    ### Details

    Add detailed information here with proper paragraphs.

    Requirements:
    - Add empty lines between sections
    - Use proper heading hierarchy
    - Include bullet points with proper spacing
    - Format dates and numbers clearly
    - Use emphasis where appropriate
    - Start with most important information
    """

    def create_conclusion_prompt(self, query: str, references: List[Dict]) -> str:
        """Create an optimized conclusion prompt using all gathered information."""
        structured_summary = self.summarize_structured_info(references)

        return f"""Provide a comprehensive answer about "{query}" based on all sources.

    {structured_summary}

    Format your response following this structure:

    ## Overview

    Provide a concise introduction here.

    ### Key Findings

    - Important finding one [n]
    - Important finding two [n]
    - Important finding three [n]

    ### Detailed Analysis

    Break down the main points here with proper citations [n].

    ### Additional Context

    Add any relevant context or background information.

    ### Conclusion

    Summarize the key takeaways.

    Requirements:
    - Add empty lines between sections
    - Use consistent heading levels
    - Include proper citations [n]
    - Use bullet points with spacing
    - Format dates and numbers clearly
    - Break paragraphs for readability
    """

    def summarize_structured_info(self, references: List[Dict]) -> str:
        """Summarize structured information from all references."""
        all_dates = []
        all_numbers = []
        all_key_points = []

        for ref in references:
            info = ref["structured_info"]
            all_dates.extend(info["dates"])
            all_numbers.extend(info["numbers"])
            all_key_points.extend(info["key_points"])

        return f"""
- Timeline: {', '.join(sorted(set(all_dates[:5])))}
- Key Statistics: {', '.join(set(all_numbers[:5]))}
- Main Points: {'; '.join(set(all_key_points[:3]))}
- Sources: {', '.join(set(ref['domain'] for ref in references))}"""

    def format_references(self, references: List[Dict]) -> str:
        """Format references with additional metadata."""
        return "\n".join(
            f"[{ref['id']}] [{ref['title']}]({ref['url']}) - {ref['domain']}"
            for ref in references
        )

    async def handle_markdown_streaming(self, buffer: str) -> tuple[str, str]:
        """Handle markdown streaming with smoother output"""
        # Handle special Markdown elements first
        patterns = [
            # Headers
            (r'^(#{1,6}\s+[^\n]+)\n', '\n\n'),
            # Bullet points
            (r'^([*-]\s+[^\n]+)\n', '\n'),
            # Code blocks
            (r'^(```[^\n]*\n[\s\S]*?```)\n', '\n\n'),
            # Blockquotes
            (r'^(>\s+[^\n]+)\n', '\n'),
        ]

        for pattern, spacing in patterns:
            match = re.search(pattern, buffer)
            if match:
                end = match.end()
                content = buffer[:end] + spacing
                return content, buffer[end:]

        # If no special elements, try to break at natural points
        natural_breaks = [
            # End of sentence followed by space and capital letter
            r'([.!?])\s+(?=[A-Z])',
            # Comma followed by space
            r'(,)\s+',
            # Natural word breaks
            r'(\s+)'
        ]

        for pattern in natural_breaks:
            match = re.search(pattern, buffer)
            if match:
                end = match.end()
                return buffer[:end], buffer[end:]

        # If buffer is getting too long without breaks, force a break at a space
        if len(buffer) > 50:  # Adjust this threshold as needed
            space_idx = buffer.rfind(' ')
            if space_idx > 0:
                return buffer[:space_idx+1], buffer[space_idx+1:]

        return "", buffer

    async def stream_markdown_content(self, content_generator):
        """Stream content with smoother output"""
        buffer = ""
        last_yield_time = asyncio.get_event_loop().time()
        min_chunk_size = 10  # Minimum characters to yield
        max_delay = 0.05  # Maximum time to hold content

        async for chunk in content_generator:
            buffer += chunk
            current_time = asyncio.get_event_loop().time()

            # Process buffer if it's long enough or enough time has passed
            while buffer:
                output, new_buffer = await self.handle_markdown_streaming(buffer)

                if output:
                    # For very small chunks, accumulate more unless too much time has passed
                    if len(output) < min_chunk_size and (current_time - last_yield_time) < max_delay:
                        buffer = output + new_buffer
                        continue

                    # Yield the output
                    yield output
                    buffer = new_buffer
                    last_yield_time = current_time

                    # Small delay for natural flow
                    await asyncio.sleep(0.01)
                else:
                    break

            # Don't hold content for too long
            if buffer and (current_time - last_yield_time) > max_delay:
                words = buffer.split()
                if len(words) > 1:
                    yield words[0] + " "
                    buffer = " ".join(words[1:])
                    last_yield_time = current_time

        # Flush any remaining content
        if buffer:
            yield buffer
