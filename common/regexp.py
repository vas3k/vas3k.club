import re

USERNAME_RE = re.compile(r"(?:\s|\n|^)@([A-Za-z0-9_-]{3,})")
IMAGE_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png)")
VIDEO_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:mov|mp4)")
YOUTUBE_RE = re.compile(
    r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
)
TWITTER_RE = re.compile(r"(https?:\/\/twitter.com\/[a-zA-Z0-9_]+\/status\/[\d]+)")
FAVICON_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|ico)")
