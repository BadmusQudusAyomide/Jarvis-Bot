import requests
import json
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class WebTools:
    """
    Web-based tools for gathering real-time information.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_web(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        Search the web for information using DuckDuckGo.
        
        Args:
            query (str): Search query
            num_results (int): Number of results to return
            
        Returns:
            List[Dict]: Search results with title, snippet, and URL
        """
        try:
            # Use DuckDuckGo instant answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            results = []
            
            # Get abstract if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('AbstractSource', 'Web Search'),
                    'snippet': data.get('Abstract'),
                    'url': data.get('AbstractURL', '')
                })
            
            # Get related topics
            for topic in data.get('RelatedTopics', [])[:num_results-len(results)]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                        'snippet': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })
            
            return results[:num_results]
            
        except Exception as e:
            return [{'title': 'Search Error', 'snippet': f'Could not search: {str(e)}', 'url': ''}]
    
    def get_weather(self, location: str) -> Dict:
        """
        Get current weather information for a location.
        
        Args:
            location (str): Location name or coordinates
            
        Returns:
            Dict: Weather information
        """
        try:
            # Using OpenWeatherMap-like free API (wttr.in)
            url = f"https://wttr.in/{location}?format=j1"
            response = self.session.get(url)
            data = response.json()
            
            current = data['current_condition'][0]
            
            return {
                'location': location,
                'temperature': f"{current['temp_C']}°C ({current['temp_F']}°F)",
                'condition': current['weatherDesc'][0]['value'],
                'humidity': f"{current['humidity']}%",
                'wind': f"{current['windspeedKmph']} km/h",
                'feels_like': f"{current['FeelsLikeC']}°C",
                'visibility': f"{current['visibility']} km"
            }
            
        except Exception as e:
            return {'error': f'Could not get weather for {location}: {str(e)}'}
    
    def get_news_headlines(self, category: str = 'general', count: int = 5) -> List[Dict]:
        """
        Get latest news headlines.
        
        Args:
            category (str): News category
            count (int): Number of headlines to return
            
        Returns:
            List[Dict]: News headlines
        """
        try:
            # Using RSS feeds for free news access
            rss_urls = {
                'general': 'https://feeds.bbci.co.uk/news/rss.xml',
                'technology': 'https://feeds.bbci.co.uk/news/technology/rss.xml',
                'science': 'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
                'business': 'https://feeds.bbci.co.uk/news/business/rss.xml',
                'world': 'https://feeds.bbci.co.uk/news/world/rss.xml'
            }
            
            url = rss_urls.get(category, rss_urls['general'])
            response = self.session.get(url)
            
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            
            headlines = []
            for item in root.findall('.//item')[:count]:
                title = item.find('title')
                description = item.find('description')
                link = item.find('link')
                pub_date = item.find('pubDate')
                
                headlines.append({
                    'title': title.text if title is not None else 'No title',
                    'description': description.text if description is not None else 'No description',
                    'url': link.text if link is not None else '',
                    'published': pub_date.text if pub_date is not None else ''
                })
            
            return headlines
            
        except Exception as e:
            return [{'title': 'News Error', 'description': f'Could not fetch news: {str(e)}', 'url': '', 'published': ''}]
    
    def scrape_webpage(self, url: str) -> Dict:
        """
        Scrape content from a webpage.
        
        Args:
            url (str): URL to scrape
            
        Returns:
            Dict: Scraped content including title and text
        """
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else 'No title'
            
            # Get main content
            # Try to find main content areas
            content_selectors = ['main', 'article', '.content', '#content', '.post', '.entry']
            content_text = ""
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    content_text = content.get_text().strip()
                    break
            
            # Fallback to body if no main content found
            if not content_text:
                body = soup.find('body')
                if body:
                    content_text = body.get_text().strip()
            
            # Clean up text
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = content_text[:2000]  # Limit to 2000 characters
            
            return {
                'title': title_text,
                'content': content_text,
                'url': url,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'title': 'Scraping Error',
                'content': f'Could not scrape {url}: {str(e)}',
                'url': url,
                'status': 'error'
            }
    
    def get_cryptocurrency_prices(self, coins: List[str] = None) -> Dict:
        """
        Get current cryptocurrency prices.
        
        Args:
            coins (List[str]): List of coin symbols (default: BTC, ETH, ADA)
            
        Returns:
            Dict: Cryptocurrency prices
        """
        if coins is None:
            coins = ['bitcoin', 'ethereum', 'cardano']
        
        try:
            # Using CoinGecko free API
            coins_str = ','.join(coins)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coins_str}&vs_currencies=usd&include_24hr_change=true"
            
            response = self.session.get(url)
            data = response.json()
            
            prices = {}
            for coin, info in data.items():
                prices[coin] = {
                    'price': f"${info['usd']:,.2f}",
                    'change_24h': f"{info['usd_24h_change']:+.2f}%"
                }
            
            return prices
            
        except Exception as e:
            return {'error': f'Could not fetch crypto prices: {str(e)}'}
    
    def translate_text(self, text: str, target_language: str = 'en') -> Dict:
        """
        Translate text using a free translation service.
        
        Args:
            text (str): Text to translate
            target_language (str): Target language code
            
        Returns:
            Dict: Translation result
        """
        try:
            # Using MyMemory free translation API
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': f'auto|{target_language}'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data['responseStatus'] == 200:
                return {
                    'original': text,
                    'translated': data['responseData']['translatedText'],
                    'source_language': data['responseData'].get('detectedLanguage', 'auto'),
                    'target_language': target_language,
                    'status': 'success'
                }
            else:
                return {'error': 'Translation failed', 'status': 'error'}
                
        except Exception as e:
            return {'error': f'Translation error: {str(e)}', 'status': 'error'}
