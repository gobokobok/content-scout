import { canDownloadViaTelegram, downloadFileViaTelegram } from "@/lib/telegram-webapp";

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
  display_name: string;
  is_admin: boolean;
  has_telegram: boolean;
  token_balance: number;
}

export interface ProjectResponse {
  id: string;
  name: string;
  created_at: string;
  archived_at: string | null;
  accounts_count: number;
}

export interface ProjectStatsResponse {
  lifetime_items_analyzed: number;
}

export interface AccountResponse {
  id: string;
  handle: string;
  normalized_url: string;
  status: string;
  created_at: string;
  display_name: string | null;
  followers_count: number | null;
  avatar_url: string | null;
  profile_updated_at: string | null;
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
  duration_days: number | null;
  item_limit: number | null;
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
  summary_status: "pending" | "done" | "failed";
  summary_text: string | null;
  summary_topics: string[] | null;
}

export interface RunRequest {
  duration_days?: number;
  item_limit?: number;
  account_ids?: string[];
}

export interface ContentItemResponse {
  id: string;
  account_handle: string;
  followers_count: number | null;
  published_at: string;
  type: "reel" | "post" | "carousel" | "video" | "short";
  title: string | null;
  url: string;
  summary: string | null;
  likes: number | null;
  views: number | null;
  comments: number | null;
  days_since_published: number;
  views_per_day: number | null;
  likes_per_day: number | null;
  engagement_rate: number | null;
  virality: "high" | "medium" | "low" | null;
  in_shortlist: boolean;
}

export type ScheduleMode = "once" | "recurring";
export type ScheduledRunSkipReason = "no_accounts" | "no_tokens" | "quota_exceeded";

export interface ScheduledRunResponse {
  id: string;
  project_id: string;
  account_ids: string[] | null;
  duration_days: number | null;
  item_limit: number | null;
  mode: ScheduleMode;
  days_of_week: number[];
  time_of_day: string;
  timezone: string;
  active: boolean;
  notify_enabled: boolean;
  last_run_id: string | null;
  last_skip_reason: ScheduledRunSkipReason | null;
  last_skip_at: string | null;
  created_at: string;
}

export interface SkippedScheduleResponse {
  id: string;
  project_id: string;
  project_name: string;
  reason: ScheduledRunSkipReason;
  skipped_at: string;
}

export interface ScheduledRunRequest {
  duration_days?: number;
  item_limit?: number;
  account_ids?: string[];
  mode: ScheduleMode;
  days_of_week: number[];
  time_of_day: string;
  timezone: string;
  active: boolean;
  notify_enabled: boolean;
}

export interface ShortlistItemResponse {
  id: string;
  content_item_id: string;
  account_handle: string;
  published_at: string;
  type: "reel" | "post" | "carousel" | "video" | "short";
  title: string | null;
  url: string;
  summary: string | null;
  likes: number | null;
  views: number | null;
  added_at: string;
}

export interface UserUsageRowResponse {
  user_id: string;
  email: string;
  runs: number;
  apify_units: number;
  claude_input_tokens: number;
  claude_output_tokens: number;
  total_cost_usd: string;
}

export interface AdminUsageResponse {
  from_: string;
  to: string;
  users: UserUsageRowResponse[];
}

export interface KindTotalResponse {
  kind: string;
  quantity: number;
  cost_usd: string;
}

export interface UsageResponse {
  from_: string;
  to: string;
  total_cost_usd: string;
  by_kind: KindTotalResponse[];
}

export interface RunSummaryResponse {
  id: string;
  project_id: string;
  project_name: string;
  kind: "run" | "deep_analysis";
  status: string;
  duration_days: number | null;
  item_limit: number | null;
  progress_items: number;
  tokens_charged: number;
  total_input_tokens: number;
  total_output_tokens: number;
  created_at: string;
  finished_at: string | null;
}

export interface ShortlistHistoryItemResponse {
  id: string;
  content_item_id: string;
  account_handle: string;
  type: "reel" | "post" | "carousel" | "video" | "short";
  title: string | null;
  url: string;
  added_at: string;
  removed_at: string | null;
}

