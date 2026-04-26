import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { llmGenerate, vkDeletePost, vkPoster, vkUploadPhoto } from "./api";

type AuthMode = "login" | "register";
type User = {
  email: string;
  passwordHash?: string;
  passwordSalt?: string;
  password?: string;
  createdAt: string;
};
type MessageType = "success" | "error" | "idle";
type GuardEntry = { fails: number; lockedUntil: number };
type VerificationEntry = {
  email: string;
  codeHash: string;
  salt: string;
  expiresAt: number;
  verified: boolean;
};
type CalendarView = "month" | "week" | "day";
type AppTab = "home" | "calendar" | "content" | "report";
type EventStatus = "draft" | "scheduled" | "published";
type ThemeMode = "dark-red" | "light-blue";
type CalendarEvent = {
  id: string;
  title: string;
  date: string;
  startTime: string;
  endTime: string;
  description: string;
  status: EventStatus;
  platforms: string[];
};

/** События/посты с промптом и ИИ — отдельно от календаря */
type ContentEvent = {
  id: string;
  title: string;
  prompt: string;
  tone: string;
  generatedText: string;
  attachmentName?: string;
  attachmentDataUrl?: string;
  createdAt: string;
  /** Ссылка на пост, если публикация в VK прошла успешно */
  vkWallUrl?: string;
  vkPostId?: number;
  vkPublishError?: string;
};

const USERS_KEY = "protechno_users";
const AUTH_GUARD_KEY = "protechno_auth_guard";
const SESSION_KEY = "protechno_session";
const EMAIL_VERIFY_KEY = "protechno_email_verify";
const EVENTS_KEY = "protechno_events";
const CONTENT_EVENTS_KEY = "protechno_content_events";
const THEME_KEY = "protechno_theme";
const MAX_ATTEMPTS = 5;
const LOCK_TIME_MS = 60_000;
const CODE_EXPIRE_MS = 10 * 60_000;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const WEEK_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const EMAILJS_SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID as string | undefined;
const EMAILJS_TEMPLATE_ID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID as string | undefined;
const EMAILJS_PUBLIC_KEY = import.meta.env.VITE_EMAILJS_PUBLIC_KEY as string | undefined;
const INTRO_LINES = [
  "Пустоши не прощают слабых.",
  "Скорость решает. Команда выживает.",
  "Каждый пост - как выстрел в цель.",
];
const MAX_ATTACHMENT_BYTES = 220 * 1024;
/** Длительность заставки до начала скрытия (мс): быстро, но не резко */
const INTRO_SPLASH_MS = 2800;
const VK_MESSAGE_MAX = 3900;

function readFileAsDataURL(file: File, maxBytes: number): Promise<string> {
  return new Promise((resolve, reject) => {
    if (file.size > maxBytes) {
      reject(new Error(`Файл больше ${Math.round(maxBytes / 1024)} КБ`));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Не удалось прочитать файл"));
    reader.readAsDataURL(file);
  });
}

/**
 * Восстанавливает File из base64 data URL (используется при повторной
 * публикации сохранённого события: оригинальный File теряется, в state
 * остаётся только attachmentDataUrl).
 */
function dataUrlToFile(dataUrl: string, filename: string): File | null {
  try {
    const [header, base64] = dataUrl.split(",");
    if (!header || !base64) return null;
    const mimeMatch = header.match(/data:([^;]+);base64/i);
    const mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    const safeName = filename && /\.[a-z0-9]+$/i.test(filename)
      ? filename
      : `${filename || "photo"}.${mime.split("/")[1] || "jpg"}`;
    return new File([bytes], safeName, { type: mime });
  } catch {
    return null;
  }
}

const readUsers = (): User[] => {
  const raw = localStorage.getItem(USERS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as User[];
  } catch {
    return [];
  }
};

const saveUsers = (users: User[]) => {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
};

const readGuard = (): Record<string, GuardEntry> => {
  const raw = localStorage.getItem(AUTH_GUARD_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, GuardEntry>;
  } catch {
    return {};
  }
};

const saveGuard = (value: Record<string, GuardEntry>) => {
  localStorage.setItem(AUTH_GUARD_KEY, JSON.stringify(value));
};

const readVerification = (): Record<string, VerificationEntry> => {
  const raw = localStorage.getItem(EMAIL_VERIFY_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, VerificationEntry>;
  } catch {
    return {};
  }
};

const saveVerification = (value: Record<string, VerificationEntry>) => {
  localStorage.setItem(EMAIL_VERIFY_KEY, JSON.stringify(value));
};

const readEvents = (): CalendarEvent[] => {
  const raw = localStorage.getItem(EVENTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as CalendarEvent[];
  } catch {
    return [];
  }
};

const saveEvents = (events: CalendarEvent[]) => {
  localStorage.setItem(EVENTS_KEY, JSON.stringify(events));
};

const readContentEvents = (): ContentEvent[] => {
  const raw = localStorage.getItem(CONTENT_EVENTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as ContentEvent[];
  } catch {
    return [];
  }
};

const saveContentEvents = (items: ContentEvent[]) => {
  localStorage.setItem(CONTENT_EVENTS_KEY, JSON.stringify(items));
};

const passwordRules = (pass: string) => ({
  minLength: pass.length >= 8,
  upper: /[A-ZА-Я]/.test(pass),
  lower: /[a-zа-я]/.test(pass),
  digit: /\d/.test(pass),
  special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pass),
});

const passwordStrength = (pass: string): { label: string; score: number } => {
  const rules = passwordRules(pass);
  const score = Object.values(rules).filter(Boolean).length;
  if (score <= 2) return { label: "Слабый", score };
  if (score <= 4) return { label: "Средний", score };
  return { label: "Надёжный", score };
};

