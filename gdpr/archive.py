import json
import os
import random
import shutil
import tempfile
from datetime import datetime

from django.conf import settings
from django_q.tasks import schedule

from badges.models import UserBadge
from bookmarks.models import PostBookmark
from comments.models import Comment
from gdpr.serializers import post_to_json, post_to_md, user_to_json, comments_to_json, user_tags_to_json, \
    comment_to_md, comment_to_json, bookmarks_to_json, upvotes_to_json, badges_to_json, \
    achievements_to_json
from notifications.email.users import send_data_archive_ready_email
from posts.models.post import Post
from posts.models.votes import PostVote
from users.models.achievements import UserAchievement
from tags.models import UserTag


def generate_data_archive(user, save_path=settings.GDPR_ARCHIVE_STORAGE_PATH):
    with tempfile.TemporaryDirectory() as tmp_dir:
        user_dir = os.path.join(tmp_dir, user.slug)
        os.makedirs(user_dir)

        # dump data
        dump_user_profile(user_dir, user)
        dump_user_posts(user_dir, user)
        dump_user_comments(user_dir, user)
        dump_user_bookmarks(user_dir, user)
        dump_user_upvotes(user_dir, user)
        dump_user_badges(user_dir, user)
        dump_user_achievements(user_dir, user)

        # save zip archive
        archive_name = f"{user.slug}-{datetime.utcnow().strftime('%Y-%m-%d-%H-%M')}-{random.randint(1000000, 9999998)}"
        archive_path = shutil.make_archive(os.path.join(save_path, archive_name), "zip", tmp_dir)

        # schedule a task to remove archive after timeout
        schedule(
            "gdpr.archive.delete_data_archive",
            archive_path,
            next_run=datetime.utcnow() + settings.GDPR_ARCHIVE_DELETE_TIMEDELTA
        )

        # notify the user
        send_data_archive_ready_email(
            user=user,
            url=settings.GDPR_ARCHIVE_URL + os.path.basename(archive_path),
        )


def delete_data_archive(archive_path):
    os.remove(archive_path)


def dump_user_profile(user_dir, user):
    with open(os.path.join(user_dir, "profile.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(user_to_json(user), ensure_ascii=False))

    user_tags = UserTag.objects.filter(user=user)
    with open(os.path.join(user_dir, "tags.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(user_tags_to_json(user_tags), ensure_ascii=False))


def dump_user_posts(user_dir, user):
    posts = Post.objects.filter(author=user).select_related("author", "room")

    for post in posts:
        post_dir = os.path.join(user_dir, f"posts/{post.slug}")
        os.makedirs(post_dir)

        with open(os.path.join(post_dir, f"{post.slug}.md"), "w", encoding="utf-8") as f:
            f.write(post_to_md(post))

        with open(os.path.join(post_dir, f"{post.slug}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(post_to_json(post), ensure_ascii=False))

        # dump post comments
        post_comments = Comment.objects.filter(post=post).select_related("author", "post")
        with open(os.path.join(post_dir, f"comments.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(comments_to_json(post_comments), ensure_ascii=False))


def dump_user_comments(user_dir, user):
    comments = Comment.objects.filter(author=user).select_related("author", "post")

    for comment in comments:
        comment_dir = os.path.join(user_dir, f"comments/{comment.id}")
        os.makedirs(comment_dir)

        with open(os.path.join(comment_dir, f"{comment.id}.md"), "w", encoding="utf-8") as f:
            f.write(comment_to_md(comment))

        with open(os.path.join(comment_dir, f"{comment.id}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(comment_to_json(comment), ensure_ascii=False))

        # dump replies
        comment_replies = Comment.objects.filter(reply_to=comment).select_related("author", "post")
        with open(os.path.join(comment_dir, f"replies.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(comments_to_json(comment_replies), ensure_ascii=False))


def dump_user_bookmarks(user_dir, user):
    bookmarks = PostBookmark.objects.filter(user=user).select_related("post")

    with open(os.path.join(user_dir, "bookmarks.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(bookmarks_to_json(bookmarks), ensure_ascii=False))


def dump_user_upvotes(user_dir, user):
    upvotes = PostVote.objects.filter(user=user).select_related("post")

    with open(os.path.join(user_dir, "upvotes.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(upvotes_to_json(upvotes), ensure_ascii=False))


def dump_user_badges(user_dir, user):
    badges = UserBadge.objects.filter(to_user=user).select_related("badge", "from_user")

    with open(os.path.join(user_dir, "badges.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(badges_to_json(badges), ensure_ascii=False))


def dump_user_achievements(user_dir, user):
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement")

    with open(os.path.join(user_dir, "achievements.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(achievements_to_json(achievements), ensure_ascii=False))
