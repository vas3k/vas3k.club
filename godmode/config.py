from badges.models import UserBadge, Badge
from bookmarks.models import PostBookmark
from comments.models import Comment
from gdpr.models import DataRequests
from godmode.models import ClubSettings
from godmode.admin import ClubAdmin, ClubAdminGroup, ClubAdminModel, ClubAdminPage, ClubAdminField
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
                ),
                ClubAdminPage(
                    title="Пригласить в Клуб",
                    icon="🎁",
                    name="invite",
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
                ),
                ClubAdminPage(
                    title="Массовые рассылки",
                    icon="📬",
                    name="mass_email",
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
                ),
                ClubAdminModel(
                    model=Friend,
                    title="Друзья",
                    icon="👥",
                    name="friends",
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
                        "is_visible",
                        "is_public",
                        "is_commentable",
                        "is_visible_in_feeds",
                        "is_shadow_banned",
                    ],
                    hide_fields=["html"]
                ),
                ClubAdminModel(
                    model=Comment,
                    title="Комментарии",
                    icon="💭",
                    name="comments",
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
                ),
                ClubAdminModel(
                    model=PostBookmark,
                    title="Закладки",
                    icon="💙",
                    name="bookmarks",
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
                    list_fields=[
                        "name",
                        "code",
                        "group",
                        "index",
                        "is_visible",
                    ]
                ),
                ClubAdminModel(
                    model=UserTag,
                    title="Теги юзеров",
                    icon="🏷️",
                    name="user_tags",
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
                ),
                ClubAdminPage(
                    title="Генератор бейджиков",
                    icon="🪪",
                    name="badge_generator",
                ),
                ClubAdminPage(
                    title="Нетленки",
                    icon="💎",
                    name="sunday_posts",
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
