import React, { useState, useEffect, useRef, useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import {
  fetchConversations,
  fetchMessages,
  sendMessage,
  markMessageAsRead,
  createConversation,
  sendAnnouncement,
} from "../utils/api";

const Messages = () => {
  const { user } = useContext(AuthContext);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [messageText, setMessageText] = useState("");
  const [error, setError] = useState(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [showNewMessageModal, setShowNewMessageModal] = useState(false);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [recipients, setRecipients] = useState([]);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [announcementText, setAnnouncementText] = useState("");
  const [selectedRecipientType, setSelectedRecipientType] = useState("");

  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadConversations();

    // In a real app, we would load users from API
    setAvailableUsers([
      { id: 1, name: "John Doe", email: "john@example.com", type: "tenant" },
      {
        id: 2,
        name: "Jane Smith",
        email: "jane@example.com",
        type: "landlord",
      },
      {
        id: 3,
        name: "Robert Johnson",
        email: "robert@example.com",
        type: "tenant",
      },
      {
        id: 4,
        name: "Mary Williams",
        email: "mary@example.com",
        type: "vendor",
      },
      {
        id: 5,
        name: "James Brown",
        email: "james@example.com",
        type: "tenant",
      },
    ]);
  }, []);

  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    }
  }, [selectedConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const data = await fetchConversations();
      setConversations(data);

      // If there are conversations and none is selected, select the first one
      if (data.length > 0 && !selectedConversation) {
        setSelectedConversation(data[0]);
      }

      setError(null);
    } catch (err) {
      console.error("Error loading conversations:", err);
      setError("Failed to load conversations. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      setLoadingMessages(true);
      const data = await fetchMessages(conversationId);
      setMessages(data);
      setError(null);
    } catch (err) {
      console.error("Error loading messages:", err);
      setError("Failed to load messages. Please try again.");
    } finally {
      setLoadingMessages(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!messageText.trim() || !selectedConversation) return;

    try {
      const messageData = {
        content: messageText,
        conversation_id: selectedConversation.id,
        message_type: "direct",
      };

      await sendMessage(messageData);
      setMessageText("");

      // Refresh messages
      await loadMessages(selectedConversation.id);

      // Refresh conversations to update latest message
      await loadConversations();
    } catch (err) {
      console.error("Error sending message:", err);
      setError("Failed to send message. Please try again.");
    }
  };

  const handleOpenNewMessageModal = () => {
    setShowNewMessageModal(true);
    setRecipients([]);
  };

  const handleOpenAnnouncementModal = () => {
    setShowAnnouncementModal(true);
    setAnnouncementText("");
    setSelectedRecipientType("");
  };

  const handleCreateConversation = async () => {
    if (recipients.length === 0) return;

    try {
      const conversationData = {
        is_group: recipients.length > 1,
        title: recipients.length > 1 ? "Group Conversation" : null,
        participant_ids: [...recipients.map((r) => r.id), user.id],
      };

      const newConversation = await createConversation(conversationData);

      // Close modal and refresh conversations
      setShowNewMessageModal(false);
      await loadConversations();

      // Select the new conversation
      setSelectedConversation(newConversation);
    } catch (err) {
      console.error("Error creating conversation:", err);
      setError("Failed to create conversation. Please try again.");
    }
  };

  const handleSendAnnouncement = async () => {
    if (!announcementText.trim()) return;

    try {
      await sendAnnouncement(
        announcementText,
        selectedRecipientType || undefined
      );

      // Close modal and refresh conversations
      setShowAnnouncementModal(false);
      setAnnouncementText("");
      setSelectedRecipientType("");

      await loadConversations();
    } catch (err) {
      console.error("Error sending announcement:", err);
      setError("Failed to send announcement. Please try again.");
    }
  };

  const handleSelectRecipient = (user) => {
    // Check if the user is already selected
    if (recipients.some((r) => r.id === user.id)) {
      // Remove user from recipients
      setRecipients(recipients.filter((r) => r.id !== user.id));
    } else {
      // Add user to recipients
      setRecipients([...recipients, user]);
    }
  };

  const formatMessageTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();

    // If the message is from today, show only time
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    // If the message is from this year, show date without year
    if (date.getFullYear() === now.getFullYear()) {
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    }

    // Otherwise show full date
    return date.toLocaleDateString();
  };

  if (loading && conversations.length === 0) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-3 text-gray-600">Loading conversations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-900">Messages</h1>

        <div className="space-x-3">
          {(user?.user_type === "admin" || user?.user_type === "landlord") && (
            <button
              onClick={handleOpenAnnouncementModal}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
            >
              <i className="fas fa-bullhorn mr-2"></i>
              Announcement
            </button>
          )}

          <button
            onClick={handleOpenNewMessageModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Message
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p>{error}</p>
          <button
            onClick={() => {
              if (selectedConversation) loadMessages(selectedConversation.id);
              else loadConversations();
            }}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex">
        {/* Conversations List */}
        <div className="w-full sm:w-1/3 md:w-1/4 border-r border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <div className="relative rounded-md shadow-sm">
              <input
                type="search"
                placeholder="Search messages..."
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400"></i>
              </div>
            </div>
          </div>

          <div className="overflow-y-auto h-[calc(100vh-13rem)]">
            {conversations.length > 0 ? (
              conversations
                .filter((conv) => {
                  if (!searchTerm) return true;
                  // Search in conversation title or latest message
                  return (
                    (conv.title &&
                      conv.title
                        .toLowerCase()
                        .includes(searchTerm.toLowerCase())) ||
                    (conv.latest_message &&
                      conv.latest_message.content
                        .toLowerCase()
                        .includes(searchTerm.toLowerCase()))
                  );
                })
                .map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`p-4 border-b border-gray-200 cursor-pointer hover:bg-gray-50 ${
                      selectedConversation?.id === conversation.id
                        ? "bg-blue-50"
                        : ""
                    }`}
                    onClick={() => setSelectedConversation(conversation)}
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                        {conversation.is_group ? (
                          <i className="fas fa-users"></i>
                        ) : (
                          // Show first letter of other participant's name (mock)
                          "U"
                        )}
                      </div>
                      <div className="ml-3 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">
                            {conversation.title || "Direct Message"}
                          </p>
                          <p className="text-xs text-gray-500">
                            {conversation.latest_message
                              ? formatMessageTime(
                                  conversation.latest_message.created_at
                                )
                              : formatMessageTime(conversation.created_at)}
                          </p>
                        </div>
                        <p className="text-sm text-gray-500 truncate">
                          {conversation.latest_message
                            ? conversation.latest_message.content
                            : "No messages yet"}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
            ) : (
              <div className="p-4 text-center text-gray-500">
                No conversations found
              </div>
            )}
          </div>
        </div>

        {/* Messages Area */}
        <div className="w-full sm:w-2/3 md:w-3/4 flex flex-col">
          {selectedConversation ? (
            <>
              {/* Conversation Header */}
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                    {selectedConversation.is_group ? (
                      <i className="fas fa-users"></i>
                    ) : (
                      // Show first letter of other participant's name (mock)
                      "U"
                    )}
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-900">
                      {selectedConversation.title || "Direct Message"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {selectedConversation.is_group
                        ? `${selectedConversation.participants.length} participants`
                        : "Online"}
                    </p>
                  </div>
                </div>

                <div className="flex space-x-2">
                  <button className="text-gray-400 hover:text-gray-500">
                    <i className="fas fa-phone"></i>
                  </button>
                  <button className="text-gray-400 hover:text-gray-500">
                    <i className="fas fa-video"></i>
                  </button>
                  <button className="text-gray-400 hover:text-gray-500">
                    <i className="fas fa-ellipsis-v"></i>
                  </button>
                </div>
              </div>

              {/* Messages List */}
              <div className="flex-1 p-4 overflow-y-auto">
                {loadingMessages ? (
                  <div className="flex justify-center items-center h-full">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : messages.length > 0 ? (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${
                          message.sender_id === user?.id
                            ? "justify-end"
                            : "justify-start"
                        }`}
                      >
                        <div
                          className={`max-w-xs sm:max-w-md rounded-lg px-4 py-2 ${
                            message.sender_id === user?.id
                              ? "bg-blue-600 text-white"
                              : message.message_type === "announcement"
                              ? "bg-purple-100 text-purple-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {message.message_type === "announcement" && (
                            <div className="flex items-center mb-1 text-purple-600">
                              <i className="fas fa-bullhorn mr-1 text-xs"></i>
                              <span className="text-xs font-semibold">
                                Announcement
                              </span>
                            </div>
                          )}
                          <p>{message.content}</p>
                          <p
                            className={`text-xs mt-1 ${
                              message.sender_id === user?.id
                                ? "text-blue-200"
                                : message.message_type === "announcement"
                                ? "text-purple-600"
                                : "text-gray-500"
                            }`}
                          >
                            {formatMessageTime(message.created_at)}
                            {message.sender_id === user?.id &&
                              message.is_read && (
                                <span className="ml-1">
                                  <i className="fas fa-check-double"></i>
                                </span>
                              )}
                          </p>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                ) : (
                  <div className="flex justify-center items-center h-full text-gray-500">
                    No messages yet
                  </div>
                )}
              </div>

              {/* Message Input */}
              <div className="p-4 border-t border-gray-200">
                <form
                  onSubmit={handleSendMessage}
                  className="flex items-center"
                >
                  <button
                    type="button"
                    className="text-gray-400 hover:text-gray-500 mr-3"
                  >
                    <i className="fas fa-paperclip"></i>
                  </button>
                  <input
                    type="text"
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 focus:ring-blue-500 focus:border-blue-500 block w-full min-w-0 rounded-md sm:text-sm border-gray-300"
                  />
                  <button
                    type="submit"
                    disabled={!messageText.trim()}
                    className="ml-3 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    <i className="fas fa-paper-plane mr-2"></i>
                    Send
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <i className="fas fa-comments text-5xl mb-4"></i>
              <p>Select a conversation to view messages</p>
              <button
                onClick={handleOpenNewMessageModal}
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <i className="fas fa-plus mr-2"></i>
                Start New Conversation
              </button>
            </div>
          )}
        </div>
      </div>

      {/* New Message Modal */}
      {showNewMessageModal && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">New Message</h3>
              <button
                onClick={() => setShowNewMessageModal(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Recipients
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search for users..."
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-3 pr-10 py-2 border-gray-300 rounded-md text-sm"
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <i className="fas fa-search text-gray-400"></i>
                </div>
              </div>

              {/* Selected recipients */}
              {recipients.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {recipients.map((recipient) => (
                    <div
                      key={recipient.id}
                      className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm flex items-center"
                    >
                      <span>{recipient.name}</span>
                      <button
                        type="button"
                        onClick={() => handleSelectRecipient(recipient)}
                        className="ml-1 text-blue-600 hover:text-blue-800"
                      >
                        <i className="fas fa-times-circle"></i>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
              {availableUsers
                .filter((user) => user.id !== (user?.id || 0)) // Filter out current user
                .filter(
                  (user) =>
                    user.name
                      .toLowerCase()
                      .includes(searchTerm.toLowerCase()) ||
                    user.email.toLowerCase().includes(searchTerm.toLowerCase())
                )
                .map((user) => (
                  <div
                    key={user.id}
                    className={`p-3 border-b border-gray-200 flex items-center justify-between cursor-pointer hover:bg-gray-50 last:border-b-0 ${
                      recipients.some((r) => r.id === user.id)
                        ? "bg-blue-50"
                        : ""
                    }`}
                    onClick={() => handleSelectRecipient(user)}
                  >
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                        {user.name.charAt(0)}
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">
                          {user.name}
                        </p>
                        <p className="text-xs text-gray-500">{user.email}</p>
                      </div>
                    </div>

                    {recipients.some((r) => r.id === user.id) && (
                      <div className="text-blue-600">
                        <i className="fas fa-check-circle"></i>
                      </div>
                    )}
                  </div>
                ))}

              {availableUsers.filter(
                (user) =>
                  user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  user.email.toLowerCase().includes(searchTerm.toLowerCase())
              ).length === 0 && (
                <div className="p-4 text-center text-gray-500">
                  No users found
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setShowNewMessageModal(false)}
                className="mr-3 inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateConversation}
                disabled={recipients.length === 0}
                className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                Start Conversation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Announcement Modal */}
      {showAnnouncementModal && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Send Announcement</h3>
              <button
                onClick={() => setShowAnnouncementModal(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Recipient Type (Optional)
              </label>
              <select
                className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={selectedRecipientType}
                onChange={(e) => setSelectedRecipientType(e.target.value)}
              >
                <option value="">All Users</option>
                <option value="tenant">Tenants Only</option>
                <option value="landlord">Landlords Only</option>
                <option value="vendor">Vendors Only</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Announcement Message
              </label>
              <textarea
                className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
                rows="4"
                value={announcementText}
                onChange={(e) => setAnnouncementText(e.target.value)}
                placeholder="Type your announcement here..."
                required
              ></textarea>
            </div>

            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <i className="fas fa-exclamation-triangle text-yellow-400"></i>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700">
                    This announcement will be sent to{" "}
                    {selectedRecipientType || "all users"} and cannot be
                    recalled.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setShowAnnouncementModal(false)}
                className="mr-3 inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSendAnnouncement}
                disabled={!announcementText.trim()}
                className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md shadow-sm hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50"
              >
                Send Announcement
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Messages;
