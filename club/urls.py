from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path

from auth.helpers import auth_switch
from auth.views.auth import login, logout, debug_dev_login, debug_random_login, join
from auth.views.email import email_login, email_login_code
from auth.views.external import external_login
from auth.views.patreon import patreon_login, patreon_oauth_callback
from bot.views import webhook_telegram, link_telegram
from comments.views import create_comment, edit_comment, delete_comment, show_comment, upvote_comment, \
    retract_comment_vote, pin_comment
from landing.views import landing, docs, god_settings
from misc.views import achievements, network
from notifications.views import weekly_digest, email_unsubscribe, email_confirm, daily_digest, email_digest_switch
from payments.views import membership_expired, pay, done, stripe_webhook, stop_subscription
from posts.api import md_show_post, api_show_post
from posts.models.post import Post
from posts.rss import NewPostsRss
from posts.sitemaps import sitemaps
from posts.views.admin import admin_post, announce_post
from posts.views.api import toggle_post_bookmark
from posts.views.feed import feed
from posts.views.posts import show_post, edit_post, upvote_post, retract_post_vote, compose, compose_type, \
    toggle_post_subscription
from bookmarks.views import bookmarks
from search.views import search
from users.api import api_profile
from users.views.delete_account import request_delete_account, confirm_delete_account
from users.views.messages import on_review, rejected, banned
from users.views.profile import profile, toggle_tag, add_expertise, delete_expertise
from users.views.settings import profile_settings, edit_profile, edit_account, edit_notifications, edit_payments, \
    edit_bot, edit_data, request_data
from users.views.intro import intro
from users.views.admin import admin_profile
from users.views.people import people

POST_TYPE_RE = r"(?P<post_type>(all|{}))".format("|".join(dict(Post.TYPES).keys()))
ORDERING_RE = r"(?P<ordering>(activity|new|top|top_week|top_month))"

