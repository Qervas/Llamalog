from bs4 import BeautifulSoup, Tag, NavigableString
import trafilatura
from readability import Document
import html2text
from typing import Dict, Optional, TypedDict, Any
import re
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentMetadata(TypedDict):
    description: Optional[str]
    keywords: Optional[str]
    author: Optional[str]
    published_date: Optional[str]
    modified_date: Optional[str]
    structured_data: Optional[Dict[str, Any]]

class ExtractedContent(TypedDict):
    title: str
    main_content: str
    metadata: ContentMetadata
    summary: str
    timestamp: str
    url: str

class ContentExtractor:
    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.ignore_tables = False

    async def extract_content(self, html: str, url: str) -> ExtractedContent:
        """Extract clean, structured content from HTML"""
        try:
            # Create soup object
            soup = BeautifulSoup(html, 'html.parser')

            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'ads', 'noscript']):
                element.decompose()

            content: ExtractedContent = {
                'title': self._extract_title(soup),
                'main_content': await self._extract_main_content(soup, html),
                'metadata': self._extract_metadata(soup),
                'summary': await self._generate_summary(soup),
                'timestamp': datetime.utcnow().isoformat(),
                'url': url
            }

            return content

        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                'title': '',
                'main_content': '',
                'metadata': {
                    'description': None,
                    'keywords': None,
                    'author': None,
                    'published_date': None,
                    'modified_date': None,
                    'structured_data': None
                },
                'summary': '',
                'timestamp': datetime.utcnow().isoformat(),
                'url': url
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title with fallbacks"""
        # Try meta title first
        meta_title = soup.find('meta', property='og:title')
        if meta_title and isinstance(meta_title, Tag):  # Type check
            content = meta_title.get('content')
            if content:
                return content.strip()

        # Try regular title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.text.strip()

        # Try h1 tag
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.text.strip()

        return ''

    async def _extract_main_content(self, soup: BeautifulSoup, html: str) -> str:
        """Extract main content using multiple methods"""
        # Try trafilatura first (usually best results)
        extracted = trafilatura.extract(html, include_tables=True, include_links=True)
        if extracted:
            return self._clean_text(extracted)

        # Try readability as fallback
        try:
            doc = Document(html)
            content = doc.summary()
            if content:
                return self._clean_text(self.h2t.handle(content))
        except Exception as e:
            logger.warning(f"Readability extraction failed: {str(e)}")

        # Last resort: find main content area
        main_tags = ['main', 'article', '[role="main"]', '#content', '.content', '#main', '.main']
        for tag in main_tags:
            main_content = soup.select_one(tag)
            if main_content and isinstance(main_content, Tag):  # Type check
                return self._clean_text(self.h2t.handle(str(main_content)))

        # If all else fails, get all paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            texts = []
            for p in paragraphs:
                if isinstance(p, Tag):  # Type check
                    texts.append(p.text)
            return self._clean_text(' '.join(texts))

        return ''

    def _extract_metadata(self, soup: BeautifulSoup) -> ContentMetadata:
        """Extract metadata from page"""
        metadata: ContentMetadata = {
            'description': None,
            'keywords': None,
            'author': None,
            'published_date': None,
            'modified_date': None,
            'structured_data': None
        }

        # Extract meta tags
        meta_tags = {
            'description': ['description', 'og:description'],
            'keywords': ['keywords'],
            'author': ['author', 'og:author'],
            'published_date': ['article:published_time', 'publishedDate'],
            'modified_date': ['article:modified_time', 'lastModified'],
        }

        for key, meta_names in meta_tags.items():
            for name in meta_names:
                meta = soup.find('meta', attrs={'name': name}) or soup.find('meta', attrs={'property': name})
                if meta and isinstance(meta, Tag):  # Type check
                    content = meta.get('content')
                    if content:
                        metadata[key] = content
                        break

        # Extract structured data
        for script in soup.find_all('script', type='application/ld+json'):
            if isinstance(script, Tag):  # Type check
                try:
                    if script.string:
                        data = json.loads(script.string)
                        metadata['structured_data'] = data
                        break
                except:
                    continue

        return metadata

    async def _generate_summary(self, soup: BeautifulSoup) -> str:
        """Generate a brief summary of the content"""
        # Get the first few paragraphs
        paragraphs = soup.find_all('p')
        if not paragraphs:
            return ''

        # Combine first few paragraphs (up to 3)
        texts = []
        for p in paragraphs[:3]:
            if isinstance(p, Tag):  # Type check
                texts.append(p.text.strip())
        summary_text = ' '.join(texts)
        return self._clean_text(summary_text)[:1000]  # Limit 1000 characters

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ''

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove duplicate newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)

        # Fix common encoding issues
        text = text.replace('â€™', "'")
        text = text.replace('â€"', "—")
        text = text.replace('â€œ', '"')
        text = text.replace('â€', '"')

        # Remove any remaining HTML entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)

        # Clean up spaces around punctuation
        text = re.sub(r'\s+([,.!?])', r'\1', text)

        return text.strip()
