import re

USERNAME_RE = re.compile(r"(?:\s|\n|^)@([A-Za-z0-9_-]{3,})")
IMAGE_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png)")
VIDEO_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:mov|mp4)")
YOUTUBE_RE = re.compile(
    (
        r"http(?:s?):\/\/(?:www\.)?(?:youtube\.com\/(?:watch\?v=|playlist\?)|youtu\.be\/)"
        r"(?:(?:(?<=\bv=)|(?<=youtu\.be\/))([\w\-\_]*))?(?:.*list=(PL[\w\-\_]*))?"
    )
)
TWITTER_RE = re.compile(r"(https?:\/\/twitter.com\/[a-zA-Z0-9_]+\/status\/[\d]+)")
FAVICON_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|ico)")
