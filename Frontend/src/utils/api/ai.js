// AI Chatbot API Functions
import { apiRequest } from './core';

export const sendChatMessage = async (messages, context, documentIds) => {
  return apiRequest("/ai/chat/", {
    method: "POST",
    body: JSON.stringify({
      messages,
      context,
      document_ids: documentIds,
    }),
  });
};

export const documentQA = async (messages, context, documentIds) => {
  return apiRequest("/ai/document-qa/", {
    method: "POST",
    body: JSON.stringify({
      messages,
      document_ids: documentIds,
      context,
    }),
  });
};

export const getTenantSupport = async (messages, context) => {
  return apiRequest("/ai/tenant-support/", {
    method: "POST",
    body: JSON.stringify({
      messages,
      context,
    }),
  });
}; 