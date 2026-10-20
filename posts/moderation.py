from enum import Enum


class PostRejectReason(Enum):
    ad = "ad"
    bias = "bias"
    chat = "chat"
    design = "design"
    draft = "draft"
    duplicate = "duplicate"
    dyor = "dyor"
    false_dilemma = "false_dilemma"
    github = "github"
    hot = "hot"
    inside = "inside"
    self = "self"
    title = "title"
    tldr = "tldr"
    tldr_link = "tldr_link"
    value = "value"