export interface ItemsPageResponse {
  items: ContentItemResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TopViralityResponse {
  items: ContentItemResponse[];
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
  | "comments"
  | "days_since_published"
  | "views_per_day"
  | "likes_per_day"
  | "engagement_rate"
  | "virality";

// E17: Run Deep Analysis
export type DeepAnalysisStatus = "pending" | "extracting" | "synthesizing" | "done" | "failed";

export interface DeepAnalysisTopicStat {
  topic: string;
  frequency: number;
  avg_virality: "high" | "medium" | "low" | "unknown";
}

export interface DeepAnalysisFormatStat {
  format: string;
  count: number;
}

export interface DeepAnalysisHookStat {
  hook_type: string;
  count: number;
}

export interface DeepAnalysisStats {
  topics: DeepAnalysisTopicStat[];
  formats: DeepAnalysisFormatStat[];
  hooks: DeepAnalysisHookStat[];
  cta_share: number | null;
  cadence_summary: string;
  sentiment_summary: string;
  representative_quotes: string[];
  // E17-S9: set when comment coverage across the run's items was too thin to trust
  // comment-derived sections — those sections are stripped server-side when this is true.
  comment_coverage_degraded?: boolean;
}

export interface DeepAnalysisContentIdea {
  topic: string;
  format: string;
  hook: string;
  why: string;
}

export interface DeepAnalysisStealThisItem {
  content_item_id: string;
  reason: string;
}

export interface DeepAnalysisRecommendations {
  content_ideas: DeepAnalysisContentIdea[];
  do_more: string[];
  do_less: string[];
  hook_templates: string[];
  faq_pack: string[];
  posting_schedule: string;
  steal_this: DeepAnalysisStealThisItem[];
  comment_coverage_degraded?: boolean;
}

export interface DeepAnalysisResponse {
  id: string;
  run_id: string;
  project_id: string;
  status: DeepAnalysisStatus;
  tokens_charged: number;
  error_message: string | null;
  report_stats: DeepAnalysisStats | null;
  report_recommendations: DeepAnalysisRecommendations | null;
  created_at: string;
  completed_at: string | null;
}

export interface DeepAnalysisEstimateResponse {
  tokens: number;
}

export const api = {
  getRegisterConfig: () =>
    request<{ require_invite: boolean }>("/auth/register/config"),
  register: (email: string, password: string, inviteCode?: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, invite_code: inviteCode ?? null }),
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserResponse>("/auth/me"),
  updateDisplayName: (displayName: string) =>
    request<UserResponse>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ display_name: displayName }),
    }),
  getTelegramConfig: () =>
    request<{ enabled: boolean; bot_username: string }>("/auth/telegram/config"),
  telegramLogin: (data: Record<string, string | number>) =>
    request<TokenResponse>("/auth/telegram/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  telegramWebappLogin: (initData: string) =>
    request<TokenResponse>("/auth/telegram/webapp", {
      method: "POST",
      body: JSON.stringify({ init_data: initData }),
    }),
  telegramLink: (data: Record<string, string | number>) =>
    request<UserResponse>("/auth/telegram/link", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listProjects: (includeArchived = false) =>
    request<ProjectResponse[]>(`/projects${includeArchived ? "?include_archived=true" : ""}`),
  createProject: (name: string) =>
    request<ProjectResponse>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  getProject: (id: string) => request<ProjectResponse>(`/projects/${id}`),
  getProjectStats: (id: string) => request<ProjectStatsResponse>(`/projects/${id}/stats`),
  renameProject: (id: string, name: string) =>
    request<ProjectResponse>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  archiveProject: (id: string) =>
    request<ProjectResponse>(`/projects/${id}/archive`, { method: "POST" }),
  unarchiveProject: (id: string) =>
    request<ProjectResponse>(`/projects/${id}/unarchive`, { method: "POST" }),
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
  listScheduledRuns: (projectId: string) =>
    request<ScheduledRunResponse[]>(`/projects/${projectId}/scheduled-runs`),
  createScheduledRun: (projectId: string, body: ScheduledRunRequest) =>
    request<ScheduledRunResponse>(`/projects/${projectId}/scheduled-runs`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateScheduledRun: (projectId: string, scheduledRunId: string, body: ScheduledRunRequest) =>
    request<ScheduledRunResponse>(`/projects/${projectId}/scheduled-runs/${scheduledRunId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteScheduledRun: (projectId: string, scheduledRunId: string) =>
    request<void>(`/projects/${projectId}/scheduled-runs/${scheduledRunId}`, {
      method: "DELETE",
    }),
  listSkippedSchedules: () => request<SkippedScheduleResponse[]>("/scheduled-runs/skipped"),
  listDeepAnalyses: (projectId: string) =>
    request<DeepAnalysisResponse[]>(`/projects/${projectId}/deep-analyses`),
  estimateDeepAnalysis: (projectId: string, runId: string) =>
    request<DeepAnalysisEstimateResponse>(
      `/projects/${projectId}/runs/${runId}/deep-analyses/estimate`,
    ),
  createDeepAnalysis: (projectId: string, runId: string) =>
    request<DeepAnalysisResponse>(`/projects/${projectId}/runs/${runId}/deep-analyses`, {
      method: "POST",
    }),
  getDeepAnalysis: (analysisId: string) =>
    request<DeepAnalysisResponse>(`/deep-analyses/${analysisId}`),
  getTopVirality: (runId: string, limit = 5) =>
    request<TopViralityResponse>(`/runs/${runId}/top-virality?limit=${limit}`),
  listRunItems: (
    runId: string,
    params: { sort: ItemSortField; order: "asc" | "desc"; page: number },
  ) =>
    request<ItemsPageResponse>(
      `/runs/${runId}/items?sort=${params.sort}&order=${params.order}&page=${params.page}`,
    ),
  listProjectItems: (
    projectId: string,
    params: {
      runId: string | null;
      starredOnly: boolean;
      sort: ItemSortField;
      order: "asc" | "desc";
      page: number;
    },
  ) => {
    const q = new URLSearchParams({
      sort: params.sort,
      order: params.order,
      page: String(params.page),
      starred_only: String(params.starredOnly),
    });
    if (params.runId) q.set("run_id", params.runId);
    return request<ItemsPageResponse>(`/projects/${projectId}/items?${q.toString()}`);
  },
  listShortlist: (projectId: string) =>
    request<ShortlistItemResponse[]>(`/projects/${projectId}/shortlist/items`),
  addToShortlist: (projectId: string, itemIds: string[]) =>
    request<void>(`/projects/${projectId}/shortlist/items`, {
      method: "POST",
      body: JSON.stringify({ item_ids: itemIds }),
    }),
  removeFromShortlist: (projectId: string, contentItemId: string) =>
    request<void>(`/projects/${projectId}/shortlist/items/${contentItemId}`, {
      method: "DELETE",
    }),
  listShortlistHistory: (projectId: string) =>
    request<ShortlistHistoryItemResponse[]>(`/projects/${projectId}/history/shortlist`),
  getMyUsage: (from: Date, to: Date) =>
    request<UsageResponse>(
      `/me/usage?from=${from.toISOString()}&to=${to.toISOString()}`,
    ),
  getMyRuns: (from: Date, to: Date) =>
    request<RunSummaryResponse[]>(
      `/me/runs?from=${from.toISOString()}&to=${to.toISOString()}`,
    ),
  getAdminUsage: (from: Date, to: Date) =>
    request<AdminUsageResponse>(
      `/admin/usage?from=${from.toISOString()}&to=${to.toISOString()}`,
    ),
  downloadShortlistXlsx: async (projectId: string): Promise<{ blob: Blob; filename: string }> => {
    const token = getToken();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`${API_URL}/projects/${projectId}/shortlist/export.xlsx`, { headers });
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
    const filename = match?.[1] ?? `content-scout_shortlist_${projectId}.xlsx`;
    return { blob, filename };
  },
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
  mintRunExportToken: (runId: string) =>
    request<{ token: string }>(`/runs/${runId}/export-token`, { method: "POST" }),
  mintShortlistExportToken: (projectId: string) =>
    request<{ token: string }>(`/projects/${projectId}/shortlist/export-token`, {
      method: "POST",
    }),
  mintProjectItemsExportToken: (projectId: string) =>
    request<{ token: string }>(`/projects/${projectId}/items/export-token`, { method: "POST" }),
  downloadProjectItemsXlsx: async (
    projectId: string,
    params: { runId: string | null; starredOnly: boolean; sort: ItemSortField; order: "asc" | "desc" },
  ): Promise<{ blob: Blob; filename: string }> => {
    const token = getToken();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const q = new URLSearchParams({
      sort: params.sort,
      order: params.order,
      starred_only: String(params.starredOnly),
    });
    if (params.runId) q.set("run_id", params.runId);
    const res = await fetch(`${API_URL}/projects/${projectId}/items/export.xlsx?${q.toString()}`, {
      headers,
    });
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
    const filename = match?.[1] ?? `content-scout_${projectId}.xlsx`;
    return { blob, filename };
  },
};

/**
 * Downloads an .xlsx export, routing through Telegram's native downloadFile popup when
 * available. Telegram's iOS/Android WebView does not reliably honor `<a download>` on a blob
 * URL — the request succeeds server-side, but the user never gets a save prompt. downloadFile
 * fetches the URL itself with no custom headers, so it needs a short-lived scoped token
 * (dl_token) rather than the normal Authorization header, and needs the filename up front
 * (before the response — and its real Content-Disposition filename — even exists).
 */
export async function downloadXlsx(
  endpointPath: string,
  mintToken: () => Promise<{ token: string }>,
  blobDownload: () => Promise<{ blob: Blob; filename: string }>,
  telegramFileName: string,
): Promise<void> {
  if (canDownloadViaTelegram()) {
    const { token } = await mintToken();
    const sep = endpointPath.includes("?") ? "&" : "?";
    const url = `${API_URL}${endpointPath}${sep}dl_token=${encodeURIComponent(token)}`;
    downloadFileViaTelegram(url, telegramFileName);
    return;
  }
  const { blob, filename } = await blobDownload();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
