import json
import urllib.request
import urllib.error
from datetime import datetime

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
        with urllib.request.urlopen(WEEKLY_DIGEST_URL) as response:
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            json_data = json.loads(data.decode(encoding))
            return json_data
    except urllib.error.URLError as e:
        raise
    except json.JSONDecodeError as e:
        raise

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
    Fetches weekly digest data and extracts title and content.
    
    Returns:
        str: Formatted markdown content of the digest post
        
    Raises:
        urllib.error.URLError: If there's an error fetching the URL
        json.JSONDecodeError: If the response is not valid JSON
        KeyError: If required fields are missing from the response
    """
    data = get_news_weekly_digest()
    
    content_parts = ["Привет, Олимпийский! Ниже подборка актуальных постов тренеров и руководителей проектов за прошедшую неделю"]
    content_parts.append("")  # Empty line for spacing
    
    # Process each feed
    for feed_data in data:
        feed = feed_data.get("feed", {})
        feed_title = feed.get("title", "")
        posts = feed_data.get("posts", [])
        
        if not feed_title or not posts:
            continue
        
        # Add feed title as heading
        content_parts.append(f"## {feed_title}")
        content_parts.append("")
        
        # Process each post in the feed
        for post in posts:
            post_text = post.get("postText", "")
            post_url = post.get("postUrl", "")
            post_image = post.get("postImage", "")
            post_date = post.get("postDate", "")
            
            # Add post link
            if post_url:
                content_parts.append(f"[Читать пост]({post_url})")
            
            # Add post image if available
            if post_image:
                content_parts.append(f"![Post image]({post_image})")
            
            # Add post text (HTML content - could be converted to markdown if needed)
            if post_text:
                content_parts.append("")
                content_parts.append(post_text)
            
            # Add post date if available
            if post_date:
                content_parts.append("")
                content_parts.append(f"*Дата: {post_date}*")
            
            content_parts.append("")  # Empty line between posts
            content_parts.append("---")  # Separator between posts
            content_parts.append("")
    
    return "\n".join(content_parts)

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
            current_date = datetime.utcnow().strftime("%d.%m.%Y")
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