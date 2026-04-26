/** База API: пустая строка = относительные пути (прокси Vite → backend). Или VITE_API_BASE_URL=http://127.0.0.1:8000 */
export function apiUrl(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";
  if (!path.startsWith("/")) return `${base}/${path}`;
  return base ? `${base}${path}` : path;
}

async function fetchJson<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Нет соединения с backend. Проверьте, что фронт запущен через Vite, а backend доступен по proxy /api");
    }
    throw error;
  }

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export type LlmGenerateResponse = {
  text: string;
  model: string;
  shots_used: number;
};

export async function llmGenerate(query: string): Promise<LlmGenerateResponse> {
  return fetchJson<LlmGenerateResponse>("/api/llm/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}

export type VkPosterResponse = {
  post_id: number;
  url: string;
};

/** Публикация на стену VK (токен и группа настраиваются на бэкенде). */
export async function vkPoster(payload: {
  message: string;
  attachments?: string | null;
  from_group?: boolean;
}): Promise<VkPosterResponse> {
  return fetchJson<VkPosterResponse>("/api/vk/poster", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: payload.message,
      attachments: payload.attachments ?? null,
      from_group: payload.from_group ?? true,
    }),
  });
}

export async function vkDeletePost(post_id: number): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>("/api/vk/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post_id }),
  });
}

/** Загружает фото в VK и возвращает строку вложения (photo{owner}_{id}). */
export async function vkUploadPhoto(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(apiUrl("/api/vk/upload-photo"), { method: "POST", body: form });
  } catch (error) {
    throw new Error("Нет соединения с backend при загрузке фото");
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { attachment: string };
  return data.attachment;
}
