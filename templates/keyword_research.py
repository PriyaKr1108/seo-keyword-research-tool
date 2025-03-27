import requests
import trafilatura
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import CountVectorizer
import logging
import re
import random
import time
from urllib.parse import quote_plus

class SEOKeywordAgent:
    """
    A class for SEO keyword research that extracts and optimizes keywords 
    from Google search results and related websites.
    """
    def __init__(self):
        self.keywords = []
        self.search_titles = []
        self.search_snippets = []
        self.top_websites = []
        self.related_searches = []
        self.people_also_ask = []
        self.setup_logging()
        
        # List of user agents to rotate for avoiding blocks
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        
    def setup_logging(self):
        """Set up logging for the SEO keyword agent."""
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("SEOKeywordAgent")
    
    def reset(self):
        """Reset the agent's data."""
        self.keywords = []
        self.search_titles = []
        self.search_snippets = []
        self.top_websites = []
        self.related_searches = []
        self.people_also_ask = []
    
    def fetch_keywords(self, query):
        """
        Fetch keywords from Google search results and top websites for the given query.
        
        Args:
            query (str): The search query to find keywords for
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Reset data for new search
            self.reset()
            
            # Format the query for URL
            formatted_query = quote_plus(query)
            
            # Set headers with a random user agent to avoid being blocked
            random_user_agent = random.choice(self.user_agents)
            headers = {
                'User-Agent': random_user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            # Method 1: Google search - adding result count parameter and language settings
            url = f"https://www.google.com/search?q={formatted_query}&num=30&hl=en&lr=lang_en"
            self.logger.debug(f"Fetching results from: {url}")
            
            # Add slight delay to avoid rate limiting
            time.sleep(0.5)
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch data: Status code {response.status_code}")
                # Try with a different user agent if first attempt fails
                random_user_agent = random.choice(self.user_agents)
                headers['User-Agent'] = random_user_agent
                time.sleep(1)  # Wait a bit longer before retry
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    self.logger.error(f"Second attempt also failed: Status code {response.status_code}")
                    return False
            
            # Extract webpage content using Beautiful Soup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Extract search result titles and snippets
            search_results = []
            
            # Find all search result blocks
            for result in soup.select('div.g'):
                # Extract title
                title_element = result.select_one('h3')
                if title_element:
                    title = title_element.get_text().strip()
                    self.search_titles.append(title)
                    search_results.append(title)
                
                # Extract snippet
                snippet_element = result.select_one('div.VwiC3b')
                if snippet_element:
                    snippet = snippet_element.get_text().strip()
                    self.search_snippets.append(snippet)
                    search_results.append(snippet)
            
            # Add search results to keywords
            if search_results:
                self.logger.debug(f"Extracted {len(search_results)} search results")
                self.keywords.extend(search_results)
            
            # 2. Extract "People also ask" questions
            people_also_ask = []
            paa_elements = soup.select('div.related-question-pair')
            
            if not paa_elements:  # Try alternative selectors if the first one doesn't work
                paa_elements = soup.select('div.g.related-question')
            
            if not paa_elements:
                # Manual extraction as a fallback
                for div in soup.find_all('div'):
                    if div.get_text().strip().startswith('People also ask'):
                        for question_div in div.find_all_next('div', limit=20):
                            question_text = question_div.get_text().strip()
                            if len(question_text) > 10 and len(question_text) < 200:
                                people_also_ask.append(question_text)
            else:
                for question in paa_elements:
                    question_text = question.get_text().strip()
                    if question_text and len(question_text) > 10:
                        people_also_ask.append(question_text)
            
            # Store and add "People also ask" questions to keywords
            if people_also_ask:
                self.logger.debug(f"Found {len(people_also_ask)} 'People also ask' questions")
                self.people_also_ask = people_also_ask
                self.keywords.extend(people_also_ask)
            
            # 3. Extract "Related searches" links
            related_searches = []
            
            # Try with multiple possible selectors
            related_elements = soup.select('div.AJLUJb > div > a')
            
            if not related_elements:
                related_elements = soup.select('div.card-section a.k8XOCe')
            
            if not related_elements:
                # Manual extraction as a fallback
                for div in soup.find_all('div'):
                    if 'related searches' in div.get_text().lower()[:30]:
                        for related_a in div.find_all_next('a', limit=30):
                            related_text = related_a.get_text().strip()
                            if len(related_text) > 3 and len(related_text) < 100:
                                related_searches.append(related_text)
            else:
                for related in related_elements:
                    related_text = related.get_text().strip()
                    if related_text:
                        related_searches.append(related_text)
            
            # Store and add related searches to keywords
            if related_searches:
                self.logger.debug(f"Found {len(related_searches)} related searches")
                self.related_searches = related_searches
                self.keywords.extend(related_searches)
            
            # 4. Extract URLs from the search results page
            links = []
            
            # Find all <a> tags with href attributes
            for a_tag in soup.find_all('a'):
                href = a_tag.get('href', '')
                
                # Google search results use /url?q= to indicate outbound links
                if href.startswith('/url?q='):
                    try:
                        actual_url = href.split('/url?q=')[1].split('&')[0]
                        # Skip Google links and other common non-content sites
                        if not any(domain in actual_url for domain in [
                            'google.com', 'youtube.com', 'facebook.com', 'twitter.com',
                            'instagram.com', 'pinterest.com', 'reddit.com'
                        ]):
                            links.append(actual_url)
                    except IndexError:
                        continue
            
            # Get top 5 unique links (increased from 3)
            unique_links = []
            for link in links:
                if link not in unique_links and len(unique_links) < 5:
                    unique_links.append(link)
            
            # 5. Extract content from top websites in search results
            for i, link in enumerate(unique_links):
                try:
                    self.logger.debug(f"Analyzing website {i+1}: {link}")
                    
                    # Add random delay between requests to avoid rate limiting
                    time.sleep(random.uniform(0.5, 2.0))
                    
                    # Use trafilatura for better content extraction
                    downloaded = trafilatura.fetch_url(
                        link,
                        user_agent=random.choice(self.user_agents),
                        timeout=10
                    )
                    
                    if downloaded:
                        # Extract main content, excluding boilerplate
                        text = trafilatura.extract(
                            downloaded,
                            include_links=False,
                            include_images=False,
                            include_comments=False,
                            favor_precision=True
                        )
                        
                        if text and len(text) > 200:  # Ensure we have meaningful content
                            self.logger.debug(f"Extracted content from {link} ({len(text)} chars)")
                            self.top_websites.append(text)
                            self.keywords.append(text)
                    else:
                        self.logger.warning(f"Failed to download content from {link}")
                        
                except Exception as e:
                    self.logger.warning(f"Error extracting content from {link}: {str(e)}")
                    continue
            
            # 6. Generate additional related keyword variations
            related_terms = self.generate_related_terms(query)
            if related_terms:
                self.keywords.extend(related_terms)
            
            # 7. Make sure we have something to work with
            if not self.keywords or (len(self.keywords) == 1 and len(self.top_websites) == 0):
                self.logger.warning("Insufficient keyword data found, using fallback methods")
                
                # Add the query and its variations as fallback
                self.keywords.append(query)
                
                # Add common SEO word patterns
                if ' ' in query:
                    words = query.split()
                    for word in words:
                        if len(word) >= 4:  # Only use meaningful words
                            self.keywords.append(word)
                
                # Add some variations
                self.keywords.append(f"best {query}")
                self.keywords.append(f"{query} guide")
                self.keywords.append(f"how to {query}")
                self.keywords.append(f"{query} tips")
            
            self.logger.debug(f"Added content from {len(self.top_websites)} websites with {len(self.keywords)} total keyword sources")
            return True
            
        except Exception as e:
            self.logger.error(f"Error fetching keywords: {str(e)}")
            
            # In case of error, fall back to the original query and variations
            self.keywords = [
                query,
                f"best {query}",
                f"{query} guide",
                f"how to {query}",
                f"{query} tips"
            ]
            
            return True  # Return True to continue with minimal processing
    
    def generate_related_terms(self, query):
        """Generate related search terms for the given query."""
        related_terms = []
        
        # Add variations of the query
        words = query.split()
        
        # Add the original query
        related_terms.append(query)
        
        # Add variations with "how to", "what is", etc.
        prefixes = ["how to", "what is", "why", "best", "top", "guide to"]
        for prefix in prefixes:
            related_terms.append(f"{prefix} {query}")
        
        # Add variations with different word orders for queries with multiple words
        if len(words) > 1:
            for i in range(1, len(words)):
                new_query = " ".join(words[i:] + words[:i])
                related_terms.append(new_query)
        
        return related_terms

    def optimize_keywords(self):
        """
        Optimize and rank keywords based on frequency and relevance.
        
        Returns:
            pandas.Series: A series of optimized keywords with counts, sorted by frequency
        """
        try:
            if not self.keywords:
                self.logger.warning("No keywords to optimize")
                return pd.Series()
            
            # Use CountVectorizer to extract keywords
            vectorizer = CountVectorizer(
                stop_words='english',    # Remove common English stop words
                min_df=1,                # Minimum document frequency
                ngram_range=(1, 3),      # Include 1, 2 and 3-word phrases
                token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z0-9+#]{2,}\b|\b[a-zA-Z][a-zA-Z0-9\s]+[a-zA-Z0-9]\b',  # Custom token pattern
                max_features=500         # Limit to top 500 features
            )
            
            X = vectorizer.fit_transform(self.keywords)
            
            # Get feature names (keywords)
            feature_names = vectorizer.get_feature_names_out()
            
            # Create a DataFrame with keywords and their counts
            keywords_df = pd.DataFrame(X.toarray(), columns=feature_names)
            
            # Sum up the counts for each keyword
            keyword_counts = keywords_df.sum().sort_values(ascending=False)
            
            # Filter out keywords with less than 3 characters
            keyword_counts = keyword_counts[keyword_counts.index.str.len() > 3]
            
            # Filter out single words that are likely not valuable for SEO
            # Keep phrases (containing spaces) and more specific single words
            for keyword in list(keyword_counts.index):
                # Skip multi-word phrases as they're usually more valuable
                if ' ' in keyword:
                    continue
                    
                # Filter out common words and short terms that aren't valuable SEO keywords
                if len(keyword) < 5 or keyword.lower() in [
                    'about', 'these', 'those', 'their', 'there', 'where', 'which', 'what', 
                    'when', 'here', 'have', 'more', 'some', 'them', 'with', 'this', 'that', 
                    'from', 'your', 'will', 'would', 'could', 'should', 'than', 'then',
                    'page', 'find', 'just', 'know', 'need', 'like', 'make', 'take', 'want',
                    'well', 'into', 'time', 'year', 'also', 'help', 'look', 'only', 'seen',
                    'very', 'post', 'sure', 'such', 'many', 'other'
                ]:
                    keyword_counts = keyword_counts.drop(keyword)
            
            # Take the top 100 keywords at most
            keyword_counts = keyword_counts.head(100)
            
            self.logger.debug(f"Optimized {len(keyword_counts)} keywords")
            return keyword_counts
            
        except Exception as e:
            self.logger.error(f"Error optimizing keywords: {str(e)}")
            return pd.Series()

    def run(self, query):
        """
        Run the entire keyword research process for the given query.
        
        Args:
            query (str): The search query
            
        Returns:
            pandas.Series: Optimized keywords with their counts
        """
        success = self.fetch_keywords(query)
        if not success:
            self.logger.error("Keyword fetch failed")
            return pd.Series()
            
        optimized_keywords = self.optimize_keywords()
        return optimized_keywords