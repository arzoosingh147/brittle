import { Repository, PullRequestReview, ReviewMetricsSummary } from "@/types";

const getBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    const customUrl = process.env.NEXT_PUBLIC_API_URL;
    if (customUrl && !customUrl.includes("localhost") && !customUrl.includes("127.0.0.1")) {
      return customUrl.endsWith("/api/v1") ? customUrl : `${customUrl.replace(/\/+$/, "")}/api/v1`;
    }
    return "/api/v1";
  }
  const serverUrl = process.env.INTERNAL_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
  return serverUrl.endsWith("/api/v1") ? serverUrl : `${serverUrl.replace(/\/+$/, "")}/api/v1`;
};

const API_BASE_URL = getBaseUrl();

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // ignore
    }
    throw new ApiError(
      response.status,
      (errorData as { detail?: string })?.detail || `API request failed with status ${response.status}`,
      errorData
    );
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  // Repositories
  async getRepositories(): Promise<Repository[]> {
    return request<Repository[]>("/repos");
  },

  async getRepository(id: number): Promise<Repository> {
    return request<Repository>(`/repos/${id}`);
  },

  async triggerIndexing(id: number): Promise<{ message: string; status: string }> {
    return request<{ message: string; status: string }>(`/repos/${id}/index`, {
      method: "POST",
    });
  },

  async createRepository(data: {
    name: string;
    owner?: string;
    default_branch?: string;
    is_private?: boolean;
    rules?: Record<string, unknown>;
    auto_index?: boolean;
  }): Promise<Repository> {
    return request<Repository>("/repos", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteRepository(id: number): Promise<{ message: string; id: number }> {
    return request<{ message: string; id: number }>(`/repos/${id}`, {
      method: "DELETE",
    });
  },

  async updateRules(id: number, rules: Record<string, unknown>): Promise<Repository> {
    return request<Repository>(`/repos/${id}/rules`, {
      method: "PUT",
      body: JSON.stringify({ rules }),
    });
  },

  // Reviews
  async getReviews(repoId?: number): Promise<PullRequestReview[]> {
    const query = repoId ? `?repo_id=${repoId}` : "";
    return request<PullRequestReview[]>(`/reviews${query}`);
  },

  async getReview(id: number): Promise<PullRequestReview> {
    return request<PullRequestReview>(`/reviews/${id}`);
  },

  async getMetrics(repoId?: number): Promise<ReviewMetricsSummary> {
    const query = repoId ? `?repo_id=${repoId}` : "";
    return request<ReviewMetricsSummary>(`/reviews/metrics/summary${query}`);
  },

  async simulateReview(): Promise<{ message: string; review_id: number; pr_number: number }> {
    return request<{ message: string; review_id: number; pr_number: number }>("/reviews/simulate", {
      method: "POST",
    });
  },
};
