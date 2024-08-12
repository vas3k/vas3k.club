from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.views.generic import RedirectView

from authn.helpers import auth_switch
from authn.views.apps import list_apps, create_app, edit_app, delete_app
from authn.views.auth import login, logout, join
from authn.views.debug import debug_dev_login, debug_random_login, debug_login
from authn.views.email import email_login, email_login_code
from authn.views.openid import openid_authorize, openid_issue_token, openid_revoke_token, \
    openid_well_known_configuration, openid_well_known_jwks
from authn.views.patreon import patreon_sync, patreon_sync_callback
from badges.views import create_badge_for_post, create_badge_for_comment
from club import features
from comments.api import api_list_post_comments
from comments.views import create_comment, edit_comment, delete_comment, show_comment, upvote_comment, \
    retract_comment_vote, pin_comment, delete_comment_thread
from common.feature_flags import feature_switch
from landing.views import landing, docs, godmode_network_settings, godmode_digest_settings, godmode_settings, \
    godmode_invite
from misc.fun import badge_generator, mass_note
from misc.views import stats, network, robots, generate_ical_invite, generate_google_invite, show_achievement
from rooms.views import redirect_to_room_chat, list_rooms
from notifications.views import render_weekly_digest, email_unsubscribe, email_confirm, email_digest_switch, \
    link_telegram
from notifications.webhooks import webhook_event
from payments.views.common import membership_expired
from payments.api import api_gift_days
from payments.views.stripe import pay, done, stripe_webhook, stop_subscription
from payments.views.camp import stripe_camp_webhook
from payments.views.crypto import crypto, coinbase_webhook
from posts.api import md_show_post, api_show_post, json_feed
from posts.models.post import Post
from posts.rss import NewPostsRss
from posts.user_rss import UserPostsRss
from posts.sitemaps import sitemaps
from posts.views.admin_actions import admin_post, announce_post, curate_post
from posts.views.api import toggle_post_bookmark
from posts.views.feed import feed
from posts.views.posts import show_post, edit_post, upvote_post, retract_post_vote, compose, compose_type, \
    toggle_post_subscription, delete_post, unpublish_post, clear_post
from bookmarks.views import bookmarks
from search.views import search
from users.api import api_profile, api_profile_by_telegram_id
from users.views.delete_account import request_delete_account, confirm_delete_account
from users.views.friends import toggle_friend, friends
from users.views.messages import on_review, rejected, banned
from users.views.muted import toggle_mute, muted
from users.views.notes import edit_note
from users.views.profile import profile, toggle_tag, profile_comments, profile_posts, profile_badges
from users.views.settings import profile_settings, edit_profile, edit_account, edit_notifications, edit_payments, \
    edit_bot, edit_data, request_data
from users.views.intro import intro
from users.views.admin_actions import admin_profile
from users.views.people import people
from search.api import api_search_users, api_search_tags

