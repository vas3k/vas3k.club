from badges.models import UserBadge, Badge
from bookmarks.models import PostBookmark
from comments.models import Comment
from gdpr.models import DataRequests
from godmode.actions.post_announce import get_announce_action, post_announce_action
from godmode.actions.post_comments import get_comments_action, post_comments_action
from godmode.actions.post_feeds import get_feeds_action, post_feeds_action
from godmode.actions.post_label import get_label_action, post_label_action
from godmode.actions.post_owner import get_owner_action, post_owner_action
from godmode.actions.post_pin import get_pin_action, post_pin_action
from godmode.actions.post_view import view_post_action
from godmode.actions.tag_join import get_join_tag_action, post_join_tag_action
from godmode.actions.user_achievement import get_achievement_action, post_achievement_action
from godmode.actions.user_ban import get_ban_action, post_ban_action
from godmode.actions.user_delete import get_delete_action, post_delete_action
from godmode.actions.user_hat import get_hat_action, post_hat_action
from godmode.actions.user_ping import get_ping_action, post_ping_action
from godmode.actions.user_profile import view_profile_action
from godmode.actions.user_prolong import get_prolong_action, post_prolong_action
from godmode.actions.user_role import get_role_action, post_role_action
from godmode.actions.user_unmoderate import get_unmoderate_action, post_unmoderate_action
from godmode.models import ClubSettings
from godmode.admin import ClubAdmin, ClubAdminGroup, ClubAdminModel, ClubAdminPage, ClubAdminField, ClubAdminAction
from godmode.pages.badge_generator import badge_generator
from godmode.pages.digest import compose_weekly_digest
from godmode.pages.invite import invite_user_by_email
from godmode.pages.mass_achievement import mass_achievement
from godmode.pages.mass_email import mass_email
from godmode.pages.moderation import moderation
from godmode.pages.sunday_posts import sunday_posts
from invites.models import Invite
from misc.models import NetworkGroup, ProTip
from posts.models.linked import LinkedPost
from posts.models.post import Post
from rooms.models import Room
from tags.models import Tag, UserTag
from tickets.models import Ticket, TicketSale
from users.models.achievements import Achievement, UserAchievement
from users.models.friends import Friend
from users.models.geo import Geo
from users.models.mute import UserMuted
from users.models.notes import UserNote
from users.models.user import User

