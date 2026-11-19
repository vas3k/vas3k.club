OPENAI_CHAT_MODEL = "gpt-6.1-sol"
REASONING_EFFORT = "low"

AI_GLOBAL_HOURLY_REQUESTS = 60

TRIM_LONG_CONTENT_TO_LEN = 2000
USER_INPUT_MAX_LEN = 4096
REPLY_INPUT_MAX_LEN = 8192

CLUB_INFO_POST_LABEL = "essential"
CLUB_INFO_POST_SLUGS = [
    "about",
    "values",
    "contact",
    "10447",  # good and bad content
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

CLUB_GUIDE_TOPICS = {
    "values": ["values", "about"],
    "posting": ["10447", "values"],
    "ai": ["ai_policy", "10447", "values"],
    "moderation": ["10857", "10447"],
    "membership": ["about", "contact"],
    "privacy": ["privacy_policy"],
    "memes": ["4916"],
    "bot": ["7979"],
}

AI_USER_DAILY_REQUESTS = 50
AI_GLOBAL_DAILY_REQUESTS = 500