const toHex = (buffer: ArrayBuffer): string =>
  [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");

const randomSalt = (): string => {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return toHex(bytes.buffer);
};

const hashPassword = async (password: string, salt: string): Promise<string> => {
  const data = new TextEncoder().encode(`${salt}:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return toHex(digest);
};

const generateCode = (): string => String(Math.floor(100000 + Math.random() * 900000));

const toInputDate = (date: Date): string => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const parseInputDate = (value: string): Date => {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
};

const startOfWeek = (date: Date): Date => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
};

const statusLabel: Record<EventStatus, string> = {
  draft: "Черновик",
  scheduled: "Запланирован",
  published: "Опубликован",
};

const toCalendarDateRange = (date: string, time: string, durationMin: number) => {
  const [year, month, day] = date.split("-").map(Number);
  const [hours, minutes] = time.split(":").map(Number);
  const start = new Date(Date.UTC(year, month - 1, day, hours, minutes));
  const end = new Date(start.getTime() + durationMin * 60 * 1000);

  const fmt = (d: Date) =>
    `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(
      d.getUTCDate()
    ).padStart(2, "0")}T${String(d.getUTCHours()).padStart(2, "0")}${String(
      d.getUTCMinutes()
    ).padStart(2, "0")}00Z`;

  return `${fmt(start)}/${fmt(end)}`;
};

const buildCalendarUrl = (title: string, date: string, time: string, duration: number) => {
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: title,
    dates: toCalendarDateRange(date, time, duration),
    details: "Событие создано в медиахабе команды Безумный MAX",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
};

const canSendRealEmail = (): boolean =>
  Boolean(EMAILJS_SERVICE_ID && EMAILJS_TEMPLATE_ID && EMAILJS_PUBLIC_KEY);

const sendCodeByEmail = async (email: string, code: string): Promise<void> => {
  const response = await fetch("https://api.emailjs.com/api/v1.0/email/send", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      service_id: EMAILJS_SERVICE_ID,
      template_id: EMAILJS_TEMPLATE_ID,
      user_id: EMAILJS_PUBLIC_KEY,
      template_params: {
        to_email: email,
        passcode: code,
        project_name: "Безумный MAX · Медиахаб",
      },
    }),
  });

  if (!response.ok) {
    throw new Error("EMAIL_SEND_FAILED");
  }
};

function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [introStep, setIntroStep] = useState(1);
  const [activeTab, setActiveTab] = useState<AppTab>("home");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [calendarModalOpen, setCalendarModalOpen] = useState(false);
  const [calendarView, setCalendarView] = useState<CalendarView>("month");
  const [calendarDate, setCalendarDate] = useState<Date>(new Date());
  const [selectedDay, setSelectedDay] = useState<string>(toInputDate(new Date()));
  const [events, setEvents] = useState<CalendarEvent[]>(() => readEvents());
  const [contentEvents, setContentEvents] = useState<ContentEvent[]>(() => readContentEvents());
  const [contentMessage, setContentMessage] = useState("");
  const [contentMessageType, setContentMessageType] = useState<MessageType>("idle");
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [verificationCode, setVerificationCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [codeVerified, setCodeVerified] = useState(false);
  const [codeDebugHint, setCodeDebugHint] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [authMessageType, setAuthMessageType] = useState<MessageType>("idle");
  const [authLoading, setAuthLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<string>(() => {
    return localStorage.getItem(SESSION_KEY) ?? sessionStorage.getItem(SESSION_KEY) ?? "";
  });
  const [eventTitle, setEventTitle] = useState("Планёрка медиакоманды");
  const [eventDate, setEventDate] = useState("");
  const [eventTime, setEventTime] = useState("10:00");
  const [duration, setDuration] = useState(60);
  const [eventDescription, setEventDescription] = useState("Событие медиахаба");
  const [eventStatus, setEventStatus] = useState<EventStatus>("scheduled");
  const [eventPlatforms, setEventPlatforms] = useState<string[]>(["VK", "Telegram"]);
  const [calendarMessage, setCalendarMessage] = useState("");
  const [calendarMessageType, setCalendarMessageType] = useState<MessageType>("idle");
  const [smartEventOpen, setSmartEventOpen] = useState(false);
  const [smartTitle, setSmartTitle] = useState("");
  const [smartPrompt, setSmartPrompt] = useState("");
  const [smartTone, setSmartTone] = useState("");
  const [smartGenerated, setSmartGenerated] = useState("");
  const [smartLlmLoading, setSmartLlmLoading] = useState(false);
  const [smartMessage, setSmartMessage] = useState("");
  const [smartMessageType, setSmartMessageType] = useState<MessageType>("idle");
  const [smartImageFile, setSmartImageFile] = useState<File | null>(null);
  const [smartImagePreview, setSmartImagePreview] = useState<string | null>(null);
  const smartFileInputRef = useRef<HTMLInputElement | null>(null);
  const [publishToVk, setPublishToVk] = useState(false);
  const [vkPublishing, setVkPublishing] = useState(false);
  const [publishingItemId, setPublishingItemId] = useState<string | null>(null);
  const [deletingVkItemId, setDeletingVkItemId] = useState<string | null>(null);
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light-blue" ? "light-blue" : "dark-red";
  });
  const [themeToggleMode, setThemeToggleMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light-blue" ? "light-blue" : "dark-red";
  });
  const [reportOpen, setReportOpen] = useState(false);
  const [reportText, setReportText] = useState("");
  const [reportMessage, setReportMessage] = useState("");
  const [reportMessageType, setReportMessageType] = useState<MessageType>("idle");
  const [themeAnimating, setThemeAnimating] = useState(false);
  const [themeSwitching, setThemeSwitching] = useState(false);
  const introFinishedRef = useRef(false);
  const villagerAudioRef = useRef<HTMLAudioElement | null>(null);
  const themeTimersRef = useRef<number[]>([]);

  const authTitle = useMemo(
    () => (authMode === "login" ? "Вход" : "Регистрация"),
    [authMode]
  );

  const handleAuthSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();

    if (!normalizedEmail || !trimmedPassword || (authMode === "register" && !confirmPassword)) {
      setAuthMessageType("error");
      setAuthMessage("Пожалуйста, заполните все поля.");
      return;
    }
    if (!EMAIL_REGEX.test(normalizedEmail)) {
      setAuthMessageType("error");
      setAuthMessage("Введите корректный e-mail.");
      return;
    }

    setAuthLoading(true);
    try {
      const users = readUsers();
      const existing = users.find((user) => user.email === normalizedEmail);

      if (authMode === "register") {
        const rules = passwordRules(trimmedPassword);
        if (!Object.values(rules).every(Boolean)) {
          setAuthMessageType("error");
          setAuthMessage("Пароль не соответствует требованиям безопасности.");
          return;
        }
        if (trimmedPassword !== confirmPassword.trim()) {
          setAuthMessageType("error");
          setAuthMessage("Пароли не совпадают.");
          return;
        }
        if (existing) {
          setAuthMessageType("error");
          setAuthMessage("Эта почта уже зарегистрирована.");
          return;
        }
        const verifications = readVerification();
        const verifyEntry = verifications[normalizedEmail];
        if (!verifyEntry?.verified || verifyEntry.expiresAt < Date.now()) {
          setAuthMessageType("error");
          setAuthMessage("Подтвердите e-mail кодом из письма.");
          return;
        }

        const salt = randomSalt();
        const hash = await hashPassword(trimmedPassword, salt);
        users.push({
          email: normalizedEmail,
          passwordSalt: salt,
          passwordHash: hash,
          createdAt: new Date().toISOString(),
        });
        saveUsers(users);
        delete verifications[normalizedEmail];
        saveVerification(verifications);
        setAuthMessageType("success");
        setAuthMessage("Аккаунт успешно создан. Теперь войдите в систему.");
        setAuthMode("login");
        setPassword("");
        setConfirmPassword("");
        setVerificationCode("");
        setCodeSent(false);
        setCodeVerified(false);
        setCodeDebugHint("");
        return;
      }

      const guard = readGuard();
      const entry = guard[normalizedEmail];
      if (entry?.lockedUntil && entry.lockedUntil > Date.now()) {
        const seconds = Math.ceil((entry.lockedUntil - Date.now()) / 1000);
        setAuthMessageType("error");
        setAuthMessage(`Слишком много попыток. Повторите через ${seconds} сек.`);
        return;
      }

      if (!existing) {
        guard[normalizedEmail] = {
          fails: (entry?.fails ?? 0) + 1,
          lockedUntil:
            (entry?.fails ?? 0) + 1 >= MAX_ATTEMPTS ? Date.now() + LOCK_TIME_MS : entry?.lockedUntil ?? 0,
        };
        saveGuard(guard);
        setAuthMessageType("error");
        setAuthMessage("Неверная почта или пароль.");
        return;
      }

      let isValid = false;
      if (existing.passwordHash && existing.passwordSalt) {
        const candidateHash = await hashPassword(trimmedPassword, existing.passwordSalt);
        isValid = candidateHash === existing.passwordHash;
      } else if (existing.password) {
        // Миграция с устаревшего формата хранения в localStorage.
        isValid = trimmedPassword === existing.password;
        if (isValid) {
          const salt = randomSalt();
          existing.passwordSalt = salt;
          existing.passwordHash = await hashPassword(trimmedPassword, salt);
          delete existing.password;
          saveUsers(users);
        }
      }

      if (!isValid) {
        const fails = (entry?.fails ?? 0) + 1;
        guard[normalizedEmail] = {
          fails,
          lockedUntil: fails >= MAX_ATTEMPTS ? Date.now() + LOCK_TIME_MS : 0,
        };
        saveGuard(guard);
        setAuthMessageType("error");
        setAuthMessage(
          fails >= MAX_ATTEMPTS
            ? "Аккаунт временно заблокирован на 60 секунд."
            : `Неверный пароль. Осталось попыток: ${MAX_ATTEMPTS - fails}.`
        );
        return;
      }

      delete guard[normalizedEmail];
      saveGuard(guard);

      if (rememberMe) {
        localStorage.setItem(SESSION_KEY, normalizedEmail);
        sessionStorage.removeItem(SESSION_KEY);
      } else {
        sessionStorage.setItem(SESSION_KEY, normalizedEmail);
        localStorage.removeItem(SESSION_KEY);
      }
      setCurrentUser(normalizedEmail);
      setAuthMessageType("success");
      setAuthMessage("Вход выполнен успешно. Добро пожаловать!");
      setAuthModalOpen(false);
      setPassword("");
      setConfirmPassword("");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleCalendarSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!eventTitle.trim() || !eventDate || !eventTime || duration < 15) {
      setCalendarMessageType("error");
      setCalendarMessage("Введите корректные данные события.");
      return;
    }
    const title = eventTitle.trim();
    const startTime = eventTime;
    const start = new Date(`${eventDate}T${startTime}:00`);
    const end = new Date(start.getTime() + duration * 60_000);
    const endTime = `${String(end.getHours()).padStart(2, "0")}:${String(end.getMinutes()).padStart(2, "0")}`;

    const newEvent: CalendarEvent = {
      id: editingEventId ?? crypto.randomUUID(),
      title,
      date: eventDate,
      startTime,
      endTime,
      description: eventDescription.trim() || "Событие медиахаба",
      status: eventStatus,
      platforms: eventPlatforms.length ? eventPlatforms : ["VK"],
    };
    const nextEvents = editingEventId
      ? events.map((ev) => (ev.id === editingEventId ? newEvent : ev))
      : [...events, newEvent];
    nextEvents.sort((a, b) => (a.date + a.startTime).localeCompare(b.date + b.startTime));
    setEvents(nextEvents);
    saveEvents(nextEvents);

    const url = buildCalendarUrl(title, eventDate, eventTime, duration);
    window.open(url, "_blank", "noopener,noreferrer");
    setCalendarMessageType("success");
    setCalendarMessage(editingEventId ? "Событие обновлено и открыто в календаре." : "Событие создано и открыто в календаре.");
    setCalendarModalOpen(false);
    setEditingEventId(null);
  };

  const removeEvent = (id: string) => {
    const next = events.filter((ev) => ev.id !== id);
    setEvents(next);
    saveEvents(next);
  };

  const openCreateEvent = (date?: string) => {
    setEditingEventId(null);
    const chosenDate = date ?? selectedDay ?? toInputDate(new Date());
    setEventDate(chosenDate);
    setEventTime("10:00");
    setDuration(60);
    setEventTitle("Новое событие");
    setEventDescription("Событие медиахаба");
    setEventStatus("scheduled");
    setEventPlatforms(["VK", "Telegram"]);
    setCalendarModalOpen(true);
  };

  const openEditEvent = (ev: CalendarEvent) => {
    setEditingEventId(ev.id);
    setEventTitle(ev.title);
    setEventDate(ev.date);
    setEventTime(ev.startTime);
    const [sh, sm] = ev.startTime.split(":").map(Number);
    const [eh, em] = ev.endTime.split(":").map(Number);
    setDuration((eh * 60 + em) - (sh * 60 + sm));
    setEventDescription(ev.description);
    setEventStatus(ev.status);
    setEventPlatforms(ev.platforms);
    setCalendarModalOpen(true);
  };

  const openSmartEvent = () => {
    setSmartTitle("");
    setSmartPrompt("");
    setSmartTone("");
    setSmartGenerated("");
    setSmartMessage("");
    setSmartMessageType("idle");
    setSmartImageFile(null);
    setSmartImagePreview(null);
    setPublishToVk(false);
    setVkPublishing(false);
    if (smartFileInputRef.current) smartFileInputRef.current.value = "";
    setSmartEventOpen(true);
  };

  const removeContentEvent = (id: string) => {
    const next = contentEvents.filter((c) => c.id !== id);
    setContentEvents(next);
    saveContentEvents(next);
  };

  const updateContentEvents = (updater: (prev: ContentEvent[]) => ContentEvent[]) => {
    setContentEvents((prev) => {
      const next = updater(prev);
      saveContentEvents(next);
      return next;
    });
  };

  const closeSmartEvent = () => {
    setSmartEventOpen(false);
    setSmartLlmLoading(false);
    setVkPublishing(false);
  };

  const handleSmartImagePick = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setSmartMessageType("error");
      setSmartMessage("Нужен файл изображения.");
      return;
    }
    try {
      const url = await readFileAsDataURL(file, MAX_ATTACHMENT_BYTES);
      setSmartImageFile(file);
      setSmartImagePreview(url);
      setSmartMessageType("idle");
      setSmartMessage("");
    } catch (err) {
      setSmartMessageType("error");
      setSmartMessage(err instanceof Error ? err.message : "Ошибка файла");
      setSmartImageFile(null);
      setSmartImagePreview(null);
    }
  };

  const clearSmartImage = () => {
    setSmartImageFile(null);
    setSmartImagePreview(null);
    if (smartFileInputRef.current) smartFileInputRef.current.value = "";
  };

  const handleSmartGenerate = async () => {
    const parts: string[] = [];
    if (smartTitle.trim()) parts.push(`Название события: ${smartTitle.trim()}`);
    if (smartPrompt.trim()) parts.push(`Задание (промпт): ${smartPrompt.trim()}`);
    if (smartTone.trim()) parts.push(`Тон и стиль: ${smartTone.trim()}`);
    const query = parts.join("\n");
    if (!smartPrompt.trim() && !smartTitle.trim()) {
      setSmartMessageType("error");
      setSmartMessage("Укажите название или промпт для генерации.");
      return;
    }
    setSmartLlmLoading(true);
    setSmartMessage("");
    try {
      const res = await llmGenerate(query);
      setSmartGenerated(res.text);
      setSmartMessageType("success");
      setSmartMessage(`Сгенерировано (${res.model}, шагов: ${res.shots_used})`);
    } catch (err) {
      const fallback = [smartTitle.trim(), smartPrompt.trim()].filter(Boolean).join("\n\n");
      if (fallback) {
        setSmartGenerated(fallback);
      }
      setSmartMessageType("error");
      setSmartMessage(
        err instanceof Error
          ? `${err.message}. Подставлен черновик без LLM.`
          : "Ошибка LLM. Подставлен черновик без LLM."
      );
    } finally {
      setSmartLlmLoading(false);
    }
  };

  const publishContentEventToVk = async (
    item: ContentEvent,
    imageFile?: File | null,
  ): Promise<{ url: string; postId: number }> => {
    const body = item.generatedText.trim() || item.prompt.trim();
    const text = body ? `${item.title}\n\n${body}` : item.title;
    const message = text.slice(0, VK_MESSAGE_MAX);
    if (!message.trim()) {
      throw new Error("Пустой текст для VK.");
    }
    let attachments: string | null = null;
    if (imageFile) {
      attachments = await vkUploadPhoto(imageFile);
    }
    const vk = await vkPoster({ message, attachments, from_group: true });
    return { url: vk.url, postId: vk.post_id };
  };

  const handleSmartSubmit = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!smartTitle.trim()) {
      setSmartMessageType("error");
      setSmartMessage("Укажите название.");
      return;
    }
    const generatedText = (smartGenerated.trim() || smartPrompt.trim() || "").slice(0, 12_000);
    const newItem: ContentEvent = {
      id: crypto.randomUUID(),
      title: smartTitle.trim(),
      prompt: smartPrompt.trim(),
      tone: smartTone.trim(),
      generatedText,
      attachmentName: smartImageFile?.name ?? undefined,
      attachmentDataUrl: smartImagePreview ?? undefined,
      createdAt: new Date().toISOString(),
    };
    updateContentEvents((prev) => [newItem, ...prev]);

    if (publishToVk) {
      setVkPublishing(true);
      setSmartMessageType("idle");
      setSmartMessage("");
      try {
        const vk = await publishContentEventToVk(newItem, smartImageFile);
        updateContentEvents((prev) =>
          prev.map((e) =>
            e.id === newItem.id ? { ...e, vkWallUrl: vk.url, vkPostId: vk.postId, vkPublishError: undefined } : e
          )
        );
        setContentMessageType("success");
        setContentMessage("Сохранено и опубликовано в VK.");
      } catch (err) {
        const errorText =
          err instanceof Error ? err.message : "Ошибка VK (проверьте бэкенд: токен, группа, proxy).";
        updateContentEvents((prev) =>
          prev.map((e) => (e.id === newItem.id ? { ...e, vkPublishError: errorText } : e))
        );
        setContentMessageType("error");
        setContentMessage(`Сохранено, но VK не опубликовал: ${errorText}`);
      }
      setVkPublishing(false);
    } else {
      setContentMessageType("success");
      setContentMessage("Событие сохранено.");
    }

    setActiveTab("content");
    closeSmartEvent();
  };

  const republishContentEvent = async (id: string) => {
    const target = contentEvents.find((item) => item.id === id);
    if (!target) return;
    setPublishingItemId(id);
    try {
      // Восстанавливаем File из data URL — иначе при повторной публикации
      // фото теряется и в VK уходит только текст.
      const imageFile = target.attachmentDataUrl
        ? dataUrlToFile(target.attachmentDataUrl, target.attachmentName ?? "photo.jpg")
        : null;
      const vk = await publishContentEventToVk(target, imageFile);
      updateContentEvents((prev) =>
        prev.map((item) =>
          item.id === id ? { ...item, vkWallUrl: vk.url, vkPostId: vk.postId, vkPublishError: undefined } : item
        )
      );
      setContentMessageType("success");
      setContentMessage("Пост опубликован в VK.");
    } catch (err) {
      const errorText =
        err instanceof Error ? err.message : "Ошибка VK (проверьте бэкенд: токен, группа, proxy).";
      updateContentEvents((prev) =>
        prev.map((item) => (item.id === id ? { ...item, vkPublishError: errorText } : item))
      );
      setContentMessageType("error");
      setContentMessage(`Не удалось опубликовать в VK: ${errorText}`);
    } finally {
      setPublishingItemId(null);
    }
  };

  const deleteVkPostForContent = async (id: string) => {
    const target = contentEvents.find((item) => item.id === id);
    if (!target || !target.vkPostId) {
      setContentMessageType("error");
      setContentMessage("Не найден post_id для удаления в VK.");
      return;
    }
    setDeletingVkItemId(id);
    try {
      const res = await vkDeletePost(target.vkPostId);
      if (!res.success) {
        throw new Error("VK вернул неуспешный результат удаления.");
      }
      updateContentEvents((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, vkWallUrl: undefined, vkPostId: undefined, vkPublishError: undefined }
            : item
        )
      );
      setContentMessageType("success");
      setContentMessage("Пост удалён из VK.");
    } catch (err) {
      setContentMessageType("error");
      setContentMessage(err instanceof Error ? err.message : "Не удалось удалить пост в VK.");
    } finally {
      setDeletingVkItemId(null);
    }
  };

  const buildContentReport = (items: ContentEvent[]): string => {
    const now = new Date().toLocaleString("ru-RU");
    const total = items.length;
    const vkPublished = items.filter((i) => i.vkWallUrl).length;
    const lines = items.slice(0, 20).map((item, idx) => {
      const stamp = new Date(item.createdAt).toLocaleString("ru-RU");
      const text = (item.generatedText || item.prompt || "Нет текста").replace(/\s+/g, " ").trim();
      const shortText = text.length > 220 ? `${text.slice(0, 220)}...` : text;
      return `${idx + 1}. ${item.title}\n   Дата: ${stamp}\n   VK: ${
        item.vkWallUrl ? item.vkWallUrl : "не опубликовано"
      }\n   Текст: ${shortText}`;
    });
    return [
      "ОТЧЕТ ПО КОНТЕНТУ",
      `Сформировано: ${now}`,
      `Всего записей: ${total}`,
      `Опубликовано в VK: ${vkPublished}`,
      "",
      "КЛЮЧЕВЫЕ ЗАПИСИ:",
      lines.length ? lines.join("\n\n") : "Нет данных для отчета.",
    ].join("\n");
  };

  const openReportModal = () => {
    const nextReport = buildContentReport(contentEvents);
    setReportText(nextReport);
    setReportMessage("");
    setReportMessageType("idle");
    setReportOpen(true);
  };

  const downloadReport = () => {
    const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `content-report-${stamp}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    setReportMessageType("success");
    setReportMessage("Отчет скачан.");
  };

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(reportText);
      setReportMessageType("success");
      setReportMessage("Отчет скопирован в буфер.");
    } catch {
      setReportMessageType("error");
      setReportMessage("Не удалось скопировать отчет.");
    }
  };

  const playVillagerSound = () => {
    const audio = villagerAudioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    void audio.play().catch(() => {
      // Если браузер блокирует звук, просто игнорируем ошибку.
    });
  };

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode);
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setVerificationCode("");
    setCodeSent(false);
    setCodeVerified(false);
    setCodeDebugHint("");
    setAuthMessage("");
    setAuthMessageType("idle");
    setAuthModalOpen(true);
  };

  const finishIntro = () => {
    if (introFinishedRef.current) return;
    introFinishedRef.current = true;
    setShowIntro(false);
    // После заставки сразу показываем авторизацию только для гостя.
    if (!currentUser) {
      openAuth("login");
    }
  };

  const logout = () => {
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(SESSION_KEY);
    setCurrentUser("");
  };

  const passStrength = useMemo(() => passwordStrength(password), [password]);
  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const ev of events) {
      const list = map.get(ev.date) ?? [];
      list.push(ev);
      map.set(ev.date, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.startTime.localeCompare(b.startTime));
    }
    return map;
  }, [events]);

  const monthCells = useMemo(() => {
    const first = new Date(calendarDate.getFullYear(), calendarDate.getMonth(), 1);
    const start = startOfWeek(first);
    const cells: Date[] = [];
    for (let i = 0; i < 42; i += 1) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      cells.push(d);
    }
    return cells;
  }, [calendarDate]);

  const weekDays = useMemo(() => {
    const start = startOfWeek(calendarDate);
    return Array.from({ length: 7 }, (_, idx) => {
      const d = new Date(start);
      d.setDate(start.getDate() + idx);
      return d;
    });
  }, [calendarDate]);

  const periodLabel = useMemo(() => {
    if (calendarView === "month") {
      return calendarDate.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
    }
    if (calendarView === "week") {
      const start = weekDays[0];
      const end = weekDays[6];
      return `${start.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })} - ${end.toLocaleDateString(
        "ru-RU",
        { day: "numeric", month: "short", year: "numeric" }
      )}`;
    }
    return parseInputDate(selectedDay).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }, [calendarDate, calendarView, selectedDay, weekDays]);

  const selectedEvents = eventsByDate.get(selectedDay) ?? [];

  const shiftPeriod = (dir: 1 | -1) => {
    const d = new Date(calendarDate);
    if (calendarView === "month") d.setMonth(d.getMonth() + dir);
    else if (calendarView === "week") d.setDate(d.getDate() + 7 * dir);
    else d.setDate(d.getDate() + dir);
    setCalendarDate(d);
    setSelectedDay(toInputDate(d));
  };

  const sendVerificationCode = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!EMAIL_REGEX.test(normalizedEmail)) {
      setAuthMessageType("error");
      setAuthMessage("Сначала укажите корректный e-mail.");
      return;
    }

    const users = readUsers();
    if (users.some((u) => u.email === normalizedEmail)) {
      setAuthMessageType("error");
      setAuthMessage("Эта почта уже зарегистрирована.");
      return;
    }

    setAuthLoading(true);
    try {
      const code = generateCode();
      const salt = randomSalt();
      const codeHash = await hashPassword(code, salt);
      const verifications = readVerification();
      verifications[normalizedEmail] = {
        email: normalizedEmail,
        codeHash,
        salt,
        expiresAt: Date.now() + CODE_EXPIRE_MS,
        verified: false,
      };
      saveVerification(verifications);

      if (canSendRealEmail()) {
        await sendCodeByEmail(normalizedEmail, code);
        setCodeDebugHint("");
        setAuthMessageType("success");
        setAuthMessage("Код отправлен на почту. Проверьте входящие и спам.");
      } else {
        // Режим без backend/почтового шлюза: код показывается для локального теста.
        setCodeDebugHint(`Тестовый код: ${code}`);
        setAuthMessageType("success");
        setAuthMessage(
          "Почтовый шлюз не настроен. Для демо используйте тестовый код ниже."
        );
      }

      setCodeSent(true);
      setCodeVerified(false);
      setVerificationCode("");
    } catch {
      setAuthMessageType("error");
      setAuthMessage("Ошибка отправки письма. Повторите попытку или проверьте настройки EmailJS.");
    } finally {
      setAuthLoading(false);
    }
  };

  const verifyCode = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    const inputCode = verificationCode.trim();
    if (!inputCode) {
      setAuthMessageType("error");
      setAuthMessage("Введите код из письма.");
      return;
    }

    const verifications = readVerification();
    const entry = verifications[normalizedEmail];
    if (!entry) {
      setAuthMessageType("error");
      setAuthMessage("Сначала отправьте код подтверждения.");
      return;
    }
    if (entry.expiresAt < Date.now()) {
      setAuthMessageType("error");
      setAuthMessage("Код истёк. Отправьте новый код.");
      return;
    }

    const hash = await hashPassword(inputCode, entry.salt);
    if (hash !== entry.codeHash) {
      setAuthMessageType("error");
      setAuthMessage("Неверный код подтверждения.");
      return;
    }

    entry.verified = true;
    verifications[normalizedEmail] = entry;
    saveVerification(verifications);
    setCodeVerified(true);
    setAuthMessageType("success");
    setAuthMessage("Почта подтверждена. Теперь завершите регистрацию.");
  };

  useEffect(() => {
    // Один проход короткой заставки: строки → логотип, без привязки к introStep.
    const lineMs = Math.round(INTRO_SPLASH_MS / 4);
    const t1 = window.setTimeout(() => setIntroStep(2), lineMs);
    const t2 = window.setTimeout(() => setIntroStep(3), lineMs * 2);
    const t3 = window.setTimeout(() => setIntroStep(4), lineMs * 3);
    const t4 = window.setTimeout(() => finishIntro(), INTRO_SPLASH_MS);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
      window.clearTimeout(t4);
    };
  }, [currentUser]);

  useEffect(() => {
    const hardStop = window.setTimeout(() => finishIntro(), INTRO_SPLASH_MS + 1500);
    return () => window.clearTimeout(hardStop);
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    setThemeAnimating(true);
    const t = window.setTimeout(() => setThemeAnimating(false), 520);
    return () => window.clearTimeout(t);
  }, [themeMode]);

  useEffect(
    () => () => {
      themeTimersRef.current.forEach((id) => window.clearTimeout(id));
      themeTimersRef.current = [];
    },
    []
  );

  const handleThemeToggle = () => {
    if (themeSwitching) return;
    const nextTheme: ThemeMode = themeToggleMode === "dark-red" ? "light-blue" : "dark-red";
    themeTimersRef.current.forEach((id) => window.clearTimeout(id));
    themeTimersRef.current = [];
    setThemeSwitching(true);
    // 1) Сначала двигаем шарик переключателя.
    setThemeToggleMode(nextTheme);
    // 2) Затем в середине движения меняем тему интерфейса.
    const applyThemeId = window.setTimeout(() => setThemeMode(nextTheme), 210);
    const finishSwitchId = window.setTimeout(() => setThemeSwitching(false), 520);
    themeTimersRef.current.push(applyThemeId, finishSwitchId);
  };

  return (
    <div className={`page theme-${themeMode} ${themeAnimating ? "theme-animating" : ""}`}>
      <AnimatePresence>
        {showIntro && (
          <motion.div
            className="intro-overlay"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.6 } }}
          >
            <button type="button" className="intro-skip-btn" onClick={finishIntro}>
              Пропустить
            </button>
            <div className="intro-sequence">
              <AnimatePresence mode="wait">
                {introStep < 4 ? (
                  <motion.p
                    key={`line-${introStep}`}
                    className="intro-line"
                    initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
                    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                    exit={{ opacity: 0, y: -16, filter: "blur(3px)" }}
                    transition={{ duration: 0.55 }}
                  >
                    {INTRO_LINES[introStep - 1]}
                  </motion.p>
                ) : (
                  <motion.div
                    key="logo"
                    className="intro-title"
                    initial={{ letterSpacing: "0.34em", opacity: 0, scale: 1.04 }}
                    animate={{ letterSpacing: "0.14em", opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, y: -16 }}
                    transition={{ duration: 0.6 }}
                  >
                    БЕЗУМНЫЙ MAX
                  </motion.div>
                )}
              </AnimatePresence>
              <motion.div
                className="intro-sub"
                initial={{ opacity: 0 }}
                animate={{ opacity: introStep >= 3 ? 1 : 0 }}
              >
                медиахаб
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="cinema-noise" />
      <div className="cinema-lines" />
      <div className="site-haze" />
      <div className="glow glow-top" />
      <div className="glow glow-bottom" />

      <header className="container header">
        <a className="logo" href="#">
          Безумный <span>MAX</span>
        </a>
        <div className="top-tabs">
          <button
            className={`tiny-btn ${activeTab === "home" ? "active" : ""}`}
            onClick={() => setActiveTab("home")}
          >
            Главная
          </button>
          <button
            className={`tiny-btn ${activeTab === "calendar" ? "active" : ""}`}
            onClick={() => setActiveTab("calendar")}
          >
            Календарь
          </button>
          <button
            className={`tiny-btn ${activeTab === "content" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveTab("content")}
          >
            Контент
          </button>
          <button
            className={`tiny-btn ${activeTab === "report" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveTab("report")}
          >
            Отчет
          </button>
          <button
            className={`theme-toggle ${themeToggleMode === "light-blue" ? "light" : "dark"} ${
              themeSwitching ? "switching" : ""
            } has-tooltip`}
            type="button"
            onClick={handleThemeToggle}
            aria-label="Переключить тему"
            data-tooltip={themeMode === "dark-red" ? "Переключить на светло-голубую" : "Переключить на темно-красную"}
          >
            <span className="theme-toggle-track" />
            <span className="theme-toggle-thumb" />
            <span className="theme-toggle-label">{themeMode === "dark-red" ? "Dark Red" : "Light Blue"}</span>
          </button>
        </div>
        {currentUser ? (
          <div className="auth-chip-wrap">
            <span className="auth-chip has-tooltip" data-tooltip={currentUser}>
              {currentUser}
            </span>
            <button className="btn btn-outline" onClick={logout}>
              Выйти
            </button>
          </div>
        ) : (
          <button className="btn btn-outline" onClick={() => openAuth("login")}>
            Войти
          </button>
        )}
      </header>

      <main className="container main">
        {authModalOpen && (
          <motion.section
            className="auth-screen"
            initial={{ opacity: 0, y: 16, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.35 }}
          >
            <div className="auth-screen-bg" />
            <div className="auth-layout">
              <aside className="auth-value">
                <p className="badge">Безумный MAX</p>
                <h2 className="auth-value-title">Медиахаб нового уровня</h2>
                <p className="auth-value-lead">
                  {authMode === "login"
                    ? "Возвращайтесь в единое рабочее пространство и продолжайте с того места, где остановились."
                    : "Создайте аккаунт за минуту и получите доступ к контенту, календарю и публикациям в одном окне."}
                </p>
                <div className="auth-value-list">
                  <p>Единый контур: идеи, генерация, публикация</p>
                  <p>Прозрачные статусы и быстрый цикл контента</p>
                  <p>Без лишних шагов и лишнего интерфейса</p>
                </div>
                <div className="auth-value-metrics">
                  <div>
                    <strong>&lt; 1 мин</strong>
                    <span>вход в работу</span>
                  </div>
                  <div>
                    <strong>3 шага</strong>
                    <span>от идеи до поста</span>
                  </div>
                </div>
              </aside>

              <div className="auth-page">
                <div className="auth-page-top">
                  <h2>{authTitle}</h2>
                  <p className="muted auth-page-lead">
                    {authMode === "login"
                      ? "Войдите с помощью e-mail и пароля."
                      : "Зарегистрируйтесь и подтвердите почту кодом."}
                  </p>
                </div>
                <form className="form auth-page-form" onSubmit={handleAuthSubmit}>
                <label>
                  Электронная почта
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@mail.com"
                    required
                  />
                </label>
                {authMode === "register" && (
                  <div className="verify-panel">
                    <button type="button" className="btn btn-outline" onClick={sendVerificationCode}>
                      {authLoading
                        ? "Отправка..."
                        : codeSent
                        ? "Отправить код повторно"
                        : "Отправить код на почту"}
                    </button>
                    {codeSent && (
                      <div className="verify-inline">
                        <input
                          type="text"
                          inputMode="numeric"
                          maxLength={6}
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                          placeholder="Код из письма"
                        />
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={verifyCode}
                          disabled={codeVerified}
                        >
                          {codeVerified ? "Подтверждено" : "Подтвердить код"}
                        </button>
                      </div>
                    )}
                    {codeDebugHint && <p className="debug-code">{codeDebugHint}</p>}
                  </div>
                )}
                <label>
                  Пароль
                  <input
                    type={showPassword ? "text" : "password"}
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Минимум 8 символов"
                    required
                  />
                </label>
                {authMode === "register" && (
                  <>
                    <label>
                      Повторите пароль
                      <input
                        type={showPassword ? "text" : "password"}
                        minLength={8}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Повторите пароль"
                        required
                      />
                    </label>
                    <div className="password-meter">
                      <div className={`meter-bar meter-${passStrength.score}`} />
                      <span>Сложность пароля: {passStrength.label}</span>
                    </div>
                    <ul className="rules-list">
                      <li className={passwordRules(password).minLength ? "ok" : ""}>минимум 8 символов</li>
                      <li className={passwordRules(password).upper ? "ok" : ""}>хотя бы 1 заглавная буква</li>
                      <li className={passwordRules(password).lower ? "ok" : ""}>хотя бы 1 строчная буква</li>
                      <li className={passwordRules(password).digit ? "ok" : ""}>хотя бы 1 цифра</li>
                      <li className={passwordRules(password).special ? "ok" : ""}>
                        хотя бы 1 спецсимвол (!@#$...)
                      </li>
                    </ul>
                  </>
                )}
                <label className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={showPassword}
                    onChange={(e) => setShowPassword(e.target.checked)}
                  />
                  Показать пароль
                </label>
                {authMode === "login" && (
                  <label className="checkbox-line">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    Запомнить меня на этом устройстве
                  </label>
                )}
                <button className="btn btn-primary" type="submit">
                  {authLoading ? "Проверка..." : "Продолжить"}
                </button>
                </form>
                {authMode === "login" && (
                  <p className="forgot-hint">Забыли пароль? Для MVP используйте регистрацию заново.</p>
                )}
                <p className="switch-text">
                  {authMode === "login" ? "Нет аккаунта?" : "Уже зарегистрированы?"}
                  <button
                    className="link-btn"
                    onClick={() => {
                      setAuthMode(authMode === "login" ? "register" : "login");
                      setAuthMessage("");
                    }}
                  >
                    {authMode === "login" ? " Зарегистрироваться" : " Войти"}
                  </button>
                </p>
                <p className={`message ${authMessageType}`}>{authMessage}</p>
              </div>
            </div>
          </motion.section>
        )}

        <AnimatePresence mode="wait">
          {activeTab === "home" && (
            <motion.div
              key="home"
              initial={{ opacity: 0, y: 18, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -14, filter: "blur(3px)" }}
              transition={{ duration: 0.45 }}
            >
            <motion.section
              className="hero"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55 }}
            >
              <motion.h1
                initial={{ opacity: 0, y: 28 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.8 }}
              >
                Медиахаб для молодёжного центра Красноярского края
              </motion.h1>
              <p className="subtitle">
                Команда «Безумный MAX» делает удобный сервис для планирования контента,
                автогенерации постов и быстрой работы с календарём публикаций.
              </p>
            </motion.section>

            <motion.section className="cards" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ staggerChildren: 0.08 }}>
              <motion.article className="card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.03 }} whileHover={{ y: -6 }}>
                <h3>Проблема кейса</h3>
                <p>Контент публикуется хаотично, а данные и медиа хранятся разрозненно.</p>
              </motion.article>
              <motion.article className="card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.11 }} whileHover={{ y: -6 }}>
                <h3>MVP решение</h3>
                <p>Авторизация, календарь контента и быстрый сценарий создания события.</p>
              </motion.article>
              <motion.article className="card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }} whileHover={{ y: -6 }}>
                <h3>Целевая аудитория</h3>
                <p>Сотрудники МЦ, руководители, волонтёры и молодёжь 14–35 лет.</p>
              </motion.article>
            </motion.section>

            <section className="showcase">
              <article className="showcase-item">
                <div className="showcase-content">
                  <h2>Контент-план как режиссура: неделя, роли, дедлайны.</h2>
                  <p>Единая панель для SMM-команды, волонтёров и руководителя центра.</p>
                </div>
              </article>
              <article className="showcase-item reverse">
                <div className="showcase-content">
                  <h2>Календарь публикаций, который выглядит и работает как pro-tool.</h2>
                  <p>Планирование, редактирование, удаление и контроль статусов в одном месте.</p>
                </div>
              </article>
            </section>

            <motion.section
              className="minecraft-easter"
              initial={{ opacity: 0, y: 34 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.7 }}
            >
              <div className="minecraft-copy">
                <h3>Житель уже проверил твой контент-план. Хммм…</h3>
              </div>
              <motion.div
                className="villager-wrap"
                initial={{ opacity: 0, scale: 0.9, y: 16 }}
                whileInView={{ opacity: 1, scale: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.6, delay: 0.15 }}
              >
                <button type="button" className="villager-btn" onClick={playVillagerSound}>
                  <img src="/villager-user.png" alt="Житель Minecraft" className="villager-img" />
                </button>
                <audio ref={villagerAudioRef} src="/villager-sound.mp3" preload="auto" />
              </motion.div>
            </motion.section>
            </motion.div>
          )}

          {activeTab === "content" && (
            <motion.section
              key="content"
              className="content-page"
              initial={{ opacity: 0, y: 18, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -14, filter: "blur(3px)" }}
              transition={{ duration: 0.45 }}
            >
              <div className="content-page-head">
                <div>
                  <h2 className="content-page-title">Контент</h2>
                  <p className="muted content-page-lead">
                    События с промптом, генерацией текста и картинкой хранятся здесь и не связаны с календарём публикаций.
                  </p>
                </div>
                <button className="btn btn-primary" type="button" onClick={openSmartEvent}>
                  Новое событие
                </button>
              </div>
              {contentEvents.length === 0 ? (
                <p className="empty content-empty">Пока нет записей — нажмите «Новое событие» или кнопку в шапке.</p>
              ) : (
                <div className="content-grid">
                  {contentEvents.map((c) => (
                    <article key={c.id} className="content-card">
                      <div className="content-card-head">
                        <h3>{c.title}</h3>
                        <time dateTime={c.createdAt}>
                          {new Date(c.createdAt).toLocaleString("ru-RU", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </time>
                      </div>
                      {c.attachmentDataUrl && (
                        <img src={c.attachmentDataUrl} alt="" className="content-card-thumb" />
                      )}
                      {c.prompt && (
                        <p className="content-card-meta">
                          <strong>Промпт:</strong> {c.prompt}
                        </p>
                      )}
                      {c.tone && (
                        <p className="content-card-meta">
                          <strong>Тон:</strong> {c.tone}
                        </p>
                      )}
                      {c.generatedText && (
                        <p className="content-card-text">{c.generatedText}</p>
                      )}
                      {c.vkWallUrl && (
                        <p className="content-card-vk">
                          <a href={c.vkWallUrl} target="_blank" rel="noreferrer">
                            Открыть пост в VK
                          </a>
                        </p>
                      )}
                      {c.vkWallUrl && c.vkPostId && (
                        <button
                          type="button"
                          className="link-btn danger"
                          onClick={() => deleteVkPostForContent(c.id)}
                          disabled={deletingVkItemId === c.id}
                        >
                          {deletingVkItemId === c.id ? "Удаление..." : "Удалить пост из VK"}
                        </button>
                      )}
                      {!c.vkWallUrl && (
                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => republishContentEvent(c.id)}
                          disabled={publishingItemId === c.id}
                        >
                          {publishingItemId === c.id ? "Публикация..." : "Опубликовать в VK"}
                        </button>
                      )}
                      {c.vkPublishError && <p className="content-card-error">{c.vkPublishError}</p>}
                      <button type="button" className="link-btn danger" onClick={() => removeContentEvent(c.id)}>
                        Удалить
                      </button>
                    </article>
                  ))}
                </div>
              )}
              <p className={`message ${contentMessageType}`}>{contentMessage}</p>
            </motion.section>
          )}

          {activeTab === "report" && (
            <motion.section
              key="report"
              className="content-page"
              initial={{ opacity: 0, y: 18, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -14, filter: "blur(3px)" }}
              transition={{ duration: 0.45 }}
            >
              <div className="content-page-head">
                <div>
                  <h2 className="content-page-title">Отчет</h2>
                  <p className="muted content-page-lead">
                    Сформируйте сводный отчет по контенту и публикациям в VK.
                  </p>
                </div>
                <button className="btn btn-primary" type="button" onClick={openReportModal}>
                  Создание отчета на основе контента
                </button>
              </div>
            </motion.section>
          )}

          {activeTab === "calendar" && (
          <motion.section
            key="calendar"
            className="calendar"
            initial={{ opacity: 0, y: 18, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -14, filter: "blur(3px)" }}
            transition={{ duration: 0.45 }}
          >
          <div className="calendar-top">
            <div className="calendar-nav">
              <button className="btn btn-outline" onClick={() => shiftPeriod(-1)}>
                Назад
              </button>
              <button
                className="btn btn-outline"
                onClick={() => {
                  const now = new Date();
                  setCalendarDate(now);
                  setSelectedDay(toInputDate(now));
                }}
              >
                Сегодня
              </button>
              <button className="btn btn-outline" onClick={() => shiftPeriod(1)}>
                Вперёд
              </button>
            </div>
            <h2 className="calendar-title">{periodLabel}</h2>
            <div className="calendar-actions">
              <div className="view-switch">
                  <motion.button whileTap={{ scale: 0.96 }} className={`tiny-btn ${calendarView === "month" ? "active" : ""}`} onClick={() => setCalendarView("month")}>
                  Месяц
                  </motion.button>
                  <motion.button whileTap={{ scale: 0.96 }} className={`tiny-btn ${calendarView === "week" ? "active" : ""}`} onClick={() => setCalendarView("week")}>
                  Неделя
                  </motion.button>
                  <motion.button whileTap={{ scale: 0.96 }} className={`tiny-btn ${calendarView === "day" ? "active" : ""}`} onClick={() => setCalendarView("day")}>
                  День
                  </motion.button>
              </div>
              <button className="btn btn-primary" onClick={() => openCreateEvent()}>
                + Новое событие
              </button>
            </div>
          </div>

          {calendarView === "month" && (
            <div className="month-grid">
              {WEEK_DAYS.map((d) => (
                <div key={d} className="weekday">
                  {d}
                </div>
              ))}
              {monthCells.map((d) => {
                const dateKey = toInputDate(d);
                const dayEvents = eventsByDate.get(dateKey) ?? [];
                const isCurrentMonth = d.getMonth() === calendarDate.getMonth();
                const isToday = dateKey === toInputDate(new Date());
                const isSelected = dateKey === selectedDay;
                return (
                  <button
                    key={dateKey}
                    className={`day-cell ${isCurrentMonth ? "" : "muted-cell"} ${isToday ? "today-cell" : ""} ${
                      isSelected ? "selected-cell" : ""
                    }`}
                    onClick={() => {
                      setSelectedDay(dateKey);
                      setCalendarDate(d);
                    }}
                  >
                    <span>{d.getDate()}</span>
                    <div className="mini-events">
                      {dayEvents.slice(0, 2).map((ev) => (
                        <button
                          key={ev.id}
                          className="mini-event"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditEvent(ev);
                          }}
                        >
                          {ev.startTime} {ev.title}
                        </button>
                      ))}
                      {dayEvents.length > 2 && <div className="mini-more">+{dayEvents.length - 2} ещё</div>}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {calendarView === "week" && (
            <div className="week-grid">
              {weekDays.map((d) => {
                const key = toInputDate(d);
                const dayEvents = eventsByDate.get(key) ?? [];
                return (
                  <div key={key} className="week-col">
                    <div className="week-head">
                      <strong>{WEEK_DAYS[(d.getDay() + 6) % 7]}</strong>
                      <span>{d.getDate()}</span>
                    </div>
                    <button className="link-btn week-add" onClick={() => openCreateEvent(key)}>
                      + добавить
                    </button>
                    <div className="week-events">
                      {dayEvents.length === 0 && <p className="empty">Нет событий</p>}
                      {dayEvents.map((ev) => (
                        <button key={ev.id} className="week-event" onClick={() => openEditEvent(ev)}>
                          <b>
                            {ev.startTime} - {ev.endTime}
                          </b>
                          <span>{ev.title}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {calendarView === "day" && (
            <div className="day-view">
              <div className="day-header">
                <h3>
                  {parseInputDate(selectedDay).toLocaleDateString("ru-RU", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
                </h3>
                <button className="btn btn-secondary" onClick={() => openCreateEvent(selectedDay)}>
                  Создать событие
                </button>
              </div>
              <div className="day-list">
                {selectedEvents.length === 0 && <p className="empty">На выбранный день событий нет.</p>}
                {selectedEvents.map((ev) => (
                  <div key={ev.id} className="day-event">
                    <div>
                      <b>
                        {ev.startTime} - {ev.endTime}
                      </b>
                      <p>{ev.title}</p>
                      <small>
                        {statusLabel[ev.status]} · {ev.platforms.join(", ")}
                      </small>
                    </div>
                    <div className="day-event-actions">
                      <button className="link-btn" onClick={() => openEditEvent(ev)}>
                        Редактировать
                      </button>
                      <button className="link-btn danger" onClick={() => removeEvent(ev.id)}>
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="agenda-panel">
            <div className="day-header">
              <h3>
                События на {parseInputDate(selectedDay).toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}
              </h3>
              <button className="btn btn-secondary" onClick={() => openCreateEvent(selectedDay)}>
                + Добавить
              </button>
            </div>
            <div className="day-list">
              {selectedEvents.length === 0 && <p className="empty">На этот день пока нет событий.</p>}
              {selectedEvents.map((ev) => (
                <div key={ev.id} className="day-event">
                  <div>
                    <b>
                      {ev.startTime} - {ev.endTime}
                    </b>
                    <p>{ev.title}</p>
                    <small>
                      {statusLabel[ev.status]} · {ev.platforms.join(", ")}
                    </small>
                  </div>
                  <div className="day-event-actions">
                    <button className="link-btn" onClick={() => openEditEvent(ev)}>
                      Редактировать
                    </button>
                    <button className="link-btn danger" onClick={() => removeEvent(ev.id)}>
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          </motion.section>
        )}
        </AnimatePresence>
      </main>

      {reportOpen && (
        <div className="modal-layer" onClick={() => setReportOpen(false)}>
          <div className="modal modal-wide report-modal" onClick={(e) => e.stopPropagation()}>
            <button className="close" type="button" onClick={() => setReportOpen(false)}>
              x
            </button>
            <h2>Отчет на основе контента</h2>
            <p className="muted">
              Авто-сводка по разделу «Контент»: статус публикаций, список записей и тексты.
            </p>
            <div className="report-actions">
              <button className="btn btn-primary" type="button" onClick={downloadReport}>
                Скачать .txt
              </button>
              <button className="btn btn-outline" type="button" onClick={copyReport}>
                Копировать
              </button>
            </div>
            <textarea
              className="report-textarea"
              value={reportText}
              onChange={(e) => setReportText(e.target.value)}
              rows={16}
            />
            <p className={`message ${reportMessageType}`}>{reportMessage}</p>
          </div>
        </div>
      )}

      {calendarModalOpen && (
        <div className="modal-layer" onClick={() => setCalendarModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="close" onClick={() => setCalendarModalOpen(false)}>
              x
            </button>
            <h2>Событие в календаре</h2>
            <p className="muted">Добавьте событие по сценарию в стиле Яндекс Календаря.</p>
            <form className="form" onSubmit={handleCalendarSubmit}>
              <label>
                Название
                <input type="text" value={eventTitle} onChange={(e) => setEventTitle(e.target.value)} required />
              </label>
              <label>
                Описание
                <input
                  type="text"
                  value={eventDescription}
                  onChange={(e) => setEventDescription(e.target.value)}
                  placeholder="Кратко о событии"
                />
              </label>
              <label>
                Дата
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  required
                />
              </label>
              <label>
                Время
                <input
                  type="time"
                  value={eventTime}
                  onChange={(e) => setEventTime(e.target.value)}
                  required
                />
              </label>
              <label>
                Длительность (минуты)
                <input
                  type="number"
                  min={15}
                  step={15}
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  required
                />
              </label>
              <label>
                Статус
                <select value={eventStatus} onChange={(e) => setEventStatus(e.target.value as EventStatus)}>
                  <option value="draft">Черновик</option>
                  <option value="scheduled">Запланирован</option>
                  <option value="published">Опубликован</option>
                </select>
              </label>
              <div className="platforms">
                <span>Площадки:</span>
                {["VK", "Telegram", "YouTube", "Rutube"].map((platform) => (
                  <label key={platform} className="checkbox-line">
                    <input
                      type="checkbox"
                      checked={eventPlatforms.includes(platform)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setEventPlatforms((prev) => [...prev, platform]);
                        } else {
                          setEventPlatforms((prev) => prev.filter((p) => p !== platform));
                        }
                      }}
                    />
                    {platform}
                  </label>
                ))}
              </div>
              <button className="btn btn-primary" type="submit">
                {editingEventId ? "Сохранить изменения" : "Создать событие"}
              </button>
            </form>
            <p className={`message ${calendarMessageType}`}>{calendarMessage}</p>
          </div>
        </div>
      )}

      {smartEventOpen && (
        <div className="modal-layer" onClick={closeSmartEvent}>
          <div className="modal modal-wide smart-event-modal" onClick={(e) => e.stopPropagation()}>
            <button className="close" type="button" onClick={closeSmartEvent}>
              x
            </button>
            <h2>Создать событие</h2>
            <p className="muted">
              Отдельно от календаря: сохраняется в «Контент». LLM — <code>POST /api/llm/generate</code>; опционально
              стена VK — <code>POST /api/vk/poster</code> (текст поста; картинка из формы в VK в этом режиме не
              отправляется). Бэкенд:{" "}
              <a
                href="https://github.com/TheAlexGrimes30/protechno-media-analyzer/tree/feature/frontend"
                target="_blank"
                rel="noreferrer"
              >
                feature/frontend
              </a>
              , <code>uvicorn backend.app.main:app --reload</code>
            </p>
            <form className="form" onSubmit={handleSmartSubmit}>
              <label>
                Название события
                <input
                  type="text"
                  value={smartTitle}
                  onChange={(e) => setSmartTitle(e.target.value)}
                  placeholder="Например: Кинопоказ на Татышеве"
                  required
                />
              </label>
              <label>
                Промпт для ИИ
                <textarea
                  rows={4}
                  value={smartPrompt}
                  onChange={(e) => setSmartPrompt(e.target.value)}
                  placeholder="Опишите событие, аудиторию, что должно быть в тексте поста…"
                />
              </label>
              <label>
                Тон и стиль (необязательно)
                <input
                  type="text"
                  value={smartTone}
                  onChange={(e) => setSmartTone(e.target.value)}
                  placeholder="Дружелюбно, с хэштегами, коротко…"
                />
              </label>
              <div className="smart-llm-row">
                <button className="btn btn-outline" type="button" onClick={handleSmartGenerate} disabled={smartLlmLoading}>
                  {smartLlmLoading ? "Генерация…" : "Сгенерировать текст (LLM)"}
                </button>
              </div>
              <label>
                Текст поста / описание
                <textarea
                  rows={5}
                  value={smartGenerated}
                  onChange={(e) => setSmartGenerated(e.target.value)}
                  placeholder="Сюда подставится ответ ИИ — можно править вручную"
                />
              </label>
              <div className="smart-attachment-block">
                <span className="smart-attachment-label">Изображение к событию</span>
                <input
                  ref={smartFileInputRef}
                  type="file"
                  accept="image/*"
                  className="visually-hidden"
                  onChange={handleSmartImagePick}
                />
                <div className="smart-attachment-row">
                  <button className="btn btn-secondary" type="button" onClick={() => smartFileInputRef.current?.click()}>
                    Прикрепить изображение
                  </button>
                  {smartImagePreview && (
                    <button className="btn btn-outline" type="button" onClick={clearSmartImage}>
                      Убрать файл
                    </button>
                  )}
                </div>
                {smartImagePreview && (
                  <img src={smartImagePreview} alt="Предпросмотр" className="smart-preview" />
                )}
                <small className="attachment-hint">До {Math.round(MAX_ATTACHMENT_BYTES / 1024)} КБ, хранится в браузере.</small>
              </div>
              <label className="checkbox-line vk-publish-line">
                <input
                  type="checkbox"
                  checked={publishToVk}
                  onChange={(e) => setPublishToVk(e.target.checked)}
                  disabled={vkPublishing}
                />
                Опубликовать на стену VK после сохранения (тот же текст: заголовок + пост/промпт)
              </label>
              <button className="btn btn-primary" type="submit" disabled={vkPublishing}>
                {vkPublishing ? "Публикация в VK…" : "Сохранить"}
              </button>
            </form>
            <p className={`message ${smartMessageType}`}>{smartMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
