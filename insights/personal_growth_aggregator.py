#!/usr/bin/env python3
"""
Personal Growth & Finance Insights Aggregator
Collects actionable insights from Reddit communities focused on personal finance,
life pro tips, wealth building, and personal development
"""

import requests
import feedparser
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
import json
import logging
from typing import List, Dict, Optional, Tuple
import re
from dataclasses import dataclass
import os
import base64
from dotenv import load_dotenv
from markdown import markdown as md_to_html
import bleach
from bleach.css_sanitizer import CSSSanitizer
from urllib.parse import urlparse, urljoin

# Google Gmail API imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class InsightItem:
    title: str
    url: str
    summary: str
    source: str
    score: int = 0
    comments: int = 0
    quality_score: float = 0.0
    category: str = ""
    pub_date: Optional[datetime] = None
    flair: str = ""

class PersonalGrowthAggregator:
    def __init__(self, config: Dict):
        """Initialize the aggregator with configuration"""
        self.config = config
        self.setup_gemini()
        self.brand_logo_url = os.getenv('BRAND_LOGO_URL', '').strip()

        # Enhanced keywords for personal growth and finance
        self.finance_keywords = [
            # Personal Finance Core
            'budgeting', 'budget', 'savings', 'investment', 'investing', 'portfolio',
            'retirement', '401k', 'ira', 'roth ira', 'emergency fund', 'debt',
            'credit score', 'mortgage', 'refinance', 'student loan', 'compound interest',
            'dividend', 'etf', 'mutual fund', 'index fund', 'stocks', 'bonds',

            # Wealth Building
            'wealth building', 'passive income', 'side hustle', 'real estate',
            'financial independence', 'fire', 'early retirement', 'net worth',
            'asset allocation', 'diversification', 'tax optimization', 'tax strategy',

            # Career & Income
            'salary negotiation', 'career change', 'promotion', 'raise', 'job search',
            'freelancing', 'remote work', 'skill development', 'certification',
            'networking', 'linkedin', 'resume', 'interview',

            # Life Skills & Productivity
            'productivity', 'time management', 'habit formation', 'goal setting',
            'meal prep', 'organization', 'decluttering', 'minimalism',
            'health', 'exercise', 'mental health', 'mindfulness', 'meditation',

            # Money Management
            'insurance', 'health insurance', 'life insurance', 'bank account',
            'credit card', 'cashback', 'rewards', 'frugal', 'cost cutting',
            'grocery budget', 'utilities', 'subscription', 'phone bill'
        ]

        # Quality filtering patterns for low-value content
        self.low_quality_patterns = [
            r'\bmeme\b', r'\bjoke\b', r'\bshitpost\b', r'\bcirclejerk\b',
            r'\brant\b', r'\bventing\b', r'\boff my chest\b',
            r'\bupvote if\b', r'\bkarma\b', r'\bfirst post\b'
        ]

        # Spam domains to filter out
        self.spam_domains = {
            'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'tiktok.com',
            'youtube.com', 'youtu.be', 'linkedin.com'
        }

    def setup_gemini(self):
        """Configure Google Gemini API"""
        genai.configure(api_key=self.config['gemini_api_key'])
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def fetch_reddit_insights(self) -> List[InsightItem]:
        """Fetch insights from Reddit personal growth communities"""
        logger.info("Fetching Reddit personal growth content...")
        insights = []

        # Targeted subreddit configuration with quality thresholds
        subreddit_config = [
            # Personal Finance
            ('personalfinance', 25, 1.2, 'Personal Finance'),
            ('PersonalFinanceCanada', 20, 1.1, 'Personal Finance'),
            ('financialindependence', 30, 1.3, 'Wealth Building'),
            ('investing', 25, 1.1, 'Investing'),
            # ('SecurityCareer', 15, 0.9, 'Career'),
            ('povertyfinance', 20, 1.0, 'Personal Finance'),
            ('Frugal', 15, 0.9, 'Money Saving'),

            # Life Improvement
            ('LifeProTips', 50, 1.2, 'Life Skills'),
            ('YouShouldKnow', 30, 1.1, 'Life Skills'),
            ('productivity', 15, 1.0, 'Productivity'),
            # ('getmotivated', 20, 0.8, 'Motivation'),
            # ('selfimprovement', 15, 1.0, 'Personal Development'),
            # ('DecidingToBeBetter', 10, 1.0, 'Personal Development'),
            # ('habits', 10, 1.1, 'Habit Formation'),

            # Career & Professional
            ('cscareerquestions', 20, 1.0, 'Career'),
            # ('ITCareerQuestions', 15, 0.9, 'Career'),
            ('entrepreneur', 25, 1.0, 'Business'),

            # Health & Lifestyle
            ('loseit', 20, 0.8, 'Health'),
            ('getdisciplined', 15, 1.0, 'Personal Development'),
            ('minimalism', 15, 0.9, 'Lifestyle'),

            # Money Specific
            # ('budgetfood', 10, 0.9, 'Money Saving'),
            # ('couponsharing', 5, 0.7, 'Money Saving'),
            ('beermoney', 10, 0.8, 'Side Income'),
            ('sidehustle', 15, 1.0, 'Side Income'),
        ]

        try:
            for subreddit, min_score, quality_multiplier, category in subreddit_config:
                try:
                    # Fetch from multiple sorting methods for better coverage
                    sort_methods = ['hot', 'top', 'rising']

                    for sort_method in sort_methods:
                        time_param = '&t=day' if sort_method == 'top' else ''
                        url = f"https://www.reddit.com/r/{subreddit}/{sort_method}.json?limit=10{time_param}"
                        headers = {'User-Agent': 'PersonalGrowthAggregator/1.0'}

                        response = requests.get(url, headers=headers, timeout=10)

                        # Handle rate limiting
                        if response.status_code in (429, 403):
                            logger.warning(f"Reddit rate limit for r/{subreddit}, backing off 3s")
                            time.sleep(3)
                            continue

                        try:
                            data = response.json()
                        except Exception:
                            logger.warning(f"Non-JSON response for r/{subreddit}")
                            continue

                        children = data.get('data', {}).get('children', [])
                        if not children:
                            continue

                        for post in children[:5]:  # Top 5 per sort method
                            post_data = post['data']

                            # Enhanced quality filtering
                            if (not post_data.get('stickied', False) and
                                not post_data.get('is_self', False) or
                                len(post_data.get('selftext', '')) > 100) and \
                                post_data.get('score', 0) >= min_score and \
                                not self._is_spam_domain(post_data.get('url', '')) and \
                                not post_data.get('over_18', False):

                                # Get comprehensive summary
                                summary = self._extract_reddit_summary(post_data)

                                # Check if content is relevant
                                if self._is_growth_related(post_data['title'], summary):
                                    item = InsightItem(
                                        title=post_data['title'],
                                        url=post_data.get('url', f"https://reddit.com{post_data['permalink']}"),
                                        summary=summary,
                                        source=f"Reddit r/{subreddit}",
                                        score=post_data.get('score', 0),
                                        comments=post_data.get('num_comments', 0),
                                        quality_score=quality_multiplier * (1 + post_data.get('score', 0) / 500),
                                        category=category,
                                        flair=post_data.get('link_flair_text', ''),
                                        pub_date=datetime.fromtimestamp(post_data.get('created_utc', 0))
                                    )

                                    if self._passes_quality_filter(item):
                                        insights.append(item)

                        time.sleep(0.3)  # Rate limiting between sort methods

                    time.sleep(0.8)  # Rate limiting between subreddits

                except Exception as e:
                    logger.warning(f"Error fetching r/{subreddit}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching Reddit insights: {e}")

        logger.info(f"Retrieved {len(insights)} Reddit insights")
        return insights

    def fetch_finance_blogs(self) -> List[InsightItem]:
        """Fetch content from popular personal finance blogs"""
        logger.info("Fetching finance blog content...")
        insights = []

        # Popular finance blogs with RSS feeds
        blog_feeds = [
            ("https://www.bogleheads.org/blog/feed/", "Bogleheads", 1.4, "Investing"),
            ("https://awealthofcommonsense.com/feed/", "A Wealth of Common Sense", 1.4, "Investing"),
            ("https://www.mrmoneymustache.com/feed/", "Mr. Money Mustache", 1.3, "Financial Independence"),
            ("https://www.financialsamurai.com/feed/", "Financial Samurai", 1.3, "Personal Finance"),
            ("https://www.madfientist.com/feed/", "Mad Fientist", 1.3, "Financial Independence"),
            ("https://ofdollarsanddata.com/feed/", "Of Dollars and Data", 1.4, "Data-Driven Investing"),
            ("https://humbledollar.com/feed/", "Humble Dollar", 1.3, "Personal Finance"),
        ]

        try:
            cutoff_date = datetime.now() - timedelta(days=7)  # Last week

            for feed_url, source_name, quality_multiplier, category in blog_feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:5]:  # Top 5 per feed
                        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()

                        if pub_date >= cutoff_date:
                            summary = self._clean_html(entry.get('summary', '') or entry.get('description', ''))

                            item = InsightItem(
                                title=entry.title,
                                url=entry.link,
                                summary=summary,
                                source=source_name,
                                pub_date=pub_date,
                                quality_score=quality_multiplier,
                                category=category
                            )

                            if self._passes_quality_filter(item):
                                insights.append(item)

                    time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Error fetching {source_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching finance blogs: {e}")

        logger.info(f"Retrieved {len(insights)} blog insights")
        return insights

    def fetch_lifestyle_sources(self) -> List[InsightItem]:
        """Fetch content from lifestyle and productivity sources"""
        logger.info("Fetching lifestyle and productivity content...")
        insights = []

        lifestyle_feeds = [
            ("https://zenhabits.net/feed/", "Zen Habits", 1.3, "Mindfulness & Simplicity"),
            ("https://jamesclear.com/feed", "James Clear", 1.5, "Habit Formation"),
            ("https://calnewport.com/feed/", "Cal Newport", 1.4, "Deep Work & Productivity"),
            ("https://www.becomingminimalist.com/feed/", "Becoming Minimalist", 1.2, "Minimalism & Lifestyle"),
            ("https://matthewgmiller.com/feed/", "Matt D'Avella", 1.2, "Minimalism & Habits"),
            ("https://alistapart.com/main/feed/", "A List Apart", 1.2, "Work & Creativity"),
        ]

        try:
            cutoff_date = datetime.now() - timedelta(days=5)

            for feed_url, source_name, quality_multiplier, category in lifestyle_feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:6]:  # Top 6 per feed
                        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()

                        if pub_date >= cutoff_date:
                            summary = self._clean_html(entry.get('summary', '') or entry.get('description', ''))

                            # Check if content is actionable
                            if self._is_actionable_content(entry.title, summary):
                                item = InsightItem(
                                    title=entry.title,
                                    url=entry.link,
                                    summary=summary,
                                    source=source_name,
                                    pub_date=pub_date,
                                    quality_score=quality_multiplier,
                                    category=category
                                )

                                if self._passes_quality_filter(item):
                                    insights.append(item)

                    time.sleep(0.4)

                except Exception as e:
                    logger.warning(f"Error fetching {source_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching lifestyle sources: {e}")

        logger.info(f"Retrieved {len(insights)} lifestyle insights")
        return insights

    def _is_growth_related(self, title: str, summary: str) -> bool:
        """Check if content is related to personal growth and finance"""
        text = (title + " " + summary).lower()

        # Direct keyword matching
        for keyword in self.finance_keywords:
            if keyword.lower() in text:
                return True

        # Pattern matching for growth concepts
        growth_patterns = [
            r'\b(how to|ways to|tips for|guide to|steps to)\b',
            r'\b(save money|make money|build wealth|increase income)\b',
            r'\b(improve|better|optimize|maximize|minimize)\b',
            r'\b(budget|debt|credit|investment|retirement)\b',
            r'\b(productivity|efficiency|organization|planning)\b',
            r'\b(habit|routine|discipline|motivation)\b',
            r'\b(career|job|salary|promotion|skill)\b'
        ]

        for pattern in growth_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _is_actionable_content(self, title: str, summary: str) -> bool:
        """Check if content provides actionable advice"""
        text = (title + " " + summary).lower()

        actionable_indicators = [
            'how to', 'ways to', 'steps to', 'guide to', 'tips for',
            'you should', 'you can', 'try this', 'method', 'strategy',
            'technique', 'approach', 'system', 'framework', 'process'
        ]

        return any(indicator in text for indicator in actionable_indicators)

    def _passes_quality_filter(self, item: InsightItem) -> bool:
        """Enhanced quality filtering for insight items"""
        title_lower = item.title.lower()

        # Check for low-quality patterns
        for pattern in self.low_quality_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return False

        # Check for spam domains
        if self._is_spam_domain(item.url):
            return False

        # Minimum content requirements
        if len(item.title) < 15 or not item.url:
            return False

        # Filter out overly promotional content
        promotional_words = ['buy now', 'click here', 'limited time', 'special offer', 'discount code']
        if any(word in title_lower for word in promotional_words):
            return False

        return True

    def _is_spam_domain(self, url: str) -> bool:
        """Check if URL is from a spam domain"""
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r'^www\.', '', domain)
            return domain in self.spam_domains
        except Exception:
            return False

    def _extract_reddit_summary(self, post_data: Dict) -> str:
        """Extract comprehensive summary from Reddit posts"""
        selftext = post_data.get('selftext', '')

        # For self posts with substantial content
        if selftext and len(selftext) > 100:
            # Clean markdown formatting
            clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', selftext)
            clean_text = re.sub(r'[*_`]+', '', clean_text)
            clean_text = re.sub(r'\n+', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            # Extract key points if it's a long post
            if len(clean_text) > 800:
                sentences = clean_text.split('.')
                key_sentences = [s.strip() for s in sentences[:4] if len(s.strip()) > 20]
                return '. '.join(key_sentences) + '...' if key_sentences else clean_text[:400] + '...'

            return clean_text[:600] + '...' if len(clean_text) > 600 else clean_text

        # For link posts, use title as summary
        return post_data.get('title', '')[:300]

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        return text.strip()

    def generate_insights_summary(self, insights: List[InsightItem]) -> str:
        """Generate comprehensive insights summary with actionable advice"""
        logger.info("Generating insights summary with Gemini...")

        # Rank and prepare content
        ranked_insights = self._rank_insights(insights)
        content = self._prepare_content_for_summary(ranked_insights)

        # Enhanced prompt focused on actionable insights
        prompt = f"""
        You are a personal finance advisor and life coach. Create a comprehensive daily brief focusing on ACTIONABLE INSIGHTS and PRACTICAL STRATEGIES for personal and financial growth.

        Structure the brief in Markdown with EXACTLY these H2 sections:

        ## 💰 FINANCIAL MOVES & MONEY INSIGHTS
        - 8-12 unique financial tips and strategies, each as a paragraph including:
          - **<Clear, actionable headline>**. <Specific strategy or advice>. <Expected impact or benefit>. <Source> — <url>
        - Focus on: budgeting tips, investment strategies, debt reduction, income optimization, tax savings

        ## 🎯 CAREER & INCOME GROWTH
        - 6-8 career development insights and income optimization strategies
        - Each point should: provide specific action, explain the benefit, include implementation tips
        - Focus on: salary negotiation, skill development, networking, side hustles, career transitions

        ## 📈 WEALTH BUILDING STRATEGIES
        - 5-7 long-term wealth building concepts and strategies
        - For EACH strategy provide:
          - **Strategy Name**: Clear description of the approach
          - **Implementation**: Step-by-step how to start
          - **Timeline**: Expected timeframe for results
          - **Risk/Reward**: What to expect and potential downsides
        - Focus on: investment principles, asset building, passive income, retirement planning

        ## 🧠 PRODUCTIVITY & LIFE OPTIMIZATION
        - 6-9 practical life improvement tips and productivity hacks
        - For EACH tip provide:
          - **Life Hack**: What it is and why it works
          - **Implementation**: Specific steps to adopt it
          - **Time/Money Saved**: Quantified benefit when possible
          - **Personal Impact**: How it improves daily life
        - Focus on: time management, organization, health optimization, habit formation

        ## 🚀 ACTIONABLE CHALLENGES
        - 5-8 specific challenges or tasks readers can implement this week
        - Each challenge should be:
          - Specific and measurable
          - Achievable within 7 days
          - Directly beneficial to finances or life quality
          - Include expected outcome
        - Examples: "Track every expense for 7 days", "Negotiate one monthly bill", "Learn one new skill for 30 minutes daily"

        ## 💬 COMMUNITY WISDOM
        - 6-10 notable insights and discussions from the community
        - Each with: key insight or lesson learned (2-3 sentences) and <source> — <url>
        - Highlight: success stories, common mistakes to avoid, contrarian viewpoints

        CRITICAL REQUIREMENTS:
        - NO repetition across sections - each insight appears once in the most logical section
        - Every item must be ACTIONABLE - readers should know exactly what to do
        - Include specific numbers, percentages, timeframes, and dollar amounts when available
        - Include URLs only in Financial Moves and Community sections
        - Focus on practical implementation, not theory
        - Make insights accessible to beginners but valuable to advanced users

        INSIGHTS INPUT (ranked by quality and actionability):
        {content}
        """

        try:
            # Token counting and generation
            input_tokens = None
            try:
                ct = self.model.count_tokens(prompt)
                input_tokens = getattr(ct, 'total_tokens', None) or getattr(ct, 'token_count', None)
            except Exception:
                input_tokens = None

            response = self.model.generate_content(prompt)

            # Read usage metadata
            output_tokens = None
            total_tokens = None
            try:
                um = getattr(response, 'usage_metadata', None)
                if um:
                    output_tokens = getattr(um, 'output_token_count', None) or getattr(um, 'candidates_token_count', None)
                    if input_tokens is None:
                        input_tokens = getattr(um, 'input_token_count', None)
                    total_tokens = getattr(um, 'total_token_count', None)
            except Exception:
                pass

            if total_tokens is None and (input_tokens is not None or output_tokens is not None):
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
            return self._create_fallback_summary(ranked_insights)

    def _rank_insights(self, insights: List[InsightItem]) -> List[InsightItem]:
        """Rank insights by quality score and actionability"""
        # Calculate final scores
        for item in insights:
            base_score = item.quality_score
            engagement_boost = (item.score + item.comments * 1.5) / 300
            recency_boost = 0.2 if item.pub_date and (datetime.now() - item.pub_date).days <= 1 else 0

            # Boost for actionable content
            actionability_boost = 0
            title_lower = item.title.lower()
            if any(word in title_lower for word in ['how to', 'ways to', 'tips', 'guide', 'strategy']):
                actionability_boost += 0.3
            if any(word in title_lower for word in ['save money', 'make money', 'increase', 'improve', 'optimize']):
                actionability_boost += 0.2

            item.quality_score = base_score + engagement_boost + recency_boost + actionability_boost

        # Sort by quality score descending
        return sorted(insights, key=lambda x: x.quality_score, reverse=True)

    def _prepare_content_for_summary(self, insights: List[InsightItem]) -> str:
        """Prepare ranked insights for AI summarization"""
        # De-duplicate insights
        insights = self._dedupe_insights(insights)
        content = ""

        # Group by category for better organization
        categories = {}
        for item in insights[:100]:  # Top 100 insights
            category = item.category or 'General'
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        # Priority order for categories
        priority_order = [
            'Personal Finance', 'Wealth Building', 'Investing', 'Career',
            'Life Skills', 'Productivity', 'Personal Development', 'Money Saving',
            'Side Income', 'Health', 'Lifestyle', 'General'
        ]

        # Output in priority order
        for category in priority_order:
            if category in categories and categories[category]:
                content += f"\n--- {category.upper()} ---\n"
                for item in categories[category][:12]:  # Limit items per category
                    content += f"Title: {item.title}\n"
                    if item.flair:
                        content += f"Flair: {item.flair}\n"
                    if item.summary and len(item.summary) > 50:
                        content += f"Summary: {item.summary[:500]}...\n"
                    content += f"Source: {item.source}"
                    if item.score > 0:
                        content += f" (Score: {item.score}, Comments: {item.comments})"
                    content += f"\nURL: {item.url}\n\n"

        return content[:15000]  # Increased limit for comprehensive content

    def _dedupe_insights(self, insights: List[InsightItem]) -> List[InsightItem]:
        """Remove duplicate insights with improved similarity detection"""
        def normalize_title(title: str) -> str:
            t = title.lower()
            t = re.sub(r"[^a-z0-9\s]", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            # Remove common words
            stop_words = ['lpt', 'ysk', 'tip', 'how', 'to', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'of', 'with', 'by']
            words = [w for w in t.split() if w not in stop_words and len(w) > 2]
            return " ".join(words)

        seen_titles = set()
        seen_urls = set()
        unique_insights = []

        for item in insights:
            title_key = normalize_title(item.title)
            url_key = item.url.lower()

            # Skip if we've seen very similar title or exact URL
            title_similar = any(
                len(set(title_key.split()) & set(seen.split())) > max(len(title_key.split()) * 0.7, 2)
                for seen in seen_titles
            )

            if not title_similar and url_key not in seen_urls and len(title_key.split()) >= 2:
                seen_titles.add(title_key)
                seen_urls.add(url_key)
                unique_insights.append(item)

        return unique_insights

    def _postprocess_summary(self, markdown_text: str) -> str:
        """Enhanced postprocessing with structure enforcement"""
        allowed = [
            "FINANCIAL MOVES & MONEY INSIGHTS",
            "CAREER & INCOME GROWTH",
            "WEALTH BUILDING STRATEGIES",
            "PRODUCTIVITY & LIFE OPTIMIZATION",
            "ACTIONABLE CHALLENGES",
            "COMMUNITY WISDOM",
        ]

        lines = markdown_text.splitlines()
        sections: Dict[str, List[str]] = {name: [] for name in allowed}
        current: Optional[str] = None

        header_re = re.compile(r"^##\s+[💰🎯📈🧠🚀💬]?\s*(.*)$")

        for ln in lines:
            m = header_re.match(ln.strip())
            if m:
                title = m.group(1).strip().upper()
                # Flexible matching for section headers
                for name in allowed:
                    key_words = name.split()[:2]  # First two words
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
            "FINANCIAL MOVES & MONEY INSIGHTS": "💰",
            "CAREER & INCOME GROWTH": "🎯",
            "WEALTH BUILDING STRATEGIES": "📈",
            "PRODUCTIVITY & LIFE OPTIMIZATION": "🧠",
            "ACTIONABLE CHALLENGES": "🚀",
            "COMMUNITY WISDOM": "💬"
        }

        # Generate header with current date
        output = [f"# 📊 Personal Growth & Finance Insights - {datetime.now().strftime('%Y-%m-%d')}\n"]

        # Build final output with proper sections
        for section_name in allowed:
            content_lines = [line for line in sections[section_name] if line.strip()]
            if content_lines:
                output.append(f"## {emoji_map[section_name]} {section_name}")
                output.extend(content_lines)
                output.append("")

        return "\n".join(output).strip()

    def _create_fallback_summary(self, insights: List[InsightItem]) -> str:
        """Enhanced fallback summary with better structure"""
        summary = f"# 📊 Personal Growth & Finance Insights - {datetime.now().strftime('%Y-%m-%d')}\n\n"

        # Group by category
        categories = {}
        for item in insights[:60]:  # Top 60 items
            category = item.category or "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        # Priority categories for fallback
        priority_categories = [
            "Personal Finance", "Wealth Building", "Career", "Investing",
            "Life Skills", "Productivity", "Personal Development", "Money Saving"
        ]

        for category in priority_categories:
            if category in categories and categories[category]:
                summary += f"## {category}\n"
                for item in categories[category][:8]:  # Top 8 per category
                    summary += f"- **{item.title}**\n"
                    if item.summary:
                        summary += f"  {item.summary[:300]}...\n"
                    summary += f"  [{item.source}]({item.url})\n"
                    if item.score > 0:
                        summary += f"  Score: {item.score}, Comments: {item.comments}\n"
                    summary += "\n"

        return summary

    def _get_gmail_credentials(self) -> Credentials:
        """Load or fetch Gmail API OAuth2 credentials"""
        scopes = [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
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
                logger.error(f"Failed to refresh Gmail credentials from GMAIL_REFRESH_TOKEN: {e}")

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Build client config inline from Client ID/Secret
                client_id = env_client_id or self.config.get("gmail_client_id")
                client_secret = env_client_secret or self.config.get("gmail_client_secret")
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
                auth_mode = (self.config.get("gmail_auth_mode") or "localserver").lower()
                if auth_mode == "console":
                    logger.warning("GMAIL_AUTH_MODE=console is deprecated; using localserver with open_browser=False")
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
        """Send email with the daily insights summary using Gmail API"""
        logger.info("Sending insights email via Gmail API...")

        try:
            recipient = (self.config.get('recipient_email') or '').strip()
            if not recipient:
                logger.warning("Skipping email: recipient_email not configured.")
                return

            # Build Gmail service
            creds = self._get_gmail_credentials()
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)

            # Build MIME message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 Personal Growth & Finance Insights - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.config.get('smtp_username') or self.config.get('sender_email') or "me"
            msg['To'] = recipient

            html_content = self._convert_to_html(summary)
            text_part = MIMEText(summary, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)

            # Encode and send message
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            body = {"raw": raw}

            # Send with retry logic
            attempts = 0
            while True:
                try:
                    service.users().messages().send(userId="me", body=body).execute()
                    logger.info("Insights email sent successfully via Gmail API!")
                    break
                except Exception as send_err:
                    attempts += 1
                    if attempts >= 3:
                        raise send_err
                    sleep_for = 2 ** attempts
                    logger.warning(f"Send failed (attempt {attempts}), retrying in {sleep_for}s...")
                    time.sleep(sleep_for)

        except Exception as e:
            logger.error(f"Error sending insights email via Gmail API: {e}")

    def _convert_to_html(self, summary: str) -> str:
        """Convert Markdown to HTML with enhanced styling for insights"""
        # Render Markdown to HTML
        body_html = md_to_html(
            summary,
            extensions=[
                'extra',
                'sane_lists',
                'nl2br',
                'codehilite',
            ],
            output_format='html5',
        )

        # Sanitize HTML
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union({
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'pre', 'code', 'blockquote', 'hr', 'br',
            'ul', 'ol', 'li', 'strong', 'em', 'table',
            'thead', 'tbody', 'tr', 'th', 'td', 'div'
        })
        allowed_attrs = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
            'div': ['style', 'class'],
            'span': ['style', 'class'],
            'p': ['style'],
            'h1': ['style'], 'h2': ['style'], 'h3': ['style']
        }

        # Configure CSS sanitizer to allow a safe subset of inline styles
        css_sanitizer = CSSSanitizer(
            allowed_css_properties={
                'color','background','background-color','padding','margin','border','border-color','border-style','border-width',
                'font-size','font-weight','text-decoration','display','gap','align-items','vertical-align','line-height',
                'border-radius','box-shadow','width','height'
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

        # Enhanced styling for personal growth content
        logo_html = (
            f'<img src="{self.brand_logo_url}" alt="Logo" width="32" height="32" '
            f'style="display:inline-block;border-radius:8px;margin-right:12px;vertical-align:middle;" />'
            if self.brand_logo_url else '📊'
        )

        template = f"""
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Personal Growth & Finance Insights</title>
          </head>
          <body style="margin:0;padding:0;background:#f7fafc;font-family:'Segoe UI',Arial,sans-serif;">
            <div style="max-width:900px;margin:0 auto;background:#ffffff;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
              <!-- Header -->
              <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:32px 24px;text-align:center;">
                <div style="display:inline-flex;align-items:center;gap:12px;">
                  {logo_html}
                  <div>
                    <h1 style="margin:0 0 8px 0;font-size:28px;font-weight:700;">Personal Growth & Finance Insights</h1>
                    <div style="font-size:16px;opacity:0.9;">{datetime.now().strftime('%B %d, %Y')}</div>
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
                  /* Special styling for insight sections */
                  .insight-section {{
                    background:#f8fafc;
                    padding:16px;
                    border-left:4px solid #3b82f6;
                    margin:16px 0;
                    border-radius:8px;
                  }}
                </style>
                {sanitized}
              </div>

              <!-- Footer -->
              <div style="background:#f8fafc;padding:24px;text-align:center;border-top:1px solid #e2e8f0;">
                <p style="margin:0;color:#64748b;font-size:14px;">
                  🚀 Generated by Personal Growth & Finance Insights Aggregator<br>
                  <small>Sources: Reddit Communities, Finance Blogs, Productivity Resources</small>
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        return template

    def run_daily_insights(self):
        """Run the complete daily insights aggregation process"""
        logger.info("Starting personal growth & finance insights aggregation...")

        try:
            # Collect insights from all sources
            all_insights = []

            # Core sources
            all_insights.extend(self.fetch_reddit_insights())
            all_insights.extend(self.fetch_finance_blogs())
            all_insights.extend(self.fetch_lifestyle_sources())

            logger.info(f"Total insights collected: {len(all_insights)}")

            # Rank by quality and relevance
            ranked_insights = self._rank_insights(all_insights)
            logger.info(f"Top insights after ranking: {len(ranked_insights[:100])}")

            # Generate comprehensive insights summary
            summary = self.generate_insights_summary(ranked_insights)

            # Send email
            self.send_email(summary)

            # Optional: Save summary to file
            summary_file = f"insights_summary_{datetime.now().strftime('%Y%m%d')}.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"Insights summary saved to {summary_file}")

            logger.info("Personal growth & finance insights aggregation completed successfully!")

        except Exception as e:
            logger.error(f"Error in insights aggregation process: {e}")
            raise

def main():
    """Main execution function"""

    # Enhanced configuration for personal growth aggregator
    config = {
        # Gmail API OAuth
        'gmail_client_id': os.getenv('GMAIL_CLIENT_ID'),
        'gmail_client_secret': os.getenv('GMAIL_CLIENT_SECRET'),
        'gmail_token_path': os.getenv('GMAIL_TOKEN_FILE', 'token.json'),
        'gmail_auth_mode': os.getenv('GMAIL_AUTH_MODE', 'localserver'),

        # Email settings
        'smtp_username': os.getenv('SMTP_USERNAME', ''),
        'sender_email': os.getenv('SENDER_EMAIL', ''),
        'recipient_email': os.getenv('RECIPIENT_EMAIL', 'kartikpatel0170@gmail.com'),

        # API keys
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
    }

    # Validate required configuration
    required_fields = ['gmail_client_id', 'gmail_client_secret', 'gemini_api_key']
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        logger.error(f"Missing required configuration: {missing_fields}")
        logger.error("Please set the following environment variables:")
        for field in missing_fields:
            logger.error(f"  {field.upper()}")
        return

    # Create and run aggregator
    try:
        aggregator = PersonalGrowthAggregator(config)
        aggregator.run_daily_insights()
    except Exception as e:
        logger.error(f"Failed to run personal growth aggregator: {e}")
        raise

if __name__ == "__main__":
    main()