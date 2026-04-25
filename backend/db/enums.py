import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class OrgType(str, enum.Enum):
    university = "university"
    volunteer = "volunteer"
    youth_center = "youth_center"


class PostType(str, enum.Enum):
    event_announcement = "event_announcement"
    event_result = "event_result"
    vacancy = "vacancy"
    grant = "grant"
    news = "news"
    poll = "poll"
    other = "other"


class PostStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"


class ModuleType(str, enum.Enum):
    events = "events"
    volunteer = "volunteer"


class Platform(str, enum.Enum):
    vk = "vk"
    telegram = "telegram"


class EventSource(str, enum.Enum):
    google_calendar = "google_calendar"
    manual = "manual"


class SystemStateEnum(str, enum.Enum):
    normal = "normal"
    growth = "growth"
    crisis = "crisis"