ADMIN = ClubAdmin(
    title="Админка Клуба",
    groups=[
        ClubAdminGroup(
            title="Основное",
            icon="✖︎",
            models=[
                ClubAdminModel(
                    model=ClubSettings,
                    title="Настройки Клуба",
                    icon="⚙️",
                    name="settings",
                    list_roles={User.ROLE_GOD},
                    edit_roles={User.ROLE_GOD},
                    delete_roles={User.ROLE_GOD},
                    create_roles={User.ROLE_GOD},
                ),
                ClubAdminPage(
                    title="Модерация",
                    icon="👮",
                    view=moderation,
                    name="moderation",
                ),
                ClubAdminPage(
                    title="Пригласить в Клуб",
                    icon="🎁",
                    name="invite",
                    view=invite_user_by_email,
                    access_roles={User.ROLE_GOD},
                )
            ],
        ),
        ClubAdminGroup(
            title="Рассылки",
            icon="💌",
            models=[
                ClubAdminPage(
                    title="Дайджест",
                    icon="📧",
                    name="digest",
                    view=compose_weekly_digest,
                    access_roles={User.ROLE_GOD},
                ),
                ClubAdminPage(
                    title="Массовые рассылки",
                    icon="📬",
                    name="mass_email",
                    view=mass_email,
                    access_roles={User.ROLE_GOD},
                )
            ]
        ),
        ClubAdminGroup(
            title="Юзеры",
            icon="🪪",
            models=[
                ClubAdminModel(
                    model=User,
                    title="Юзеры",
                    icon="👤",
                    name="users",
                    title_field="full_name",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    delete_roles=set(),
                    create_roles=set(),
                    list_fields=[
                        ClubAdminField(
                            name="avatar",
                            display_name="🖼️",
                            list_template="godmode/widgets/avatar.html",
                        ),
                        "full_name",
                        "slug",
                        "email",
                        "position",
                        "company",
                        "city",
                        "created_at",
                        "moderation_status",
                        "membership_started_at",
                        "membership_expires_at",
                        "membership_platform_type",
                        "upvotes",
                        "is_email_verified",
                        "is_email_unsubscribed",
                        "is_banned_until",
                        "deleted_at",
                    ],
                    hide_fields=["secret_hash", "roles"],
                    actions={
                        "profile": ClubAdminAction(
                            title="🪪 Посмотреть профиль",
                            get=view_profile_action
                        ),
                        "ban": ClubAdminAction(
                            title="💣 Забанить",
                            get=get_ban_action,
                            post=post_ban_action,
                        ),
                        "achievements": ClubAdminAction(
                            title="🌟 Дать ачивку",
                            get=get_achievement_action,
                            post=post_achievement_action,
                        ),
                        "unmoderate": ClubAdminAction(
                            title="💩 Размодерировать",
                            get=get_unmoderate_action,
                            post=post_unmoderate_action,
                        ),
                        "hat": ClubAdminAction(
                            title="🎓 Дать шапку",
                            get=get_hat_action,
                            post=post_hat_action,
                        ),
                        "prolong": ClubAdminAction(
                            title="⏰ Продлить членство",
                            get=get_prolong_action,
                            post=post_prolong_action,
                        ),
                        "roles": ClubAdminAction(
                            title="🛂 Выдать роль",
                            get=get_role_action,
                            post=post_role_action,
                        ),
                        "message": ClubAdminAction(
                            title="✉️ Написать юзеру",
                            get=get_ping_action,
                            post=post_ping_action,
                        ),
                        "delete": ClubAdminAction(
                            title="⛔ Удалить аккаунт",
                            get=get_delete_action,
                            post=post_delete_action,
                        ),
                    }
                ),
                ClubAdminModel(
                    model=Friend,
                    title="Друзья",
                    icon="👥",
                    name="friends",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "user_from",
                        "user_to",
                        "created_at",
                        "is_subscribed_to_posts",
                        "is_subscribed_to_comments",
                    ]
                ),
                ClubAdminModel(
                    model=UserNote,
                    title="Заметки",
                    icon="📝",
                    name="notes",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "user_from",
                        "user_to",
                        "text",
                        "created_at",
                    ]
                ),
                ClubAdminModel(
                    model=UserMuted,
                    title="Мьюты и жалобы",
                    icon="🔇",
                    name="mute",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "user_from",
                        "user_to",
                        "created_at",
                        "comment",
                    ]
                ),
                ClubAdminModel(
                    model=UserBadge,
                    title="Награды",
                    icon="🏅",
                    name="badges",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "from_user",
                        "to_user",
                        "badge",
                        "post",
                        "comment",
                        "created_at",
                        "note",
                    ]
                ),
                ClubAdminModel(
                    model=Geo,
                    title="География",
                    icon="🌍",
                    name="geo",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                ),
                ClubAdminModel(
                    model=Invite,
                    title="Инвайты",
                    icon="🎁",
                    name="invites",
                    list_fields=[
                        "code",
                        "user",
                        "created_at",
                        "used_at",
                        "invited_email",
                        "invited_user",
                    ]
                ),
            ],
        ),
        ClubAdminGroup(
            title="Посты и комменты",
            icon="✏️",
            models=[
                ClubAdminModel(
                    model=Post,
                    title="Посты",
                    icon="📝",
                    name="posts",
                    title_field="title",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    edit_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    delete_roles=set(),
                    create_roles=set(),
                    list_fields=[
                        "slug",
                        "type",
                        "title",
                        "author",
                        "upvotes",
                        "comment_count",
                        "view_count",
                        "created_at",
                        "published_at",
                        "is_public",
                        "moderation_status",
                        "visibility",
                    ],
                    hide_fields=["html", "deleted_at"],
                    actions={
                        "post": ClubAdminAction(
                            title="📝 Посмотреть пост",
                            get=view_post_action
                        ),
                        "pin": ClubAdminAction(
                            title="📌 Запинить/отпинить",
                            get=get_pin_action,
                            post=post_pin_action,
                            access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                        ),
                        "announce": ClubAdminAction(
                            title="📢 Анонсировать",
                            get=get_announce_action,
                            post=post_announce_action,
                        ),
                        "label": ClubAdminAction(
                            title="🏷️ Выдать лейбл",
                            get=get_label_action,
                            post=post_label_action,
                            access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                        ),
                        "visibility": ClubAdminAction(
                            title="👁️ Поведение на главной",
                            get=get_feeds_action,
                            post=post_feeds_action,
                            access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                        ),
                        "comments": ClubAdminAction(
                            title="💬 Закрыть комментарии",
                            get=get_comments_action,
                            post=post_comments_action,
                            access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                        ),
                        "owner": ClubAdminAction(
                            title="👤 Изменить владельца",
                            get=get_owner_action,
                            post=post_owner_action,
                            access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                        ),
                    }
                ),
                ClubAdminModel(
                    model=Comment,
                    title="Комментарии",
                    icon="💭",
                    name="comments",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    delete_roles=set(),
                    create_roles=set(),
                    list_fields=[
                        "post",
                        "author",
                        "text",
                        "upvotes",
                        "created_at",
                        "is_visible",
                        "is_deleted",
                    ],
                    hide_fields=["html"]
                ),
                ClubAdminModel(
                    model=LinkedPost,
                    title="Связанные посты",
                    icon="🔗",
                    name="linked_posts",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    delete_roles=set(),
                    create_roles=set(),
                ),
                ClubAdminModel(
                    model=PostBookmark,
                    title="Закладки",
                    icon="💙",
                    name="bookmarks",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    delete_roles=set(),
                    create_roles=set(),
                ),
            ],
        ),
        ClubAdminGroup(
            title="Ачивки",
            icon="🏆",
            models=[
                ClubAdminModel(
                    model=Achievement,
                    title="Ачивки",
                    icon="🥇",
                    name="achievements",
                    title_field="name",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        ClubAdminField(
                            name="image",
                            display_name="image",
                            list_template="godmode/widgets/avatar.html",
                        ),
                        "name",
                        "code",
                        "description",
                        "style",
                        "is_visible",
                        "index",
                    ]
                ),
                ClubAdminModel(
                    model=UserAchievement,
                    title="Кому выданы",
                    icon="🌟",
                    name="user_achievements",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    edit_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "user",
                        "achievement",
                        "created_at",
                    ],
                ),
                ClubAdminPage(
                    title="Массовые ачивки",
                    icon="🏅",
                    name="mass_achievement",
                    access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    view=mass_achievement,
                )
            ],
        ),
        ClubAdminGroup(
            title="Теги",
            icon="🏷️",
            models=[
                ClubAdminModel(
                    model=Tag,
                    title="Теги",
                    icon="🔖",
                    name="tags",
                    title_field="name",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "name",
                        "code",
                        "group",
                        "index",
                        "is_visible",
                    ],
                    actions={
                        "join": ClubAdminAction(
                            title="🔗 Объединить с другим тегом",
                            get=get_join_tag_action,
                            post=post_join_tag_action,
                        ),
                    }
                ),
                ClubAdminModel(
                    model=UserTag,
                    title="Теги юзеров",
                    icon="🏷️",
                    name="user_tags",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "user",
                        "tag",
                        "created_at",
                    ]
                ),
            ]
        ),
        ClubAdminGroup(
            title="Нетворк",
            icon="🌐",
            models=[
                ClubAdminModel(
                    model=Room,
                    title="Комнаты",
                    icon="📁",
                    name="rooms",
                    title_field="title",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "icon",
                        "title",
                        "description",
                        "color",
                        "network_group",
                        "chat_url",
                        "chat_member_count",
                        "send_new_posts_to_chat",
                        "send_new_comments_to_chat",
                        "is_visible",
                        "is_open_for_posting",
                        "index",
                    ]
                ),
                ClubAdminModel(
                    model=NetworkGroup,
                    title="Нетворк-группы",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    icon="🌍",
                    name="network_groups",
                ),
            ],
        ),
        ClubAdminGroup(
            title="Билеты",
            icon="🎟️",
            models=[
                ClubAdminModel(
                    model=Ticket,
                    title="Билеты",
                    icon="🎫",
                    name="tickets",
                    list_fields=[
                        "name",
                        "code",
                        "achievement",
                        "tickets_sold",
                        "limit_quantity",
                    ]
                ),
                ClubAdminModel(
                    model=TicketSale,
                    title="Проданные билеты",
                    icon="📈",
                    name="ticket_sales",
                ),
            ],
        ),
        ClubAdminGroup(
            title="Разное",
            icon="😉",
            models=[
                ClubAdminModel(
                    model=ProTip,
                    title="Про-типсы",
                    icon="💡",
                    name="pro_tips",
                    list_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    edit_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    create_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                    list_fields=[
                        "title",
                        "text",
                        "created_at",
                        "updated_at",
                        "is_visible",
                    ]
                ),
                ClubAdminModel(
                    model=DataRequests,
                    title="Запросы данных",
                    icon="🗃️",
                    name="data_requests",
                    list_roles={User.ROLE_GOD},
                    edit_roles={User.ROLE_GOD},
                    delete_roles={User.ROLE_GOD},
                    create_roles={User.ROLE_GOD},
                ),
                ClubAdminPage(
                    title="Генератор бейджиков",
                    icon="🪪",
                    name="badge_generator",
                    view=badge_generator,
                ),
                ClubAdminPage(
                    title="Нетленки",
                    icon="💎",
                    name="sunday_posts",
                    view=sunday_posts,
                    access_roles={User.ROLE_MODERATOR, User.ROLE_GOD, User.ROLE_CURATOR},
                ),
            ],
        )
    ],
    foreign_key_templates={
        User: "godmode/widgets/user.html",
        Post: "godmode/widgets/post.html",
        Comment: "godmode/widgets/comment.html",
        Tag: "godmode/widgets/tag.html",
        Badge: "godmode/widgets/badge.html",
    }
)

ITEMS_PER_PAGE = 100
