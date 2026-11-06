from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post


class ProjectDraftTest(TestCase):
    def setUp(self):
        self.user = create_approved_user("project-author")
        login(self.client, self.user)
        self.data = {
            "title": "My project",
            "text": "Short project description",
            "url": "https://example.com/project",
            "is_public": "True",
        }

    @patch("common.forms.upload_image_multipart", return_value="https://example.com/project.png")
    def test_short_project_can_be_saved_and_previewed_as_draft(self, upload):
        for action in ["", "preview"]:
            with self.subTest(action=action):
                data = {
                    **self.data,
                    "action": action,
                    "title": f"Project {action or 'save'}",
                    "image": SimpleUploadedFile("project.png", b"image"),
                }
                response = self.client.post(reverse("compose_type", args=[Post.TYPE_PROJECT]), data)
                self.assertEqual(response.status_code, 302)
                post = Post.objects.get(author=self.user, title=data["title"])
                self.assertEqual(post.visibility, Post.VISIBILITY_DRAFT)
                self.assertEqual(post.text, self.data["text"])

    @patch("posts.views.posts.async_task")
    def test_publication_requires_minimum_length(self, enqueue):
        post = Post.objects.create(
            author=self.user, type=Post.TYPE_PROJECT, image="https://example.com/project.png", **self.data,
        )
        url = reverse("edit_post", args=[post.slug])
        response = self.client.post(url, {**self.data, "action": "publish"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text", response.context["form"].errors)
        post.refresh_from_db()
        self.assertEqual(post.visibility, Post.VISIBILITY_DRAFT)
        enqueue.assert_not_called()

        response = self.client.post(url, {**self.data, "text": "x" * 1500, "action": "publish"})
        self.assertEqual(response.status_code, 302)
        post.refresh_from_db()
        self.assertEqual(post.visibility, Post.VISIBILITY_LINK_ONLY)
        self.assertEqual(post.text, "x" * 1500)

    def test_published_project_cannot_be_shortened_below_minimum(self):
        post = Post.objects.create(
            author=self.user, type=Post.TYPE_PROJECT, image="https://example.com/project.png",
            **{**self.data, "text": "x" * 1500}, visibility=Post.VISIBILITY_EVERYWHERE,
        )
        response = self.client.post(reverse("edit_post", args=[post.slug]), self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text", response.context["form"].errors)
        post.refresh_from_db()
        self.assertEqual(post.text, "x" * 1500)
