import logging

import tweepy

from club import settings
from posts.models.post import Post

log = logging.getLogger()

auth = tweepy.OAuth1UserHandler(
    consumer_key=settings.TWITTER_CONSUMER_KEY,
    consumer_secret=settings.TWITTER_SECRET_KEY,
    access_token=settings.TWITTER_ACCESS_TOKEN,
    access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET
)
twitter = tweepy.API(auth)


def send_to_twitter(post: Post):
    if post.type == Post.TYPE_INTRO:
        log.info(f"Twitter skipping post with type: {post.type}")
        return

    url = settings.APP_HOST + post.get_absolute_url()
    title = post.title
    text = f"{title} {url}"

    log.info(f"Twitter sending tweet with text: {text}")
    twitter.update_status(status = text)
