export interface ApiRequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
  cache?: boolean;
  cacheMaxAge?: number;
  signal?: AbortSignal;
  recaptchaAction?: string;
}

export declare function apiRequest(endpoint: string, options?: ApiRequestOptions): Promise<any>;
export declare function formatQueryString(queryString?: string): string;
export declare function uploadFile(endpoint: string, fileOrFormData: FormData | File, options?: { formKey?: string; extraFields?: Record<string, string> }): Promise<any>;
export interface ApiRequestOptions extends RequestInit {
  body?: string | FormData;
}

export function apiRequest(endpoint: string, options?: ApiRequestOptions): Promise<any>;
export function getAuthHeaders(): Record<string, string>;