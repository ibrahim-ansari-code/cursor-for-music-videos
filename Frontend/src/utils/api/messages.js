// Communication API Functions
import { apiRequest, formatQueryString } from './core';

export const fetchConversations = async () => {
  return apiRequest("/messages/conversations/");
};

export const createConversation = async (conversationData) => {
  return apiRequest("/messages/conversations/", {
    method: "POST",
    body: JSON.stringify(conversationData),
  });
};

export const fetchMessages = async (conversationId, params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.limit) queryParams.append("limit", params.limit);
  if (params.before_id) queryParams.append("before_id", params.before_id);

  const queryString = queryParams.toString();
  return apiRequest(
    `/messages/conversations/${conversationId}/messages${formatQueryString(
      queryString
    )}`
  );
};

export const sendMessage = async (messageData) => {
  return apiRequest("/messages/messages/", {
    method: "POST",
    body: JSON.stringify(messageData),
  });
};

export const markMessageAsRead = async (messageId) => {
  return apiRequest(`/messages/messages/${messageId}/read/`, {
    method: "PUT",
  });
};

export const sendAnnouncement = async (content, recipientType) => {
  const queryParams = new URLSearchParams();
  if (recipientType) queryParams.append("recipient_type", recipientType);
  
  const queryString = queryParams.toString();
  return apiRequest(`/messages/announcements${queryString ? '?' + queryString : ''}`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}; 