from django.conf import settings
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap

from auth.helpers import auth_switch
from auth.views.auth import login, logout, debug_dev_login
from auth.views.patreon import patreon_login, patreon_oauth_callback
from bot.views import webhook_telegram, link_telegram
from comments.views import create_comment, edit_comment, delete_comment, show_comment, upvote_comment, pin_comment
from landing.views import landing, docs, god_settings
from notifications.views import weekly_digest, email_unsubscribe, email_confirm, daily_digest, email_digest_switch
from payments.views import membership_expired
from posts.views import compose, compose_type, show_post, feed, upvote_post, edit_post, admin_post, announce_post
from posts.sitemaps import PublicPostsSitemap
from users.views import profile, edit_profile, on_review, banned, rejected, intro, toggle_tag, \
    add_expertise, admin_profile, delete_expertise

sitemaps = {
    "public_posts": PublicPostsSitemap,
}

urlpatterns = [
    path("", auth_switch(landing, feed), name="index"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),
    path("auth/patreon/", patreon_login, name="patreon_login"),
    path("auth/patreon_callback/", patreon_oauth_callback, name="patreon_oauth_callback"),

    path("monies/membership_expired/", membership_expired, name="membership_expired"),

    path("user/<slug:user_slug>/", profile, name="profile"),
    path("user/<slug:user_slug>/edit/", edit_profile, name="edit_profile"),
    path("user/<slug:user_slug>/admin/", admin_profile, name="admin_profile"),

    path("intro/", intro, name="intro"),
    path("profile/tag/<slug:tag_code>/toggle/", toggle_tag, name="toggle_tag"),
    path("profile/expertise/add/", add_expertise, name="add_expertise"),
    path("profile/expertise/<slug:expertise>/delete/", delete_expertise, name="delete_expertise"),
    path("profile/on_review/", on_review, name="on_review"),
    path("profile/rejected/", rejected, name="rejected"),
    path("profile/banned/", banned, name="banned"),

    path("feed/type/<slug:post_type>/", feed, name="feed_type"),
    path("feed/topic/<slug:topic_slug>/", feed, name="feed_topic"),

    path("create/", compose, name="compose"),
    path("create/<slug:post_type>/", compose_type, name="compose_type"),
    path("post/<slug:post_slug>/edit/", edit_post, name="edit_post"),
    path("post/<slug:post_slug>/upvote/", upvote_post, name="upvote_post"),
    path("post/<slug:post_slug>/admin/", admin_post, name="admin_post"),
    path("post/<slug:post_slug>/announce/", announce_post, name="announce_post"),
    path("post/<slug:post_slug>/comment/create/", create_comment, name="create_comment"),
    path("post/<slug:post_slug>/comment/<uuid:comment_id>/", show_comment, name="show_comment",),

    path("comment/<uuid:comment_id>/upvote/", upvote_comment, name="upvote_comment"),
    path("comment/<uuid:comment_id>/edit/", edit_comment, name="edit_comment"),
    path("comment/<uuid:comment_id>/pin/", pin_comment, name="pin_comment"),
    path("comment/<uuid:comment_id>/delete/", delete_comment, name="delete_comment"),

    path("telegram/link/", link_telegram, name="link_telegram"),
    path("telegram/webhook/<str:token>/", webhook_telegram, name="webhook_telegram"),

    path("notifications/confirm/<str:user_id>/<str:secret>/", email_confirm, name="email_confirm"),
    path("notifications/unsubscribe/<str:user_id>/<str:secret>/", email_unsubscribe, name="email_unsubscribe"),
    path("notifications/switch/<str:digest_type>/<str:user_id>/<str:secret>/", email_digest_switch,
         name="email_digest_switch"),
    path("notifications/renderer/digest/weekly/", weekly_digest, name="render_weekly_digest"),
    path("notifications/renderer/digest/daily/<slug:user_slug>/", daily_digest, name="render_daily_digest"),

    path("docs/<slug:doc_slug>/", docs, name="docs"),

    path("godmode/", god_settings, name="god_settings"),
    path("godmode/dev_login/", debug_dev_login, name="debug_dev_login"),

    # keep this guy at the bottom
    path("<slug:post_type>/<slug:post_slug>/", show_post, name="show_post"),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
