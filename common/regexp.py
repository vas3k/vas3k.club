import re

USERNAME_RE = re.compile(r"(?:\s|\n|^)@([A-Za-z0-9_-]{3,})")
IMAGE_RE = re.compile(r"https?://[^\s/$.?#].[^\s]*\.(?:jpg|jpeg|gif|png)")
VIDEO_RE = re.compile(r"https?://[^\s/$.?#].[^\s]*\.(?:mov|mp4)")
YOUTUBE_RE = re.compile(
    (
        r"http(?:s?):\/\/(?:www\.)?(?:youtube\.com\/(?:watch\?v=|playlist\?)|youtu\.be\/)"
        r"(?:(?:(?<=\bv=)|(?<=youtu\.be\/))([\w\-\_]*))?(?:.*list=(PL[\w\-\_]*))?"
    )
)
TWITTER_RE = re.compile(r"(https?:\/\/twitter.com\/[a-zA-Z0-9_]+\/status\/[\d]+)")
FAVICON_RE = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|ico)")

EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+"
)
