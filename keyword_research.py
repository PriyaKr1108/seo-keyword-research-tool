import logging
import re
import time
from collections import Counter

import pandas as pd
import requests
from bs4 import BeautifulSoup
import trafilatura


class SEOKeywordAgent:
    """
    A class for SEO keyword research that extracts and optimizes keywords 
    from Google search results and related websites.
    """
    def __init__(self):
        self.setup_logging()
        self.reset()
        
        # Configure headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Stop words to be excluded from keywords
        self.stop_words = set([
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'when', 'where', 'how', 'why', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'can',
            'could', 'should', 'would', 'may', 'might', 'must', 'shall', 'will',
            'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
            'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'all', 'any', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
            'just', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren',
            'couldn', 'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma',
            'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won',
            'wouldn', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
            'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
            'they', 'them', 'their', 'theirs', 'themselves'
        ])
        
    def setup_logging(self):
        """Set up logging for the SEO keyword agent."""
        self.logger = logging.getLogger('SEOKeywordAgent')
        
    def reset(self):
        """Reset the agent's data."""
        self.keywords = Counter()
        self.related_terms = []
        self.people_also_ask = []
        self.website_keywords = []
        
    def fetch_keywords(self, query):
        """
        Fetch keywords from Google search results and top websites for the given query.
        
        Args:
            query (str): The search query to find keywords for
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.reset()
        
        # Format the Google search URL
        search_url = f'https://www.google.com/search?q={query.replace(' ', '+')}&num=30&hl=en&lr=lang_en'
        self.logger.debug(f'Fetching results from: {search_url}')
        
        try:
            # Send the request to Google
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f'Failed to fetch search results: HTTP {response.status_code}')
                return False
                
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search result URLs
            result_divs = soup.find_all('div', class_='g')
            urls = []
            
            for div in result_divs:
                a_tag = div.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    url = a_tag['href']
                    if url.startswith('http') and not url.startswith('https://www.google.com'):
                        urls.append(url)
            
            # Extract 'People also ask' questions
            paa_divs = soup.find_all('div', class_='related-question-pair')
            for div in paa_divs:
                question = div.get_text().strip()
                if question:
                    self.people_also_ask.append(question)
                    self._extract_keywords_from_text(question, is_important=True)
            
            # Extract 'Related searches' at the bottom
            related_divs = soup.find_all('div', class_='BNeawe s3v9rd AP7Wnd')
            for div in related_divs:
                term = div.get_text().strip()
                if term and not term.startswith('Related'):
                    self.related_terms.append(term)
                    self._extract_keywords_from_text(term, is_important=True)
            
            # Process content from top websites
            site_count = 0
            max_sites = 5  # Limit to avoid excessive requests
            
            for url in urls[:max_sites]:
                try:
                    downloaded = trafilatura.fetch_url(url)
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text:
                            self._extract_keywords_from_text(text)
                            site_count += 1
                except Exception as e:
                    self.logger.warning(f'Error extracting content from {url}: {str(e)}')
            
            total_sources = site_count + len(self.people_also_ask) + len(self.related_terms)
            self.logger.debug(f'Added content from {site_count} websites with {total_sources} total keyword sources')
            
            return True
            
        except Exception as e:
            self.logger.exception(f'Error fetching search results: {str(e)}')
            return False
    
    def generate_related_terms(self, query):
        """Generate related search terms for the given query."""
        # Extract individual words from the query
        query_words = query.lower().split()
        
        # Add the original query as a related term
        self.related_terms.append(query)
        
        # Generate variations of the query
        if len(query_words) > 1:
            # Add variations with 'how to', 'what is', etc.
            prefixes = ['how to', 'what is', 'best', 'top', 'guide to']
            for prefix in prefixes:
                self.related_terms.append(f'{prefix} {query}')
        
        # Add keywords from the query to the counter
        self._extract_keywords_from_text(query, is_important=True)
    
    def _extract_keywords_from_text(self, text, is_important=False):
        """
        Extract keywords from the given text and add them to the counter.
        
        Args:
            text (str): The text to extract keywords from
            is_important (bool): Whether the text is from an important source
        """
        if not text:
            return
            
        # Convert to lowercase and clean the text
        text = text.lower()
        
        # Remove URLs, HTML tags, special characters, and excessive whitespace
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<.*?>', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Extract n-grams (1 to 3 words)
        words = text.split()
        
        # Single words (excluding stop words)
        for word in words:
            if word not in self.stop_words and len(word) > 2:
                self.keywords[word] += 2 if is_important else 1
        
        # Bigrams
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        for bigram in bigrams:
            if all(w not in self.stop_words for w in bigram.split()):
                self.keywords[bigram] += 3 if is_important else 2
        
        # Trigrams
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        for trigram in trigrams:
            if all(w not in self.stop_words for w in trigram.split()):
                self.keywords[trigram] += 4 if is_important else 3
    
    def optimize_keywords(self):
        """
        Optimize and rank keywords based on frequency and relevance.
        
        Returns:
            pandas.Series: A series of optimized keywords with counts, sorted by frequency
        """
        if not self.keywords:
            return pd.Series()
            
        # Convert Counter to Series
        keyword_series = pd.Series(self.keywords)
        
        # Filter out keywords that are too short or just numbers
        keyword_series = keyword_series[keyword_series.index.map(lambda x: len(x) > 2 and not x.isdigit())]
        
        # Sort by frequency (descending)
        keyword_series = keyword_series.sort_values(ascending=False)
        
        # Limit to top keywords (e.g., top 100)
        keyword_series = keyword_series.head(100)
        
        self.logger.debug(f'Optimized {len(keyword_series)} keywords')
        
        return keyword_series
        
    def run(self, query):
        """
        Run the entire keyword research process for the given query.
        
        Args:
            query (str): The search query
            
        Returns:
            pandas.Series: Optimized keywords with their counts
        """
        # First generate related terms based on the query
        self.generate_related_terms(query)
        
        # Fetch keywords from search results
        success = self.fetch_keywords(query)
        
        if not success:
            self.logger.warning('Failed to fetch keywords, returning only generated terms')
        
        # Optimize and return the keywords
        return self.optimize_keywords()

