import json
import urllib.request
import urllib.error
import ssl
import re
from datetime import datetime, timezone
from html import unescape

from django.core.management import BaseCommand
from users.models.user import User
from posts.models.post import Post

WEEKLY_DIGEST_URL = 'https://news.pmi.moscow/FeedPost/GetWeeklyDigest'

def get_news_weekly_digest():
    """
    Fetches weekly digest JSON from WEEKLY_DIGEST_URL using urllib.
    
    Returns:
        dict: Parsed JSON data from the weekly digest URL
        
    Raises:
        urllib.error.URLError: If there's an error fetching the URL
        json.JSONDecodeError: If the response is not valid JSON
    """
    try:
        # Create SSL context to handle certificate issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create a request object
        req = urllib.request.Request(WEEKLY_DIGEST_URL)
        
        # Make the request with SSL context
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            json_data = json.loads(data.decode(encoding))
            return json_data
    except urllib.error.URLError as e:
        raise
    except json.JSONDecodeError as e:
        raise

def clean_html(text):
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = unescape(text)
    # Clean up multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_moderator_user():
    """
    Finds and returns a user with full_name="moderator".
    
    Returns:
        User: The moderator user
        
    Raises:
        User.DoesNotExist: If no user with name="moderator" is found
        User.MultipleObjectsReturned: If multiple users with name="moderator" are found
    """
    return User.objects.get(slug="moderator")

def get_digest_post() -> str:
    """
    Fetches weekly digest data and creates formatted markdown content.
    Adapted from create_digest_article function.
    
    Returns:
        str: Formatted markdown content of the digest post
        
    Raises:
        urllib.error.URLError: If there's an error fetching the URL
        json.JSONDecodeError: If the response is not valid JSON
        KeyError: If required fields are missing from the response
    """
    data = get_news_weekly_digest()
    
    if not data or not isinstance(data, list):
        return None
    
    article_parts = []
    article_parts.append("Привет, Олимпийский! Ниже подборка актуальных постов из мира менеджмента")
    article_parts.append("")  # Empty line for spacing
    article_parts.append("---")
    article_parts.append("")
    
    # Process each feed
    for feed_data in data:
        feed = feed_data.get('feed', {})
        feed_title = feed.get('title', 'Без названия')
        feed_description = feed.get('description', '')
        # last_sync = feed_data.get('lastSyncDate', '')
        posts = feed_data.get('posts', [])
        
        article_parts.append(f"## {feed_title}")
        if feed_description:
            article_parts.append(f"*{feed_description}*")
        article_parts.append("")
        
        if posts:
            for idx, post in enumerate(posts, 1):
                post_text = post.get('postText', '')
                post_image = post.get('postImage', '')
                post_url = post.get('postUrl', '')
                post_date = post.get('postDate', '')

                date_str = ""
                if post_date:
                    try:
                        dt = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                        date_str = dt.strftime('%d.%m.%Y')
                    except:
                        date_str = post_date    
                
                if post_text:
                    cleaned_text = clean_html(post_text)
                    if cleaned_text:
                        # Truncate if too long
                        if len(cleaned_text) > 500:
                            cleaned_text = cleaned_text[:500] + "..."
                        article_parts.append(f"###  {date_str} Пост {idx}")
                        
                        # Add image if exists
                        if post_image and post_image.strip():
                            article_parts.append(f"![]({post_image})")
                            article_parts.append("")
                        
                        article_parts.append(f"{cleaned_text}")
                        article_parts.append("")
                        
                        # Add link to original post if exists
                        if post_url and post_url.strip():
                            article_parts.append(f"[🔗 Читать оригинал]({post_url})")
                            article_parts.append("")
        else:
            article_parts.append("*Нет новых постов*")
            article_parts.append("")
        
        article_parts.append("---")
        article_parts.append("")
    
    return "\n".join(article_parts)

class Command(BaseCommand):
    help = "Creates weekly digest post from PMPulse"

    def handle(self, *args, **options):
        try:
            moderator = get_moderator_user()
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("Moderator user not found. Post creation cancelled."))
            return
        except User.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR("Multiple moderator users found. Post creation cancelled."))
            return
        
        try:            
            # Format current date as DD.MM.YYYY
            current_date = datetime.now(timezone.utc).strftime("%d.%m.%Y")
            title = f"📰 {current_date} Подборка постов известных авторов"

            content = get_digest_post()

            post = Post.objects.create(
                author=moderator,
                title=title,
                text=content,
                type=Post.TYPE_POST,
                is_visible=False,
                is_approved_by_moderator=False,
            )
            
            self.stdout.write(self.style.SUCCESS(f"Created post '{post.title}' with slug '{post.slug}' (awaiting moderation)"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating post: {e}"))
            raise