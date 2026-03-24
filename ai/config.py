OPENAI_CHAT_MODEL = "gpt-4.1"

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_SLIDING_WINDOW_SECONDS = 3600  # 1 hour

TRIM_LONG_CONTENT_TO_LEN = 2000
USER_INPUT_MAX_LEN = 1000

CLUB_INFO_POST_LABEL = "essential"
CLUB_INFO_POST_SLUGS = [
    "about",
    "values",
    "contact",
    "10447", # good and bad content
    "10857",  # how to moderate
]
CLUB_EXTRA_INFO_POST_SLUGS = [
    "privacy_policy",
    "ai_policy",
    "7979",  # club bot
    "4916",  # memes
    "25328",  # why club is helpful
    "23360",  # why club is helpful
    "14856",  # towers
]
