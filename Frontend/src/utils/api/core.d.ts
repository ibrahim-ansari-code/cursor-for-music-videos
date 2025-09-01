export interface ApiRequestOptions extends RequestInit {
  body?: string | FormData;
}

export function apiRequest(endpoint: string, options?: ApiRequestOptions): Promise<any>;
export function getAuthHeaders(): Record<string, string>;