urlpatterns = [
    path("", auth_switch(landing, feed), name="index"),

    path("join/", join, name="join"),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),
    path("auth/patreon/", patreon_login, name="patreon_login"),
    path("auth/patreon_callback/", patreon_oauth_callback, name="patreon_oauth_callback"),
    path("auth/email/", email_login, name="email_login"),
    path("auth/email/code/", email_login_code, name="email_login_code"),
    path("auth/external/", external_login, name="external_login"),

    path("monies/", pay, name="pay"),
    path("monies/done/", done, name="done"),
    path("monies/membership_expired/", membership_expired, name="membership_expired"),
    path("monies/stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("monies/subscription/<str:subscription_id>/stop/", stop_subscription, name="stop_subscription"),

    path("user/<slug:user_slug>/", profile, name="profile"),
    path("user/<slug:user_slug>.json", api_profile, name="api_profile"),
    path("user/<slug:user_slug>/edit/", profile_settings, name="profile_settings"),
    path("user/<slug:user_slug>/edit/profile/", edit_profile, name="edit_profile"),
    path("user/<slug:user_slug>/edit/account/", edit_account, name="edit_account"),
    path("user/<slug:user_slug>/edit/bot/", edit_bot, name="edit_bot"),
    path("user/<slug:user_slug>/edit/notifications/", edit_notifications, name="edit_notifications"),
    path("user/<slug:user_slug>/edit/monies/", edit_payments, name="edit_payments"),
    path("user/<slug:user_slug>/edit/data/", edit_data, name="edit_data"),
    path("user/<slug:user_slug>/edit/data/request/", request_data, name="request_user_data"),
    path("user/<slug:user_slug>/admin/", admin_profile, name="admin_profile"),
    path("user/<slug:user_slug>/delete/", request_delete_account, name="request_delete_account"),
    path("user/<slug:user_slug>/delete/confirm/", confirm_delete_account, name="confirm_delete_account"),

    path("intro/", intro, name="intro"),
    path("people/", people, name="people"),
    path("achievements/", achievements, name="achievements"),
    path("profile/tag/<slug:tag_code>/toggle/", toggle_tag, name="toggle_tag"),
    path("profile/expertise/add/", add_expertise, name="add_expertise"),
    path("profile/expertise/<slug:expertise>/delete/", delete_expertise, name="delete_expertise"),
    path("profile/on_review/", on_review, name="on_review"),
    path("profile/rejected/", rejected, name="rejected"),
    path("profile/banned/", banned, name="banned"),

    path("create/", compose, name="compose"),
    path("create/<slug:post_type>/", compose_type, name="compose_type"),
    path("post/<slug:post_slug>/edit/", edit_post, name="edit_post"),
    path("post/<slug:post_slug>/bookmark/", toggle_post_bookmark, name="toggle_post_bookmark"),
    path("post/<slug:post_slug>/upvote/", upvote_post, name="upvote_post"),
    path("post/<slug:post_slug>/retract_vote/", retract_post_vote, name="retract_post_vote"),
    path("post/<slug:post_slug>/subscription/", toggle_post_subscription, name="toggle_post_subscription"),
    path("post/<slug:post_slug>/admin/", admin_post, name="admin_post"),
    path("post/<slug:post_slug>/announce/", announce_post, name="announce_post"),
    path("post/<slug:post_slug>/comment/create/", create_comment, name="create_comment"),
    path("post/<slug:post_slug>/comment/<uuid:comment_id>/", show_comment, name="show_comment", ),

    path("bookmarks/", bookmarks, name="bookmarks"),

    path("search/", search, name="search"),
    path("room/<slug:topic_slug>/", feed, name="feed_topic"),
    path("room/<slug:topic_slug>/<slug:ordering>/", feed, name="feed_topic_ordering"),

    path("comment/<uuid:comment_id>/upvote/", upvote_comment, name="upvote_comment"),
    path("comment/<uuid:comment_id>/retract_vote/", retract_comment_vote, name="retract_comment_vote"),
    path("comment/<uuid:comment_id>/edit/", edit_comment, name="edit_comment"),
    path("comment/<uuid:comment_id>/pin/", pin_comment, name="pin_comment"),
    path("comment/<uuid:comment_id>/delete/", delete_comment, name="delete_comment"),

    path("telegram/link/", link_telegram, name="link_telegram"),
    path("telegram/webhook/<str:token>/", webhook_telegram, name="webhook_telegram"),

    path("notifications/confirm/<str:secret>/", email_confirm, name="email_confirm"),
    path("notifications/confirm/<str:secret>/<str:legacy_code>/", email_confirm, name="email_confirm_legacy"),
    path("notifications/unsubscribe/<str:user_id>/<str:secret>/", email_unsubscribe, name="email_unsubscribe"),
    path("notifications/switch/<str:digest_type>/<str:user_id>/<str:secret>/", email_digest_switch,
         name="email_digest_switch"),
    path("notifications/renderer/digest/weekly/", weekly_digest, name="render_weekly_digest"),
    path("notifications/renderer/digest/daily/<slug:user_slug>/", daily_digest, name="render_daily_digest"),

    path("docs/<slug:doc_slug>/", docs, name="docs"),

    path("network/", network, name="network"),

    path("godmode/", god_settings, name="god_settings"),
    path("godmode/dev_login/", debug_dev_login, name="debug_dev_login"),
    path("godmode/random_login/", debug_random_login, name="debug_random_login"),

    # feeds
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("posts.rss", NewPostsRss(), name="rss"),

    # keep these guys at the bottom
    re_path(r"^{}/$".format(POST_TYPE_RE), feed, name="feed_type"),
    re_path(r"^{}/{}/$".format(POST_TYPE_RE, ORDERING_RE), feed, name="feed_ordering"),
    path("<slug:post_type>/<slug:post_slug>/", show_post, name="show_post"),
    path("<slug:post_type>/<slug:post_slug>.md", md_show_post, name="md_show_post"),
    path("<slug:post_type>/<slug:post_slug>.json", api_show_post, name="api_show_post"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

# According to django doc: https://docs.djangoproject.com/en/3.1/topics/testing/overview/#other-test-conditions
# Regardless of the value of the DEBUG setting in your configuration file, all Django tests run with DEBUG=False
# so we use separate special var instead of settings.DEBUG
if settings.TESTS_RUN:
    from debug.api import api_me

    urlpatterns.append(path("debug/me", api_me, name="debug_api_me"))
