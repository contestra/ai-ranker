from enum import Enum

class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_PROVIDER = "FAILED_PROVIDER"
    FAILED_PROXY = "FAILED_PROXY"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_GROUNDING = "FAILED_GROUNDING"
    CANCELLED = "CANCELLED"

class GroundingMode(str, Enum):
    NONE = "NONE"
    WEB = "WEB"

class PromptCategory(str, Enum):
    tofu = "tofu"
    mofu = "mofu"
    bofu = "bofu"