POST_TYPE_RE = r"(?P<post_type>(all|{}))".format("|".join(dict(Post.TYPES).keys()))
ORDERING_RE = r"(?P<ordering>(activity|new|top|top_week|top_month|top_year|hot))"
urlpatterns = [
    path("", feature_switch(
        features.PRIVATE_FEED,                  # if private feed is enabled
        yes=auth_switch(yes=feed, no=landing),  # show it only for authorized users
        no=feed,                                # else - show it to everyone
    ), name="index"),

    path("landing", feature_switch(
        features.PRIVATE_FEED,
        yes=RedirectView.as_view(url="/", permanent=False),
        no=landing,
    ), name="landing"),

    path("join/", join, name="join"),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),
    path("auth/patreon/", patreon_sync, name="patreon_sync"),
    path("auth/patreon_callback/", patreon_sync_callback, name="patreon_sync_callback"),
    path("auth/email/", email_login, name="email_login"),
    path("auth/email/code/", email_login_code, name="email_login_code"),

    path("auth/openid/authorize", openid_authorize, name="openid_authorize"),
    path("auth/openid/token", openid_issue_token, name="openid_issue_token"),
    path("auth/openid/revoke", openid_revoke_token, name="openid_revoke_token"),

    path("monies/", pay, name="pay"),
    path("monies/crypto/", crypto, name="crypto"),
    path("monies/done/", done, name="done"),
    path("monies/membership_expired/", membership_expired, name="membership_expired"),
    path("monies/subscription/<str:subscription_id>/stop/", stop_subscription, name="stop_subscription"),
    path("monies/stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("monies/stripe/webhook_camp/", stripe_camp_webhook, name="stripe_camp_webhook"),
    path("monies/coinbase/webhook/", coinbase_webhook, name="coinbase_webhook"),
    path("monies/gift/<int:days>/<slug:user_slug>.json", api_gift_days, name="api_gift_days"),

    path("user/<slug:user_slug>/", profile, name="profile"),
    path("user/<slug:user_slug>.json", api_profile, name="api_profile"),
    path("user/by_telegram_id/<slug:telegram_id>.json", api_profile_by_telegram_id, name="api_profile_by_telegram_id"),
    path("user/<slug:user_slug>/comments/", profile_comments, name="profile_comments"),
    path("user/<slug:user_slug>/posts/", profile_posts, name="profile_posts"),
    path("user/<slug:user_slug>/badges/", profile_badges, name="profile_badges"),
    path("user/<slug:user_slug>/friend/", toggle_friend, name="toggle_friend"),
    path("user/<slug:user_slug>/friends/", friends, name="friends"),
    path("user/<slug:user_slug>/mute/", toggle_mute, name="toggle_mute"),
    path("user/<slug:user_slug>/muted/", muted, name="muted"),
    path("user/<slug:user_slug>/note/", edit_note, name="edit_note"),

    path("user/<slug:user_slug>/edit/", profile_settings, name="profile_settings"),
    path("user/<slug:user_slug>/edit/profile/", edit_profile, name="edit_profile"),
    path("user/<slug:user_slug>/edit/account/", edit_account, name="edit_account"),
    path("user/<slug:user_slug>/edit/bot/", edit_bot, name="edit_bot"),
    path("user/<slug:user_slug>/edit/notifications/", edit_notifications, name="edit_notifications"),
    path("user/<slug:user_slug>/edit/monies/", edit_payments, name="edit_payments"),
    path("user/<slug:user_slug>/edit/data/", edit_data, name="edit_data"),
    path("user/<slug:user_slug>/edit/data/request/", request_data, name="request_user_data"),
    path("user/<slug:user_slug>/admin/", admin_profile, name="admin_profile"),

    path("apps/", list_apps, name="apps"),
    path("apps/create/", create_app, name="create_app"),
    path("apps/<slug:app_id>/edit/", edit_app, name="edit_app"),
    path("apps/<slug:app_id>/delete/", delete_app, name="delete_app"),

    path("intro/", intro, name="intro"),
    path("people/", people, name="people"),
    path("achievements/", RedirectView.as_view(url="/stats", permanent=True), name="achievements"),
    path("achievements/<slug:achievement_code>/", show_achievement, name="show_achievement"),
    path("stats/", stats, name="stats"),

    path("profile/tag/<str:tag_code>/toggle/", toggle_tag, name="toggle_tag"),
    path("profile/on_review/", on_review, name="on_review"),
    path("profile/rejected/", rejected, name="rejected"),
    path("profile/banned/", banned, name="banned"),
    path("profile/delete/", request_delete_account, name="request_delete_account"),
    path("profile/delete/confirm/", confirm_delete_account, name="confirm_delete_account"),

    path("create/", compose, name="compose"),
    path("create/<slug:post_type>/", compose_type, name="compose_type"),
    path("post/<slug:post_slug>/unpublish/", unpublish_post, name="unpublish_post"),
    path("post/<slug:post_slug>/clear/", clear_post, name="clear_post"),
    path("post/<slug:post_slug>/delete/", delete_post, name="delete_post"),
    path("post/<slug:post_slug>/edit/", edit_post, name="edit_post"),
    path("post/<slug:post_slug>/bookmark/", toggle_post_bookmark, name="toggle_post_bookmark"),
    path("post/<slug:post_slug>/upvote/", upvote_post, name="upvote_post"),
    path("post/<slug:post_slug>/retract_vote/", retract_post_vote, name="retract_post_vote"),
    path("post/<slug:post_slug>/subscription/", toggle_post_subscription, name="toggle_post_subscription"),
    path("post/<slug:post_slug>/admin/", admin_post, name="admin_post"),
    path("post/<slug:post_slug>/curate/", curate_post, name="curate_post"),
    path("post/<slug:post_slug>/announce/", announce_post, name="announce_post"),
    path("post/<slug:post_slug>/comment/create/", create_comment, name="create_comment"),
    path("post/<slug:post_slug>/comment/<uuid:comment_id>/", show_comment, name="show_comment"),
    path("post/<slug:post_slug>/badge/", create_badge_for_post, name="create_badge_for_post"),

    path("bookmarks/", bookmarks, name="bookmarks"),

    path("search/", search, name="search"),
    path("search/users.json", api_search_users, name="api_search_users"),
    path("search/tags.json", api_search_tags, name="api_search_tags"),

    path("rooms/", list_rooms, name="list_rooms"),
    path("room/<slug:room_slug>/", feed, name="feed_room"),
    path("room/<slug:room_slug>/chat/", redirect_to_room_chat, name="redirect_to_room_chat"),
    path("room/<slug:room_slug>/<slug:ordering>/", feed, name="feed_room_ordering"),
    path("label/<slug:label_code>/", feed, name="feed_label"),
    path("label/<slug:label_code>/<slug:ordering>/", feed, name="feed_label_ordering"),

    path("comment/<uuid:comment_id>/upvote/", upvote_comment, name="upvote_comment"),
    path("comment/<uuid:comment_id>/retract_vote/", retract_comment_vote, name="retract_comment_vote"),
    path("comment/<uuid:comment_id>/edit/", edit_comment, name="edit_comment"),
    path("comment/<uuid:comment_id>/pin/", pin_comment, name="pin_comment"),
    path("comment/<uuid:comment_id>/delete/", delete_comment, name="delete_comment"),
    path("comment/<uuid:comment_id>/delete_thread/", delete_comment_thread, name="delete_comment_thread"),
    path("comment/<uuid:comment_id>/badge/", create_badge_for_comment,
         name="create_badge_for_comment"),

    path("telegram/link/", link_telegram, name="link_telegram"),

    path("notifications/confirm/<str:secret>/", email_confirm, name="email_confirm"),
    path("notifications/confirm/<str:secret>/<str:legacy_code>/", email_confirm, name="email_confirm_legacy"),
    path("notifications/unsubscribe/<str:user_id>/<str:secret>/", email_unsubscribe, name="email_unsubscribe"),
    path("notifications/switch/<str:digest_type>/<str:user_id>/<str:secret>/", email_digest_switch,
         name="email_digest_switch"),
    path("notifications/renderer/digest/weekly/", render_weekly_digest, name="render_weekly_digest"),
    path("notifications/webhook/<slug:event_type>", webhook_event, name="webhook_event"),

    path("docs/<slug:doc_slug>/", docs, name="docs"),

    path("network/", network, name="network"),
    path("network/chat/<slug:chat_id>/", RedirectView.as_view(url="/room/%(chat_id)s/chat/", permanent=True),
         name="network_chat"),

    # admin features
    path("godmode/", godmode_settings, name="godmode_settings"),
    path("godmode/admin/", admin.site.urls),
    path("godmode/network/", godmode_network_settings, name="godmode_network_settings"),
    path("godmode/digest/", godmode_digest_settings, name="godmode_digest_settings"),
    path("godmode/invite/", godmode_invite, name="godmode_invite"),
    path("godmode/dev_login/", debug_dev_login, name="debug_dev_login"),
    path("godmode/random_login/", debug_random_login, name="debug_random_login"),
    path("godmode/login/<str:user_slug>/", debug_login, name="debug_login"),

    # misc
    path("misc/calendar/ical", generate_ical_invite, name="generate_ical_invite"),
    path("misc/calendar/google", generate_google_invite, name="generate_google_invite"),
    path("misc/badge_generator/", badge_generator, name="badge_generator"),
    path("misc/mass_note/", mass_note, name="mass_note"),

    # feeds
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("posts.rss", NewPostsRss(), name="rss"),
    path("user/<slug:user_slug>/posts.rss", UserPostsRss(), name="user_rss"),
    path("feed.json", json_feed, name="json_feed"),
    re_path(r"^{}/{}/feed.json$".format(POST_TYPE_RE, ORDERING_RE), json_feed, name="json_feed_ordering"),

    path(".well-known/openid-configuration", openid_well_known_configuration, name="openid_well_known_configuration"),
    path(".well-known/jwks.json", openid_well_known_jwks, name="openid_well_known_jwks"),
    path("robots.txt", robots, name="robots"),

    # keep these guys at the bottom
    re_path(r"^{}/$".format(POST_TYPE_RE), feed, name="feed_type"),
    re_path(r"^{}/{}/$".format(POST_TYPE_RE, ORDERING_RE), feed, name="feed_ordering"),
    path("<slug:post_type>/<slug:post_slug>/", show_post, name="show_post"),
    path("<slug:post_type>/<slug:post_slug>.md", md_show_post, name="md_show_post"),
    path("<slug:post_type>/<slug:post_slug>.json", api_show_post, name="api_show_post"),
    path("<slug:post_type>/<slug:post_slug>/comments.json", api_list_post_comments, name="api_list_post_comments"),
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
