// AI Agent API Functions
import { apiRequest } from './core';
import { fetchEventSource } from '@microsoft/fetch-event-source';

// API Constants
const DEFAULT_CHAT_HISTORY_LIMIT = 20;

// SSE Message Types (match backend)
const SSE_MESSAGE_TYPES = {
  CONTENT: 'content',
  ERROR: 'error',
  DONE: 'done',
  STATUS: 'status'
};

export const getChatHistory = async (limit = DEFAULT_CHAT_HISTORY_LIMIT) => {
  return apiRequest(`/agent/chat/history?limit=${limit}`, {
    method: "GET",
  });
};

export const getConversations = async () => {
  return apiRequest("/agent/conversations", {
    method: "GET",
  });
};

export const clearChatHistory = async () => {
  return apiRequest("/agent/chat/clear", {
    method: "POST",
  });
};

// Streaming chat using Microsoft's fetch-event-source for better SSE handling
export const streamChatMessage = async (message, onMessage, onError, onComplete) => {
  const token = localStorage.getItem("token");
  if (!token) {
    throw new Error("Authentication required. Please log in.");
  }

  const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
  const url = `${API_BASE_URL}/api/agent/chat/stream`;

  const abortController = new AbortController();

  try {
    await fetchEventSource(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify({ content: message }),
      signal: abortController.signal,
      
      onopen(res) {
        if (res.ok && res.headers.get('content-type')?.startsWith('text/event-stream')) {
          return; // Everything is good
        } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
          // Client-side errors are usually non-retryable
          throw new Error(`Client error: ${res.status} ${res.statusText}`);
        } else {
          // Server errors or rate limiting might be retryable
          throw new Error(`Server error: ${res.status} ${res.statusText}`);
        }
      },

      onmessage(event) {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === SSE_MESSAGE_TYPES.CONTENT) {
            onMessage?.(data.content);
          } else if (data.type === SSE_MESSAGE_TYPES.ERROR) {
            onError?.(new Error(data.error));
          } else if (data.type === SSE_MESSAGE_TYPES.DONE) {
            onComplete?.(data.total_content);
          } else if (data.type === SSE_MESSAGE_TYPES.STATUS) {
            // Handle status updates (tool execution messages)
            onMessage?.(data.status);
          } else {
            // Unknown message type - silently ignore
          }
        } catch (e) {
          // Only call onError for critical parsing failures that indicate malformed data
          if (event.data && event.data.trim() !== '') {
            onError?.(new Error(`Invalid message format: ${e.message}`));
          }
        }
      },

      onerror(err) {
        // SSE connection error - pass to error handler
        onError?.(err instanceof Error ? err : new Error('Stream connection failed'));
        throw err; // Re-throw to stop retrying if needed
      },

      onclose() {
        // SSE connection closed
        onComplete?.();
      },

      // Retry configuration
      openWhenHidden: true, // Keep connection when tab is hidden
      retryOnError: true,
    });
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error('Failed to start stream'));
  }

  return abortController; // Return controller for manual abort if needed
};

 