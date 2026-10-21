from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from comments.models import Comment, CommentVote
from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post


class TestCommentApiResources(TestCase):
    def setUp(self):
        self.author = create_approved_user("comment_resource_author")
        self.voter = create_approved_user("comment_resource_voter")
        self.post = Post.objects.create(
            slug="comment-resource-post", type=Post.TYPE_POST, author=self.author,
            title="Comment resource post", visibility=Post.VISIBILITY_EVERYWHERE,
        )
        self.comment = Comment.objects.create(author=self.author, post=self.post, text="Comment")
        login(self.client, self.voter)
        self.vote_url = reverse("toggle_comment_vote", args=[self.comment.id])

    def test_comment_vote_create_and_delete_are_idempotent(self):
        self.assertEqual(self.vote_url, f"/comment/{self.comment.id}/votes.json")
        response = self.client.get(self.vote_url)

        self.assertFalse(response.json()["is_voted"])
        self.assertFalse(CommentVote.objects.exists())

        for method, count in [(self.client.post, 1), (self.client.delete, 0)]:
            for attempt in range(2):
                response = method(self.vote_url)
                self.comment.refresh_from_db()
                self.author.refresh_from_db()

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["is_voted"], bool(count))
                self.assertEqual(self.comment.upvotes, count)
                self.assertEqual(self.author.upvotes, count)
                self.assertEqual(CommentVote.objects.count(), count)

    def test_expired_comment_vote_cannot_be_retracted(self):
        self.client.post(self.vote_url)
        CommentVote.objects.update(
            created_at=datetime.utcnow() - settings.RETRACT_VOTE_TIMEDELTA - timedelta(seconds=1),
        )

        response = self.client.delete(self.vote_url)

        self.assertTrue(response.json()["is_voted"])
        self.assertEqual(response.json()["comment"]["upvotes"], 1)
        self.assertEqual(CommentVote.objects.count(), 1)

    def test_thread_deletion_requires_moderator_and_keeps_normal_redirect(self):
        url = reverse("delete_comment_thread", args=[self.comment.id])
        reply = Comment.objects.create(author=self.voter, post=self.post, text="Reply", reply_to=self.comment)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Comment.objects.filter(id=self.comment.id).exists())
        self.assertTrue(Comment.objects.filter(id=reply.id).exists())
        self.voter.roles = ["moderator"]
        self.voter.save()
        login(self.client, self.voter)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("show_post", args=[self.post.type, self.post.slug]))
        self.assertFalse(Comment.objects.filter(id__in=[self.comment.id, reply.id]).exists())
