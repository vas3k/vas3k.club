from datetime import datetime, timedelta

from django.test import TestCase

from comments.models import Comment, CommentVote
from posts.models.post import Post
from posts.models.votes import PostVote
from posts.models.views import PostView
from users.models.user import User


class ModelCreator:
    _exist_posts = 0
    _exist_users = 0
    _exist_comments = 0

    def create_user(self):
        self._exist_users += 1
        return User.objects.create(
            email="testuser_{}@test.com".format(self._exist_users),
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="testslug_{}".format(self._exist_users),
        )

    def create_post(self, **kwargs):
        self._exist_posts += 1
        if "author" not in kwargs:
            kwargs["author"] = self.create_user()
        return Post.objects.create(
            type=Post.TYPE_POST,
            slug="test_ofu_{}".format(self._exist_posts),
            title="title_ofu_{}".format(self._exist_posts),
            visibility=Post.VISIBILITY_EVERYWHERE,
            **kwargs,
        )

    def create_comment(self, post, author=None, **kwargs):
        self._exist_comments += 1
        if author is None:
            author = self.create_user()
        return Comment.objects.create(
            post=post,
            author=author,
            text="comment text {}".format(self._exist_comments),
            **kwargs,
        )


class TestPostObjectsForUser(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.post = self.creator.create_post()

    def test_upvoted_at_is_epoch_ms_for_voted_post(self):
        vote = PostVote.objects.create(user=self.user, post=self.post)

        post = Post.objects_for_user(self.user).get(id=self.post.id)

        expected_ms = round(vote.created_at.timestamp() * 1000)
        self.assertIsNotNone(post.upvoted_at)
        self.assertAlmostEqual(post.upvoted_at, expected_ms, delta=1000)

    def test_upvoted_at_none_for_unvoted_post(self):
        post = Post.objects_for_user(self.user).get(id=self.post.id)

        self.assertIsNone(post.upvoted_at)

    def test_unread_comments(self):
        PostView.objects.create(user=self.user, post=self.post, unread_comments=5)

        post = Post.objects_for_user(self.user).get(id=self.post.id)

        self.assertEqual(post.unread_comments, 5)

    def test_unread_comments_none_without_view(self):
        post = Post.objects_for_user(self.user).get(id=self.post.id)

        self.assertIsNone(post.unread_comments)

    def test_returns_visible_objects_for_none_user(self):
        qs = Post.objects_for_user(None)
        self.assertTrue(qs.filter(id=self.post.id).exists())

    def test_executes_in_single_query(self):
        PostVote.objects.create(user=self.user, post=self.post)
        PostView.objects.create(user=self.user, post=self.post, unread_comments=3)

        with self.assertNumQueries(1):
            list(Post.objects_for_user(self.user).filter(id=self.post.id))


class TestCommentObjectsForUser(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.post = self.creator.create_post()
        self.comment = self.creator.create_comment(post=self.post)

    def test_upvoted_at_is_epoch_ms_for_voted_comment(self):
        vote = CommentVote.objects.create(
            user=self.user, comment=self.comment, post=self.post
        )

        comment = Comment.objects_for_user(self.user).get(id=self.comment.id)

        expected_ms = round(vote.created_at.timestamp() * 1000)
        self.assertIsNotNone(comment.upvoted_at)
        self.assertAlmostEqual(comment.upvoted_at, expected_ms, delta=1000)

    def test_upvoted_at_none_for_unvoted_comment(self):
        comment = Comment.objects_for_user(self.user).get(id=self.comment.id)

        self.assertIsNone(comment.upvoted_at)

    def test_executes_in_single_query(self):
        CommentVote.objects.create(
            user=self.user, comment=self.comment, post=self.post
        )

        with self.assertNumQueries(1):
            list(Comment.objects_for_user(self.user).filter(id=self.comment.id))
