import enum 

class UserRole(enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class OrgType(enum.Enum):
    university = "university"
    volunteer = "volunteer"
    youth_center = "youth_center"


class PostType(enum.Enum):
    event_announcement = "event_announcement"
    event_result = "event_result"
    vacancy = "vacancy"
    grant = "grant"
    news = "news"
    poll = "poll"
    other = "other"


class PostStatus(enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"


class ModuleType(enum.Enum):
    events = "events"
    volunteer = "volunteer"


class Platform(enum.Enum):
    vk = "vk"
    telegram = "telegram"


class EventSource(enum.Enum):
    google_calendar = "google_calendar"
    manual = "manual"


class SystemStateEnum(enum.Enum):
    normal = "normal"
    growth = "growth"
    crisis = "crisis"