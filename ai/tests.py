import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from openai.types.responses import ResponseFunctionToolCall

from ai.assistant import ask_assistant
from ai.tools import (
    read_post, read_discussion, search_users, generic_search, search_chats,
    read_comment, search_post_comments, search_room_posts, read_club_guide, club_rules_and_info,
    TOOLS_MAP, TOOLS_DESCRIPTION, parse_tool_arguments,
)
from comments.models import Comment
from posts.models.post import Post
from rooms.models import Room
from search.models import SearchIndex
from users.models.user import User


class AssistantToolTests(SimpleTestCase):
    def test_search_can_be_followed_by_reading(self):
        search = ResponseFunctionToolCall(
            type="function_call", name="search_posts", call_id="search",
            arguments='{"query":"test","post_type":null,"order_by":null}',
        )
        read = ResponseFunctionToolCall(
            type="function_call", name="read_post", arguments='{"slug":"test","offset":null}', call_id="read",
        )
        responses = [
            SimpleNamespace(status="completed", output=[search], output_text=""),
            SimpleNamespace(status="completed", output=[read], output_text=""),
            SimpleNamespace(status="completed", output=[], output_text="answer"),
        ]
        search_tool = Mock(return_value=[{"slug": "test"}])
        read_tool = Mock(return_value={"text_markdown": "body"})

        with patch("ai.assistant.create_response", side_effect=responses) as api, patch.dict(
            "ai.assistant.TOOLS_MAP", {"search_posts": search_tool, "read_post": read_tool},
        ):
            self.assertEqual(ask_assistant("question", reply_to_text="quote"), "answer")

        search_tool.assert_called_once_with(query="test", post_type=None, order_by=None)
        read_tool.assert_called_once_with(slug="test", offset=None)
        messages = api.call_args.kwargs["input"]
        self.assertIn(search, messages)
        self.assertIn(read, messages)
        self.assertEqual(json.loads(messages[-1]["output"])["text_markdown"], "body")

    def test_tool_budget_stops_search_and_answers(self):
        calls = [ResponseFunctionToolCall(
            type="function_call", name="search_posts", call_id=str(index),
            arguments=json.dumps({"query": str(index), "post_type": None, "order_by": None}),
        ) for index in range(12)]
        tool = Mock(return_value=[])

        with patch("ai.assistant.create_response", side_effect=[
            SimpleNamespace(status="completed", output=calls, output_text=""),
            SimpleNamespace(status="completed", output=[], output_text="answer"),
        ]) as api, patch.dict("ai.assistant.TOOLS_MAP", {"search_posts": tool}):
            self.assertEqual(ask_assistant("question"), "answer")

        self.assertEqual(tool.call_count, 8)
        self.assertEqual(api.call_args.kwargs["tool_choice"], "none")
        outputs = [
            item for item in api.call_args.kwargs["input"]
            if isinstance(item, dict) and item.get("type") == "function_call_output"
        ]
        self.assertEqual(len(outputs), 12)
        self.assertIn("error", json.loads(outputs[-1]["output"]))

    def test_tool_failure_is_reported_to_model(self):
        call = ResponseFunctionToolCall(
            type="function_call", name="read_post", arguments='{"slug":"test","offset":null}', call_id="read",
        )

        with patch("ai.assistant.create_response", side_effect=[
            SimpleNamespace(status="completed", output=[call], output_text=""),
            SimpleNamespace(status="completed", output=[], output_text="answer"),
        ]) as api, patch.dict("ai.assistant.TOOLS_MAP", {"read_post": Mock(side_effect=ValueError)}):
            self.assertEqual(ask_assistant("question"), "answer")

        self.assertIn("error", json.loads(api.call_args.kwargs["input"][-1]["output"]))

    def test_five_requests_then_final_answer_without_tools(self):
        responses = [SimpleNamespace(status="completed", output=[ResponseFunctionToolCall(
            type="function_call", name="search_chats", arguments=json.dumps({"query": str(index)}),
            call_id=str(index),
        )], output_text="") for index in range(4)]
        responses.append(SimpleNamespace(status="completed", output=[], output_text="answer"))

        with patch("ai.assistant.create_response", side_effect=responses) as api, patch.dict(
            "ai.assistant.TOOLS_MAP", {"search_chats": Mock(return_value=[])},
        ):
            self.assertEqual(ask_assistant("question"), "answer")

        self.assertEqual(api.call_count, 5)
        self.assertEqual(api.call_args.kwargs["tool_choice"], "none")
        self.assertTrue(all(call.kwargs["max_retries"] == 0 for call in api.call_args_list))

    def test_repeated_call_does_not_query_database_again(self):
        calls = [ResponseFunctionToolCall(
            type="function_call", name="search_chats", arguments='{"query":"Berlin"}', call_id=str(index),
        ) for index in range(2)]
        tool = Mock(return_value=[])

        with patch("ai.assistant.create_response", side_effect=[
            SimpleNamespace(status="completed", output=[calls[0]], output_text=""),
            SimpleNamespace(status="completed", output=[calls[1]], output_text=""),
            SimpleNamespace(status="completed", output=[], output_text="answer"),
        ]) as api, patch.dict("ai.assistant.TOOLS_MAP", {"search_chats": tool}):
            ask_assistant("question")

        tool.assert_called_once_with(query="Berlin")
        self.assertIn("error", json.loads(api.call_args.kwargs["input"][-1]["output"]))

    def test_invalid_arguments_and_unknown_tools_never_execute(self):
        for name, arguments in [
            ("search_chats", '{"query":"Berlin","sql":"SELECT password FROM users"}'),
            ("search_chats", '{"query":42}'),
            ("search_chats", '{}'),
            ("read_post", '{"slug":"test","offset":true}'),
            ("read_post", '{"slug":"test","offset":-1}'),
            ("shell", '{"command":"whoami"}'),
        ]:
            with self.subTest(name=name, arguments=arguments):
                tool = Mock()
                call = ResponseFunctionToolCall(
                    type="function_call", name=name, arguments=arguments, call_id="bad",
                )

                with patch("ai.assistant.create_response", side_effect=[
                    SimpleNamespace(status="completed", output=[call], output_text=""),
                    SimpleNamespace(status="completed", output=[], output_text="answer"),
                ]), patch.dict("ai.assistant.TOOLS_MAP", {name: tool}):
                    ask_assistant("question")

                tool.assert_not_called()

    def test_incomplete_output_is_not_sent_or_executed(self):
        call = ResponseFunctionToolCall(
            type="function_call", name="search_chats", arguments='{"query":"Berlin"}', call_id="call",
        )
        tool = Mock()

        with patch("ai.assistant.create_response", return_value=SimpleNamespace(
            status="incomplete", output=[call], output_text="partial",
        )), patch.dict("ai.assistant.TOOLS_MAP", {"search_chats": tool}):
            self.assertNotEqual(ask_assistant("question"), "partial")

        tool.assert_not_called()

    def test_question_and_quote_limits_are_independent_and_explicit(self):
        with patch("ai.assistant.create_response", return_value=SimpleNamespace(
            status="completed", output=[], output_text="answer",
        )) as api:
            ask_assistant("x" * 5000, reply_to_text="y" * 9000, reply_is_bot=True)

        data = json.loads(api.call_args.kwargs["input"][0]["content"])
        self.assertEqual(len(data["current_message"]), 4096)
        self.assertEqual(len(data["reply_to"]), 8192)
        self.assertTrue(data["current_message_truncated"])
        self.assertTrue(data["reply_to_truncated"])
        self.assertTrue(data["reply_is_bot"])

    def test_tool_registry_and_strict_schemas_agree(self):
        import inspect

        self.assertEqual(set(TOOLS_MAP), {tool["name"] for tool in TOOLS_DESCRIPTION})
        self.assertEqual(len(TOOLS_MAP), len(TOOLS_DESCRIPTION))

        for tool in TOOLS_DESCRIPTION:
            with self.subTest(tool=tool["name"]):
                schema = tool["parameters"]
                self.assertTrue(tool["strict"])
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["required"]), set(schema["properties"]))
                self.assertTrue(set(schema["properties"]) <= set(inspect.signature(TOOLS_MAP[tool["name"]]).parameters))

        schema = next(tool["parameters"] for tool in TOOLS_DESCRIPTION if tool["name"] == "read_club_guide")

        with self.assertRaises(ValueError):
            parse_tool_arguments('{"topic":"passwords","offset":null}', schema)


class AssistantRetrievalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            slug="ai-reader", full_name="Reader", email="private@example.com",
            moderation_status=User.MODERATION_STATUS_APPROVED, bio="Private biography",
            membership_started_at=datetime.utcnow(), membership_expires_at=datetime.utcnow() + timedelta(days=30),
        )
        self.post = Post.objects.create(
            author=self.user, slug="ai-post", title="Post", text="a" * 8000 + "last page",
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        SearchIndex.update_post_index(self.post)
        SearchIndex.update_user_index(self.user)

    def test_post_pages(self):
        first = read_post(self.post.slug)
        self.assertEqual(len(first["text_markdown"]), 8000)
        self.assertEqual(first["next_offset"], 8000)
        second = read_post(self.post.slug, offset=first["next_offset"])
        self.assertEqual(second["text_markdown"], "last page")
        self.assertIsNone(second["next_offset"])

    def test_hidden_posts_and_private_intros_are_not_readable(self):
        for visibility in (Post.VISIBILITY_DRAFT, Post.VISIBILITY_LINK_ONLY):
            Post.objects.filter(id=self.post.id).update(visibility=visibility)
            self.assertIn("error", read_post(self.post.slug))
            self.assertIn("error", read_discussion(self.post.slug))

        Post.objects.filter(id=self.post.id).update(visibility=Post.VISIBILITY_EVERYWHERE, type=Post.TYPE_INTRO)
        User.objects.filter(id=self.user.id).update(profile_publicity_level=User.PUBLICITY_LEVEL_PRIVATE)
        self.assertIn("error", read_post(self.post.slug))
        self.assertEqual(generic_search(""), [])

    def test_discussion_filters_and_pages(self):
        parent = Comment.objects.create(post=self.post, author=self.user, text="parent", upvotes=100)
        reply = Comment.objects.create(post=self.post, text="reply", reply_to=parent)
        hidden = Comment.objects.create(post=self.post, text="hidden", is_visible=False, reply_to=parent)
        Comment.objects.create(post=self.post, text="deleted", is_deleted=True)

        for index in range(10):
            Comment.objects.create(post=self.post, text=str(index))

        first = read_discussion(self.post.slug)
        self.assertEqual(len(first["comments"]), 10)
        self.assertEqual(first["comments"][0]["id"], str(parent.id))
        self.assertEqual(len(read_discussion(self.post.slug, offset=first["next_offset"])["comments"]), 2)
        replies = read_discussion(self.post.slug, reply_to_id=str(parent.id))["comments"]
        self.assertEqual({item["id"] for item in replies}, {str(parent.id), str(reply.id)})
        self.assertIn("error", read_discussion(self.post.slug, reply_to_id=str(hidden.id)))

    def test_profile_returns_only_public_identity(self):
        result = search_users("")[0]
        self.assertEqual(set(result), {"slug", "full_name", "profile_url"})
        User.objects.filter(id=self.user.id).update(profile_publicity_level=User.PUBLICITY_LEVEL_PRIVATE)
        self.assertEqual(search_users(""), [])

    def test_read_comment_pages_and_visibility(self):
        comment = Comment.objects.create(post=self.post, text="a" * 8000 + "last")
        SearchIndex.update_comment_index(comment)
        first = read_comment(str(comment.id))
        self.assertEqual(first["next_offset"], 8000)
        self.assertEqual(read_comment(str(comment.id), offset=8000)["text_markdown"], "last")
        Comment.objects.filter(id=comment.id).update(is_visible=False)
        self.assertIn("error", read_comment(str(comment.id)))
        self.assertEqual(search_post_comments(self.post.slug, ""), [])

    def test_scoped_search_does_not_cross_post_or_room(self):
        room = Room.objects.create(slug="test-room", title="Room", color="black")
        Post.objects.filter(id=self.post.id).update(room=room)
        other = Post.objects.create(author=self.user, slug="other-post", title="Other", text="Other")
        SearchIndex.update_post_index(other)
        first = Comment.objects.create(post=self.post, text="first")
        second = Comment.objects.create(post=other, text="second")
        SearchIndex.update_comment_index(first)
        SearchIndex.update_comment_index(second)
        self.assertEqual([item["id"] for item in search_post_comments(self.post.slug, "")], [str(first.id)])
        self.assertEqual([item["slug"] for item in search_room_posts(room.slug, "")], [self.post.slug])
        Room.objects.filter(slug=room.slug).update(is_visible=False)
        self.assertEqual(search_room_posts(room.slug, ""), [])
        Post.objects.filter(id=self.post.id).update(visibility=Post.VISIBILITY_DRAFT)
        self.assertEqual(search_post_comments(self.post.slug, ""), [])
        self.assertIn("error", read_comment(str(first.id)))

    def test_guides_work_without_keywords_or_search_index(self):
        for slug in ("ai_policy", "10447", "values"):
            Post.objects.create(
                author=self.user, slug=slug, title=slug, text="Guidance", type=Post.TYPE_DOCS,
                visibility=Post.VISIBILITY_EVERYWHERE,
            )

        result = read_club_guide("ai")
        self.assertEqual([doc["slug"] for doc in result["documents"]], ["ai_policy", "10447", "values"])
        self.assertEqual(result["missing_slugs"], [])
        self.assertIsNone(result["next_offset"])

    def test_guide_pages_preserve_late_rules(self):
        Post.objects.create(
            author=self.user, slug="4916", title="Memes", text="x" * 6000 + "Late example",
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        first = read_club_guide("memes")
        self.assertTrue(first["documents"][0]["text_truncated"])
        second = read_club_guide("memes", offset=first["next_offset"])
        self.assertEqual(second["documents"][0]["text_markdown"], "Late example")
        self.assertIsNone(second["next_offset"])

    def test_guide_visibility_and_missing_documents(self):
        Post.objects.create(
            author=self.user, slug="ai_policy", title="AI", text="Hidden", visibility=Post.VISIBILITY_DRAFT,
        )
        Post.objects.create(
            author=self.user, slug="10447", title="Deleted", text="Hidden", deleted_at=datetime.utcnow(),
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        result = read_club_guide("ai")
        self.assertEqual(result["documents"], [])
        self.assertEqual(set(result["missing_slugs"]), {"ai_policy", "10447", "values"})
        self.assertIn("error", read_club_guide("unknown"))

    def test_rules_search_prefers_relevance_over_recency(self):
        relevant = Post.objects.create(
            author=self.user, slug="relevant-guide", title="Quokka", text="Quokka", type=Post.TYPE_DOCS,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        newer = Post.objects.create(
            author=self.user, slug="newer-guide", title="Other", text="Something about quokka", type=Post.TYPE_DOCS,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        SearchIndex.update_post_index(relevant)
        SearchIndex.update_post_index(newer)
        self.assertEqual(club_rules_and_info("quokka", limit=1)[0]["slug"], relevant.slug)


class ChatSearchTests(TestCase):
    def setUp(self):
        Room.objects.create(slug="berlin", title="Берлин", chat_name="Вастрик.Берлин", color="black")
        Room.objects.create(slug="radiolove", title="Радиолюбители", color="black")
        Room.objects.create(slug="hidden", title="Секретная комната", color="black", is_visible=False)

    def test_typo_transliteration_slug_and_unrelated_query(self):
        for query in ("Берлни", "berln", "Berlin", "берлин"):
            with self.subTest(query=query):
                self.assertEqual(search_chats(query)[0]["slug"], "berlin")

        self.assertEqual(search_chats("radiolvoe")[0]["slug"], "radiolove")
        self.assertEqual(search_chats("qxzjkv"), [])
        self.assertEqual(search_chats(""), [])

    def test_hidden_rooms_and_private_room_fields_are_not_returned(self):
        self.assertEqual(search_chats("Секретная"), [])
        result = search_chats("Берлин")[0]
        self.assertNotIn("admins", result)
        self.assertNotIn("chat_id", result)
        self.assertIn("room_url", result)
