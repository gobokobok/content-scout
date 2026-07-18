const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "content-scout-token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public messageRu: string,
  ) {
    super(messageRu);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(
      res.status,
      detail?.code ?? "unknown_error",
      detail?.message_ru ?? "Произошла ошибка. Попробуйте ещё раз.",
    );
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  created_at: string;
  archived_at: string | null;
}

export interface AccountResponse {
  id: string;
  handle: string;
  normalized_url: string;
  status: string;
  created_at: string;
}

export interface AddAccountsResponse {
  added: AccountResponse[];
  errors: { input: string; message_ru: string }[];
  total: number;
}

export interface EstimateResponse {
  apify_units: number;
  claude_input_tokens: number;
  claude_output_tokens: number;
  estimated_cost_usd: string;
  accounts_count: number;
}

export interface RunResponse {
  id: string;
  project_id: string;
  status: "pending" | "scraping" | "summarizing" | "done" | "failed";
  duration_days: number;
  progress_accounts: number;
  progress_items: number;
  progress_summarized: number;
  error_message: string | null;
  estimated_cost_usd: string | null;
  total_cost_usd: string | null;
  total_input_tokens: number;
  total_output_tokens: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunRequest {
  duration_days: number;
  account_ids?: string[];
}

export interface ContentItemResponse {
  id: string;
  account_handle: string;
  published_at: string;
  type: "reel" | "post" | "carousel" | "video" | "short";
  title: string | null;
  url: string;
  summary: string | null;
  likes: number | null;
  views: number | null;
  days_since_published: number;
  views_per_day: number | null;
  likes_per_day: number | null;
}

export interface ItemsPageResponse {
  items: ContentItemResponse[];
  total: number;
  page: number;
  page_size: number;
}

export type ItemSortField =
  | "account"
  | "published_at"
  | "type"
  | "title"
  | "url"
  | "summary"
  | "likes"
  | "views"
  | "days_since_published"
  | "views_per_day"
  | "likes_per_day";

export const api = {
  register: (email: string, password: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserResponse>("/auth/me"),
  listProjects: () => request<ProjectResponse[]>("/projects"),
  createProject: (name: string) =>
    request<ProjectResponse>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  getProject: (id: string) => request<ProjectResponse>(`/projects/${id}`),
  renameProject: (id: string, name: string) =>
    request<ProjectResponse>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  archiveProject: (id: string) =>
    request<ProjectResponse>(`/projects/${id}/archive`, { method: "POST" }),
  listAccounts: (projectId: string) =>
    request<AccountResponse[]>(`/projects/${projectId}/accounts`),
  addAccounts: (projectId: string, entries: string[]) =>
    request<AddAccountsResponse>(`/projects/${projectId}/accounts`, {
      method: "POST",
      body: JSON.stringify({ entries }),
    }),
  removeAccount: (projectId: string, accountId: string) =>
    request<void>(`/projects/${projectId}/accounts/${accountId}`, { method: "DELETE" }),
  estimateRun: (projectId: string, body: RunRequest) =>
    request<EstimateResponse>(`/projects/${projectId}/runs/estimate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createRun: (projectId: string, body: RunRequest) =>
    request<RunResponse>(`/projects/${projectId}/runs`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getRun: (runId: string) => request<RunResponse>(`/runs/${runId}`),
  listRuns: (projectId: string) => request<RunResponse[]>(`/projects/${projectId}/runs`),
  listRunItems: (
    runId: string,
    params: { sort: ItemSortField; order: "asc" | "desc"; page: number },
  ) =>
    request<ItemsPageResponse>(
      `/runs/${runId}/items?sort=${params.sort}&order=${params.order}&page=${params.page}`,
    ),
  downloadRunXlsx: async (
    runId: string,
    sort: ItemSortField,
    order: "asc" | "desc",
  ): Promise<{ blob: Blob; filename: string }> => {
    const token = getToken();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(
      `${API_URL}/runs/${runId}/export.xlsx?sort=${sort}&order=${order}`,
      { headers },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const detail = body?.detail;
      throw new ApiError(
        res.status,
        detail?.code ?? "unknown_error",
        detail?.message_ru ?? "Произошла ошибка. Попробуйте ещё раз.",
      );
    }
    const blob = await res.blob();
    const cd = res.headers.get("content-disposition") ?? "";
    const match = cd.match(/filename="([^"]+)"/);
    const filename = match?.[1] ?? `content-scout_${runId}.xlsx`;
    return { blob, filename };
  },
};
