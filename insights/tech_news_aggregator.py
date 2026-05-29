#!/usr/bin/env python3
"""
Enhanced Daily Tech News Aggregator
Collects high-quality insights from TechCrunch, Hacker News, Reddit, and premium tech sources
Improved quality filtering and concept learning focus
"""

import requests
import feedparser
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict, Optional
import re
from dataclasses import dataclass
import os
import base64
from dotenv import load_dotenv
from markdown import markdown as md_to_html
import bleach
from bleach.css_sanitizer import CSSSanitizer
from urllib.parse import urlparse

# Google Gmail API imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    summary: str
    source: str
    score: int = 0
    comments: int = 0
    quality_score: float = 0.0
    category: str = ""
    pub_date: Optional[datetime] = None


class TechNewsAggregator:
    def __init__(self, config: Dict):
        """Initialize the aggregator with configuration"""
        self.config = config
        self.setup_gemini()
        self.brand_logo_url = os.getenv("BRAND_LOGO_URL", "").strip()

        # Enhanced tech keywords for better filtering
        self.tech_keywords = [
            # AI/ML Core
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network",
            "generative ai",
            "large language model",
            "llm",
            "gpt",
            "transformer",
            "diffusion",
            "computer vision",
            "natural language processing",
            "nlp",
            "reinforcement learning",
            # Programming & Development
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "node.js",
            "programming",
            "software development",
            "coding",
            "framework",
            "library",
            "api",
            "rest",
            "graphql",
            "microservices",
            "serverless",
            "lambda",
            # Cloud & Infrastructure
            "cloud computing",
            "aws",
            "azure",
            "google cloud",
            "kubernetes",
            "docker",
            "devops",
            "ci/cd",
            "infrastructure",
            "database",
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            "kafka",
            "terraform",
            "ansible",
            # Startup & Business
            "startup",
            "funding",
            "venture capital",
            "vc",
            "ipo",
            "acquisition",
            "saas",
            "platform",
            "unicorn",
            "series a",
            "series b",
            "series c",
            # Emerging Tech
            "blockchain",
            "cryptocurrency",
            "web3",
            "defi",
            "nft",
            "metaverse",
            "quantum computing",
            "edge computing",
            "5g",
            "iot",
            "robotics",
            "autonomous vehicles",
            "ar",
            "vr",
            "mixed reality",
            # Security & Privacy
            "cybersecurity",
            "security",
            "privacy",
            "encryption",
            "zero trust",
            "data breach",
            "vulnerability",
            "penetration testing",
            "malware",
            # Data & Analytics
            "data science",
            "big data",
            "analytics",
            "business intelligence",
            "data engineering",
            "etl",
            "data pipeline",
            "visualization",
        ]

        # Quality filtering patterns
        self.low_quality_patterns = [
            r"\beli5\b",
            r"\bexplain like.*5\b",
            r"\bhow do i\b",
            r"\bhelp me\b",
            r"\bbeginners?\b",
            r"\btutorial\b",
            r"\blearning\b.*\bstart\b",
            r"\bshowhn\b",
            r"\bask hn\b",
            r"\bmeme\b",
            r"\bjoke\b",
        ]

        # Spam domains to filter out
        self.spam_domains = {
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "tiktok.com",
            "youtube.com",
            "youtu.be",
            "linkedin.com",
            "reddit.com",
        }

    def setup_gemini(self):
        """Configure Google Gemini API"""
        genai.configure(api_key=self.config["gemini_api_key"])
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def fetch_techcrunch_news(self) -> List[NewsItem]:
        """Fetch latest news from TechCrunch with multiple feeds for better coverage"""
        logger.info("Fetching TechCrunch news...")
        news_items = []

        # Multiple TechCrunch feeds for comprehensive coverage
        feeds = [
            ("https://techcrunch.com/feed/", "TechCrunch"),
            ("https://techcrunch.com/category/startups/feed/", "TechCrunch Startups"),
            ("https://techcrunch.com/category/apps/feed/", "TechCrunch Apps"),
            (
                "https://techcrunch.com/category/artificial-intelligence/feed/",
                "TechCrunch AI",
            ),
        ]

        try:
            yesterday = datetime.now() - timedelta(days=1)

            for feed_url, source_name in feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:10]:  # Top 10 per feed
                        # Parse publication date
                        pub_date = (
                            datetime(*entry.published_parsed[:6])
                            if hasattr(entry, "published_parsed")
                            else datetime.now()
                        )

                        # Only include recent articles
                        if pub_date >= yesterday:
                            summary = self._clean_html(entry.get("summary", ""))
                            item = NewsItem(
                                title=entry.title,
                                url=entry.link,
                                summary=summary,
                                source=source_name,
                                pub_date=pub_date,
                                quality_score=1.1,  # TechCrunch gets slight quality boost
                            )

                            # Apply quality filtering
                            if self._passes_quality_filter(item):
                                news_items.append(item)

                    time.sleep(0.2)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Error fetching {feed_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching TechCrunch news: {e}")

        logger.info(f"Retrieved {len(news_items)} TechCrunch articles")
        return news_items

    def fetch_hackernews(self) -> List[NewsItem]:
        """Fetch top stories from Hacker News with better quality filtering"""
        logger.info("Fetching Hacker News stories...")
        news_items = []

        try:
            # Get both top stories and best stories for better coverage
            story_endpoints = [
                (
                    "https://hacker-news.firebaseio.com/v0/topstories.json",
                    "Hacker News",
                ),
                (
                    "https://hacker-news.firebaseio.com/v0/beststories.json",
                    "Hacker News Best",
                ),
            ]

            seen_urls = set()

            for endpoint_url, source_name in story_endpoints:
                try:
                    response = requests.get(endpoint_url, timeout=10)
                    story_ids = response.json()[:20]  # Top 20 from each endpoint

                    for story_id in story_ids:
                        try:
                            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                            story_response = requests.get(story_url, timeout=5)
                            story = story_response.json()

                            if not story or "title" not in story:
                                continue

                            story_link = story.get(
                                "url",
                                f"https://news.ycombinator.com/item?id={story_id}",
                            )

                            # Skip duplicates
                            if story_link in seen_urls:
                                continue
                            seen_urls.add(story_link)

                            # Enhanced tech filtering and quality scoring
                            if self._is_tech_related(story["title"]):
                                item = NewsItem(
                                    title=story["title"],
                                    url=story_link,
                                    summary=self._clean_html(story.get("text", ""))[
                                        :500
                                    ],
                                    source=source_name,
                                    score=story.get("score", 0),
                                    comments=story.get("descendants", 0),
                                    quality_score=self._calculate_hn_quality_score(
                                        story
                                    ),
                                )

                                if self._passes_quality_filter(item):
                                    news_items.append(item)

                            time.sleep(0.1)  # Rate limiting

                        except Exception as e:
                            logger.warning(f"Error fetching story {story_id}: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Error fetching from {endpoint_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching Hacker News: {e}")

        logger.info(f"Retrieved {len(news_items)} Hacker News stories")
        return news_items

    def fetch_reddit_tech(self) -> List[NewsItem]:
        """Fetch tech news from Reddit with enhanced quality filtering"""
        logger.info("Fetching Reddit tech posts...")
        news_items = []

        # Expanded high-quality tech subreddits with minimum score thresholds
        subreddit_config = [
            ("technology", 100, 1.0),
            ("programming", 50, 0.9),
            ("MachineLearning", 30, 1.1),
            ("artificial", 25, 1.2),
            ("startups", 40, 0.8),
            ("webdev", 30, 0.8),
            ("datascience", 25, 0.9),
            ("DevOps", 20, 0.8),
            ("cybersecurity", 20, 0.9),
            ("blockchain", 30, 0.7),
        ]

        try:
            for subreddit, min_score, quality_multiplier in subreddit_config:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15"
                    headers = {"User-Agent": "TechNewsAggregator/2.0"}

                    response = requests.get(url, headers=headers, timeout=10)
                    # Handle rate limiting or forbidden
                    if response.status_code in (429, 403):
                        logger.warning(
                            f"Reddit API rate/forbidden for r/{subreddit} (status {response.status_code}), backing off 5s"
                        )
                        time.sleep(5)
                        continue

                    # Safely parse JSON and guard missing keys
                    try:
                        data = response.json()
                    except Exception:
                        logger.warning(f"Non-JSON response for r/{subreddit}")
                        continue

                    children = (
                        data.get("data", {}).get("children", [])
                        if isinstance(data, dict)
                        else []
                    )
                    if not children:
                        logger.warning(f"No posts payload for r/{subreddit}")
                        continue

                    for post in children:
                        post_data = post["data"]

                        # Enhanced quality filtering
                        if (
                            not post_data.get("stickied", False)
                            and post_data.get("url")
                            and post_data.get("score", 0) >= min_score
                            and not self._is_spam_domain(post_data.get("url", ""))
                        ):
                            # Get better summary from selftext if available
                            summary = self._extract_reddit_summary(post_data)

                            item = NewsItem(
                                title=post_data["title"],
                                url=post_data["url"],
                                summary=summary,
                                source=f"Reddit r/{subreddit}",
                                score=post_data.get("score", 0),
                                comments=post_data.get("num_comments", 0),
                                quality_score=quality_multiplier
                                * (1 + post_data.get("score", 0) / 1000),
                            )

                            if self._passes_quality_filter(item):
                                news_items.append(item)

                    time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Error fetching r/{subreddit}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")

        logger.info(f"Retrieved {len(news_items)} Reddit posts")
        return news_items

    def fetch_premium_sources(self) -> List[NewsItem]:
        """Fetch from premium tech sources for higher quality content"""
        logger.info("Fetching premium tech sources...")
        news_items = []

        # Premium sources with RSS feeds
        premium_feeds = [
            ("https://www.technologyreview.com/feed/", "MIT Technology Review", 1.3),
            ("https://arstechnica.com/rss/", "Ars Technica", 1.2),
            ("https://www.wired.com/feed/rss", "Wired", 1.1),
            ("https://feeds.feedburner.com/venturebeat/SZYF", "VentureBeat", 1.0),
            ("https://github.blog/feed/", "GitHub Blog", 1.2),
            ("https://ai.googleblog.com/feeds/posts/default", "Google AI Blog", 1.4),
            ("https://openai.com/blog/rss/", "OpenAI Blog", 1.4),
        ]

        try:
            yesterday = datetime.now() - timedelta(
                days=2
            )  # Slightly longer window for premium content

            for feed_url, source_name, quality_multiplier in premium_feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:8]:  # Top 8 per feed
                        pub_date = (
                            datetime(*entry.published_parsed[:6])
                            if hasattr(entry, "published_parsed")
                            else datetime.now()
                        )

                        if pub_date >= yesterday:
                            summary = self._clean_html(
                                entry.get("summary", "") or entry.get("description", "")
                            )

                            item = NewsItem(
                                title=entry.title,
                                url=entry.link,
                                summary=summary,
                                source=source_name,
                                pub_date=pub_date,
                                quality_score=quality_multiplier,
                            )

                            if self._passes_quality_filter(item):
                                news_items.append(item)

                    time.sleep(0.3)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Error fetching {source_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching premium sources: {e}")

        logger.info(f"Retrieved {len(news_items)} premium articles")
        return news_items

    def fetch_dev_community(self) -> List[NewsItem]:
        """Fetch from developer community sources"""
        logger.info("Fetching developer community content...")
        news_items = []

        try:
            # Dev.to trending articles
            dev_to_url = (
                "https://dev.to/api/articles?tag=discuss&top=7"  # Last 7 days trending
            )
            headers = {"User-Agent": "TechNewsAggregator/2.0"}

            response = requests.get(dev_to_url, headers=headers, timeout=10)
            articles = response.json()

            for article in articles[:10]:  # Top 10 trending
                if (
                    article.get("positive_reactions_count", 0)
                    >= 20  # Minimum engagement
                    and article.get("comments_count", 0) >= 5
                ):
                    item = NewsItem(
                        title=article["title"],
                        url=article["url"],
                        summary=article.get("description", "")[:300],
                        source="Dev.to",
                        score=article.get("positive_reactions_count", 0),
                        comments=article.get("comments_count", 0),
                        quality_score=0.8,  # Community content gets moderate score
                    )

                    if self._passes_quality_filter(item):
                        news_items.append(item)

        except Exception as e:
            logger.error(f"Error fetching Dev.to content: {e}")

        logger.info(f"Retrieved {len(news_items)} developer community articles")
        return news_items

    def _passes_quality_filter(self, item: NewsItem) -> bool:
        """Enhanced quality filtering for news items"""
        title_lower = item.title.lower()

        # Check for low-quality patterns
        for pattern in self.low_quality_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return False

        # Must be tech-related
        if not self._is_tech_related(item.title):
            return False

        # Check for spam domains
        if self._is_spam_domain(item.url):
            return False

        # Minimum content requirements
        if len(item.title) < 10 or not item.url:
            return False

        return True

    def _is_spam_domain(self, url: str) -> bool:
        """Check if URL is from a spam domain"""
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www prefix
            domain = re.sub(r"^www\.", "", domain)
            return domain in self.spam_domains
        except Exception:
            return False

    def _extract_reddit_summary(self, post_data: Dict) -> str:
        """Extract better summary from Reddit posts"""
        selftext = post_data.get("selftext", "")
        if selftext and len(selftext) > 50:
            # Clean and truncate selftext
            clean_text = re.sub(
                r"\[([^\]]+)\]\([^)]+\)", r"\1", selftext
            )  # Remove markdown links
            clean_text = re.sub(r"[*_`]+", "", clean_text)  # Remove formatting
            return clean_text[:400] + "..." if len(clean_text) > 400 else clean_text
        return post_data.get("title", "")[:200]

    def _calculate_hn_quality_score(self, story: Dict) -> float:
        """Calculate quality score for Hacker News stories"""
        score = story.get("score", 0)
        comments = story.get("descendants", 0)

        # Base quality score
        quality = 1.0

        # Boost based on engagement
        if score > 100:
            quality += 0.3
        if score > 300:
            quality += 0.2

        if comments > 50:
            quality += 0.2
        if comments > 100:
            quality += 0.1

        # Check for high-quality content indicators
        title = story.get("title", "").lower()
        if any(word in title for word in ["research", "paper", "study", "analysis"]):
            quality += 0.2
        if any(
            word in title for word in ["launches", "announces", "releases", "funding"]
        ):
            quality += 0.1

        return quality

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        clean = re.compile("<.*?>")
        text = re.sub(clean, "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_tech_related(self, title: str) -> bool:
        """Enhanced tech relevance checking"""
        title_lower = title.lower()

        # Direct keyword matching
        for keyword in self.tech_keywords:
            if keyword.lower() in title_lower:
                return True

        # Pattern matching for tech concepts
        tech_patterns = [
            r"\b(api|sdk|framework|library|platform)\b",
            r"\b(mobile|web|desktop)\s+(app|application|development)\b",
            r"\b(cloud|saas|paas|iaas)\b",
            r"\b(data|software|tech|digital)\b.*\b(company|startup|platform)\b",
            r"\b(open\s+source|github|gitlab)\b",
        ]

        for pattern in tech_patterns:
            if re.search(pattern, title_lower):
                return True

        return False

    def generate_summary(self, news_items: List[NewsItem]) -> str:
        """Generate enhanced summary with focus on concepts and applications"""
        logger.info("Generating enhanced summary with Gemini...")

        # Rank and prepare content
        ranked_items = self._rank_news_items(news_items)
        content = self._prepare_content_for_summary(ranked_items)

        # Enhanced prompt with focus on practical concepts and applications
        prompt = f"""
        You are a senior tech analyst and educator. Create a comprehensive daily brief that emphasizes PRACTICAL LEARNING and REAL-WORLD APPLICATIONS.

        Structure the brief in Markdown with EXACTLY these H2 sections:

        ## 📊 UPDATES & MARKET MOVES
        - 8-12 unique items, each as a paragraph including:
          - **<Compelling one-sentence headline>**. <Business impact/implications>. <Specific numbers, funding amounts, or comparisons>. <Source> — <url>
        - Focus on: funding rounds, product launches, acquisitions, market shifts, policy changes

        ## 🧠 INSIGHTS & ANALYSIS
        - 6-10 analytical bullet points that connect patterns across the news
        - Each point should: identify a trend, explain its significance, predict implications
        - Reference specific items from Updates (without repeating details)
        - Focus on: market dynamics, competitive landscapes, technology adoption patterns

        ## 📚 CONCEPTS TO LEARN
        - 5-8 technical concepts that appeared in today's news
        - For EACH concept provide:
          - **Concept Name**: Clear 1-sentence definition
          - **Why it matters**: Real-world significance and current relevance
          - **Learn more**: Specific resources (courses, documentation, tutorials)
          - **Quick example**: Concrete use case or implementation detail
        - Prioritize: emerging technologies, architectural patterns, development practices

        ## 🛠️ APPLICATIONS & ARCHITECTURES
        - 4-7 practical implementation patterns from the news
        - For EACH application provide:
          - **Use Case**: What problem it solves
          - **Architecture**: Core components and data flow (2-3 sentences)
          - **Tech Stack**: Specific technologies mentioned or implied
          - **Trade-offs**: Pros/cons or when to use/avoid
        - Focus on: system designs, integration patterns, scaling solutions

        ## 💬 COMMUNITY DISCUSSIONS
        - 6-10 notable conversations and debates
        - Each with: key debate point or insight (1-2 sentences) and <source> — <url>
        - Highlight: controversial opinions, expert insights, community concerns

        CRITICAL REQUIREMENTS:
        - NO repetition across sections - each fact appears once in the most logical section
        - Every paragraph must provide NEW information or perspective
        - In Concepts/Applications sections: be specific and actionable, not generic
        - Include URLs only in Updates and Community sections
        - Make it practical - readers should learn something they can apply

        NEWS INPUT (ranked by quality and relevance):
        {content}
        """

        try:
            # Token counting and generation
            input_tokens = None
            try:
                ct = self.model.count_tokens(prompt)
                input_tokens = getattr(ct, "total_tokens", None) or getattr(
                    ct, "token_count", None
                )
            except Exception:
                input_tokens = None

            response = self.model.generate_content(prompt)

            # Read usage metadata
            output_tokens = None
            total_tokens = None
            try:
                um = getattr(response, "usage_metadata", None)
                if um:
                    output_tokens = getattr(um, "output_token_count", None) or getattr(
                        um, "candidates_token_count", None
                    )
                    if input_tokens is None:
                        input_tokens = getattr(um, "input_token_count", None)
                    total_tokens = getattr(um, "total_token_count", None)
            except Exception:
                pass

            if total_tokens is None and (
                input_tokens is not None or output_tokens is not None
            ):
                total_tokens = (input_tokens or 0) + (output_tokens or 0)

            logger.info(
                f"Gemini token usage — input: {input_tokens or 'n/a'}, "
                f"output: {output_tokens or 'n/a'}, "
                f"total: {total_tokens or 'n/a'}"
            )

            raw = response.text or ""
            cleaned = self._postprocess_summary(raw)
            return cleaned

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._create_fallback_summary(ranked_items)

    def _rank_news_items(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Rank news items by quality score and relevance"""
        # Calculate final scores
        for item in news_items:
            base_score = item.quality_score
            engagement_boost = (item.score + item.comments * 2) / 1000
            recency_boost = (
                0.1
                if item.pub_date and (datetime.now() - item.pub_date).days == 0
                else 0
            )

            item.quality_score = base_score + engagement_boost + recency_boost

        # Sort by quality score descending
        return sorted(news_items, key=lambda x: x.quality_score, reverse=True)

    def _prepare_content_for_summary(self, news_items: List[NewsItem]) -> str:
        """Prepare ranked news content for AI summarization"""
        # De-duplicate items by normalized title
        items = self._dedupe_news_items(news_items)
        content = ""

        # Group by source type for better organization
        source_groups = {
            "Premium": [],
            "TechCrunch": [],
            "Hacker News": [],
            "Reddit": [],
            "Community": [],
        }

        for item in items[:80]:  # Top 80 items
            if (
                "MIT" in item.source
                or "Google AI" in item.source
                or "OpenAI" in item.source
            ):
                source_groups["Premium"].append(item)
            elif "TechCrunch" in item.source:
                source_groups["TechCrunch"].append(item)
            elif "Hacker News" in item.source:
                source_groups["Hacker News"].append(item)
            elif "Reddit" in item.source:
                source_groups["Reddit"].append(item)
            else:
                source_groups["Community"].append(item)

        # Output in priority order
        for group_name, items in source_groups.items():
            if items:
                content += f"\n--- {group_name.upper()} SOURCES ---\n"
                for item in items[:12]:  # Limit items per group
                    content += f"Title: {item.title}\n"
                    if item.summary:
                        content += f"Summary: {item.summary[:400]}...\n"
                    content += f"Source: {item.source}"
                    if item.score > 0:
                        content += f" (Score: {item.score}, Comments: {item.comments})"
                    content += f"\nURL: {item.url}\n\n"

        return content[:12000]  # Increased limit for better content

    def _dedupe_news_items(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Enhanced deduplication with better similarity detection"""
        from urllib.parse import urlparse

        def norm_title(title: str) -> str:
            # More aggressive normalization
            t = title.lower()
            t = re.sub(r"[^a-z0-9\s]", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            # Remove common words that don't affect uniqueness
            stop_words = [
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            ]
            words = [w for w in t.split() if w not in stop_words]
            return " ".join(words)

        def norm_url(url: str) -> str:
            try:
                u = urlparse(url)
                path = re.sub(r"/+$", "", u.path)
                path = re.sub(r"\?.*", "", path)  # Remove query parameters
                return f"{u.netloc}{path}".lower()
            except Exception:
                return ""

        # Use both title similarity and URL similarity
        seen_titles = set()
        seen_urls = set()
        unique_items = []

        for item in news_items:
            title_key = norm_title(item.title)
            url_key = norm_url(item.url)

            # Skip if we've seen very similar title or exact URL
            title_similar = any(
                len(set(title_key.split()) & set(seen)) > len(title_key.split()) * 0.8
                for seen in seen_titles
            )

            if not title_similar and url_key not in seen_urls:
                seen_titles.add(title_key)
                seen_urls.add(url_key)
                unique_items.append(item)

        return unique_items

    def _postprocess_summary(self, markdown_text: str) -> str:
        """Enhanced postprocessing with better structure enforcement"""
        allowed = [
            "UPDATES & MARKET MOVES",
            "INSIGHTS & ANALYSIS",
            "CONCEPTS TO LEARN",
            "APPLICATIONS & ARCHITECTURES",
            "COMMUNITY DISCUSSIONS",
        ]

        lines = markdown_text.splitlines()
        sections: Dict[str, List[str]] = {name: [] for name in allowed}
        current: Optional[str] = None

        header_re = re.compile(r"^##\s+[📊🧠📚🛠️💬]?\s*(.*)$")

        for ln in lines:
            m = header_re.match(ln.strip())
            if m:
                title = m.group(1).strip().upper()
                # Flexible matching for section headers
                for name in allowed:
                    key_words = name.split()[0:2]  # First two words
                    if all(word in title for word in key_words):
                        current = name
                        break
                else:
                    current = None
                continue

            if current and ln.strip():
                sections[current].append(ln.rstrip())

        # Rebuild with emojis
        emoji_map = {
            "UPDATES & MARKET MOVES": "📊",
            "INSIGHTS & ANALYSIS": "🧠",
            "CONCEPTS TO LEARN": "📚",
            "APPLICATIONS & ARCHITECTURES": "🛠️",
            "COMMUNITY DISCUSSIONS": "💬",
        }

        out: List[str] = []
        for name in allowed:
            content = [line for line in sections[name] if line.strip()]
            if not content:
                continue
            out.append(f"## {emoji_map[name]} {name}")
            out.extend(content)
            out.append("")

        return "\n".join(out).strip()

    def _create_fallback_summary(self, news_items: List[NewsItem]) -> str:
        """Enhanced fallback summary with better structure"""
        summary = (
            f"# 📰 Daily Tech News Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        )

        # Group by source type
        sources = {}
        for item in news_items[:50]:  # Top 50 items
            source_type = (
                "Premium"
                if any(
                    x in item.source for x in ["MIT", "Google AI", "OpenAI", "GitHub"]
                )
                else item.source
            )
            if source_type not in sources:
                sources[source_type] = []
            sources[source_type].append(item)

        for source_type, items in sources.items():
            if items:
                summary += f"## {source_type}\n"
                for item in items[:8]:  # Top 8 per source
                    summary += f"- **{item.title}**\n"
                    if item.summary:
                        summary += f"  {item.summary[:250]}...\n"
                    summary += f"  [{item.source}]({item.url})\n"
                    if item.score > 0:
                        summary += f"  Score: {item.score}, Comments: {item.comments}\n"
                    summary += "\n"

        return summary

    def _get_gmail_credentials(self) -> Credentials:
        """Load or fetch Gmail API OAuth2 credentials"""
        scopes = ["https://www.googleapis.com/auth/gmail.send"]
        creds: Optional[Credentials] = None

        token_path = self.config.get("gmail_token_path", "token.json")

        # Prefer headless env: use pre-provisioned refresh token if provided
        env_client_id = (self.config.get("gmail_client_id") or "").strip()
        env_client_secret = (self.config.get("gmail_client_secret") or "").strip()
        env_refresh_token = (os.getenv("GMAIL_REFRESH_TOKEN") or "").strip()

        if env_client_id and env_client_secret and env_refresh_token:
            creds = Credentials(
                token=None,
                refresh_token=env_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=env_client_id,
                client_secret=env_client_secret,
                scopes=scopes,
            )
            try:
                creds.refresh(Request())
                # Optionally persist refreshed credentials
                with open(token_path, "w") as token_file:
                    token_file.write(creds.to_json())
                return creds
            except Exception as e:
                logger.error(
                    f"Failed to refresh Gmail credentials from GMAIL_REFRESH_TOKEN: {e}"
                )

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Build client config inline from Client ID/Secret
                client_id = env_client_id or self.config.get("gmail_client_id")
                client_secret = env_client_secret or self.config.get(
                    "gmail_client_secret"
                )
                if not client_id or not client_secret:
                    raise RuntimeError("Missing GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET")

                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:/"],
                    }
                }

                flow = InstalledAppFlow.from_client_config(client_config, scopes)
                auth_mode = (
                    self.config.get("gmail_auth_mode") or "localserver"
                ).lower()
                if auth_mode == "console":
                    logger.warning(
                        "GMAIL_AUTH_MODE=console is deprecated; using localserver with open_browser=False"
                    )
                    creds = flow.run_local_server(
                        port=0,
                        open_browser=False,
                        authorization_prompt_message="Please visit this URL to authorize: {url}",
                        success_message="Authorization complete. You can close this tab.",
                    )
                else:
                    creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return creds

    def send_email(self, summary: str):
        """Send email with the daily summary using Gmail API"""
        logger.info("Sending email summary via Gmail API...")

        try:
            recipient = (self.config.get("recipient_email") or "").strip()
            if not recipient:
                logger.warning("Skipping email: recipient_email not configured.")
                return

            # Build Gmail service
            creds = self._get_gmail_credentials()
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)

            # Build MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"📰 Daily Tech News Summary - {datetime.now().strftime('%B %d, %Y')}"
            )
            msg["From"] = (
                self.config.get("smtp_username")
                or self.config.get("sender_email")
                or "me"
            )
            msg["To"] = recipient

            html_content = self._convert_to_html(summary)
            text_part = MIMEText(summary, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)

            # Encode and send message
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            body = {"raw": raw}

            # Send with retry logic
            attempts = 0
            while True:
                try:
                    service.users().messages().send(userId="me", body=body).execute()
                    logger.info("Email sent successfully via Gmail API!")
                    break
                except Exception as send_err:
                    attempts += 1
                    if attempts >= 3:
                        raise send_err
                    sleep_for = 2**attempts
                    logger.warning(
                        f"Send failed (attempt {attempts}), retrying in {sleep_for}s..."
                    )
                    time.sleep(sleep_for)

        except Exception as e:
            logger.error(f"Error sending email via Gmail API: {e}")

    def _convert_to_html(self, summary: str) -> str:
        """Convert Markdown to HTML with enhanced styling"""
        # Render Markdown to HTML
        body_html = md_to_html(
            summary,
            extensions=[
                "extra",
                "sane_lists",
                "nl2br",
                "codehilite",
            ],
            output_format="html5",
        )

        # Sanitize HTML
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union(
            {
                "p",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "pre",
                "code",
                "blockquote",
                "hr",
                "br",
                "ul",
                "ol",
                "li",
                "strong",
                "em",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
                "div",
            }
        )
        allowed_attrs = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            "a": ["href", "title"],
            "img": ["src", "alt", "title", "width", "height", "style"],
            "div": ["style", "class"],
            "span": ["style", "class"],
            "p": ["style"],
            "h1": ["style"],
            "h2": ["style"],
            "h3": ["style"],
        }

        # Configure CSS sanitizer to allow a safe subset of inline styles
        css_sanitizer = CSSSanitizer(
            allowed_css_properties={
                "color",
                "background",
                "background-color",
                "padding",
                "margin",
                "border",
                "border-color",
                "border-style",
                "border-width",
                "font-size",
                "font-weight",
                "text-decoration",
                "display",
                "gap",
                "align-items",
                "vertical-align",
                "line-height",
                "border-radius",
                "box-shadow",
                "width",
                "height",
            },
            allowed_svg_properties=set(),
        )

        sanitized = bleach.clean(
            body_html,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True,
            css_sanitizer=css_sanitizer,
        )
        sanitized = bleach.linkify(sanitized)

        # Enhanced styling for better readability
        logo_html = (
            f'<img src="{self.brand_logo_url}" alt="Logo" width="32" height="32" '
            f'style="display:inline-block;border-radius:8px;margin-right:12px;vertical-align:middle;" />'
            if self.brand_logo_url
            else "📰"
        )

        template = f"""
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily Tech News</title>
          </head>
          <body style="margin:0;padding:0;background:#f8fafc;font-family:'Segoe UI',Arial,sans-serif;">
            <div style="max-width:900px;margin:0 auto;background:#ffffff;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
              <!-- Header -->
              <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:32px 24px;text-align:center;">
                <div style="display:inline-flex;align-items:center;gap:12px;">
                  {logo_html}
                  <div>
                    <h1 style="margin:0 0 8px 0;font-size:28px;font-weight:700;">Daily Tech News</h1>
                    <div style="font-size:16px;opacity:0.9;">{datetime.now().strftime("%B %d, %Y")}</div>
                  </div>
                </div>
              </div>

              <!-- Content -->
              <div style="padding:32px 24px;font-size:16px;line-height:1.7;color:#1e293b;">
                <style>
                  h2 {{
                    color:#1e40af;
                    font-size:22px;
                    font-weight:700;
                    margin:32px 0 16px 0;
                    padding-bottom:8px;
                    border-bottom:2px solid #e0e7ff;
                  }}
                  h3 {{
                    color:#3730a3;
                    font-size:18px;
                    margin:24px 0 12px 0;
                  }}
                  ul {{
                    padding-left:0;
                    list-style:none;
                  }}
                  li {{
                    margin-bottom:16px;
                    padding:12px 0;
                    border-bottom:1px solid #f1f5f9;
                  }}
                  li:last-child {{
                    border-bottom:none;
                  }}
                  strong {{
                    color:#0f172a;
                    font-weight:600;
                  }}
                  a {{
                    color:#2563eb;
                    text-decoration:none;
                    font-weight:500;
                  }}
                  a:hover {{
                    text-decoration:underline;
                  }}
                  code {{
                    background:#f1f5f9;
                    padding:2px 6px;
                    border-radius:4px;
                    font-family:Consolas,'Monaco',monospace;
                    font-size:14px;
                  }}
                </style>
                {sanitized}
              </div>

              <!-- Footer -->
              <div style="background:#f8fafc;padding:24px;text-align:center;border-top:1px solid #e2e8f0;">
                <p style="margin:0;color:#64748b;font-size:14px;">
                  🤖 Generated by Enhanced Tech News Aggregator<br>
                  <small>Sources: TechCrunch, Hacker News, Reddit, MIT Tech Review, and more</small>
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        return template

    def run_daily_summary(self):
        """Run the complete enhanced daily summary process"""
        logger.info("Starting enhanced daily tech news summary...")

        try:
            # Collect news from all sources
            all_news = []

            # Core sources
            all_news.extend(self.fetch_techcrunch_news())
            all_news.extend(self.fetch_hackernews())
            all_news.extend(self.fetch_reddit_tech())

            # Premium sources for better concepts and applications
            all_news.extend(self.fetch_premium_sources())
            all_news.extend(self.fetch_dev_community())

            logger.info(f"Total articles collected: {len(all_news)}")

            # Rank by quality and relevance
            ranked_news = self._rank_news_items(all_news)
            logger.info(f"Top articles after ranking: {len(ranked_news[:80])}")

            # Generate enhanced summary
            summary = self.generate_summary(ranked_news)

            # Send email
            self.send_email(summary)

            # Optional: Save summary to file
            summary_file = f"daily_summary_{datetime.now().strftime('%Y%m%d')}.md"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Summary saved to {summary_file}")

            logger.info("Enhanced daily summary completed successfully!")

        except Exception as e:
            logger.error(f"Error in daily summary process: {e}")
            raise


def main():
    """Main execution function"""

    # Enhanced configuration
    config = {
        # Gmail API OAuth
        "gmail_client_id": os.getenv("GMAIL_CLIENT_ID"),
        "gmail_client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
        "gmail_token_path": os.getenv("GMAIL_TOKEN_FILE", "token.json"),
        "gmail_auth_mode": os.getenv("GMAIL_AUTH_MODE", "localserver"),
        # Email settings
        "smtp_username": os.getenv("SMTP_USERNAME", ""),
        "sender_email": os.getenv("SENDER_EMAIL", ""),
        "recipient_email": os.getenv("RECIPIENT_EMAIL", "kartikpatel0170@gmail.com"),
        # API keys
        "gemini_api_key": os.getenv("GEMINI_API_KEY", "your_gemini_api_key"),
    }

    # Validate required configuration
    required_fields = ["gmail_client_id", "gmail_client_secret", "gemini_api_key"]
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        logger.error(f"Missing required configuration: {missing_fields}")
        logger.error("Please set the following environment variables:")
        for field in missing_fields:
            logger.error(f"  {field.upper()}")
        return

    # Create and run aggregator
    try:
        aggregator = TechNewsAggregator(config)
        aggregator.run_daily_summary()
    except Exception as e:
        logger.error(f"Failed to run aggregator: {e}")
        raise


if __name__ == "__main__":
    main()
