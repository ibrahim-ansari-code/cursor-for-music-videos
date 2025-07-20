import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { getChatHistory, streamChatMessage, clearChatHistory } from '../utils/api/ai';
import LoadingSpinner from './LoadingSpinner';

// UI Constants
const MESSAGE_MAX_WIDTH = '70%';
const SCROLL_TIMEOUT_MS = 100;

// Modern markdown components with sleek design matching platform aesthetics
const markdownComponents = {
  p: ({node, ...props}) => <p className="mb-4 last:mb-0 leading-relaxed" {...props} />,
  code: ({node, inline, className, children, ...props}) => {
    if (inline) {
      return <code className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-mono text-sm font-medium" {...props}>{children}</code>
    }
    return <code className="block bg-slate-50 p-4 rounded-xl text-sm overflow-x-auto border border-slate-200 font-mono" {...props}>{children}</code>
  },
  pre: ({node, ...props}) => <pre className="bg-slate-50 p-4 rounded-xl overflow-x-auto border border-slate-200" {...props} />,
  ul: ({node, ...props}) => <ul className="list-none space-y-3 mb-5 pl-0" {...props} />,
  ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-3 mb-5 pl-4" {...props} />,
  li: ({node, children, ...props}) => {
    // Modern bullet styling with subtle design
    return (
      <li className="flex items-start space-x-3 group" {...props}>
        <span className="flex-shrink-0 w-1.5 h-1.5 bg-blue-500 rounded-full mt-2.5 group-hover:bg-blue-600 transition-colors"></span>
        <span className="flex-1 text-gray-700">{children}</span>
      </li>
    )
  },
  blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-blue-500 pl-4 py-3 bg-blue-50/50 italic rounded-r-lg my-4" {...props} />,
  h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-4 text-gray-900 border-b border-gray-100 pb-3" {...props} />,
  h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-4 text-gray-900 mt-6" {...props} />,
  h3: ({node, ...props}) => <h3 className="text-lg font-semibold mb-3 text-gray-800 mt-5" {...props} />,
  h4: ({node, ...props}) => <h4 className="text-sm font-semibold mb-2 text-gray-600 uppercase tracking-wider" {...props} />,
  table: ({node, ...props}) => (
    <div className="overflow-x-auto mb-6 rounded-xl border border-gray-200 shadow-sm">
      <table className="min-w-full border-collapse" {...props} />
    </div>
  ),
  th: ({node, ...props}) => <th className="border-b border-gray-200 px-4 py-3 bg-gray-50/80 font-semibold text-left text-sm text-gray-700" {...props} />,
  td: ({node, ...props}) => <td className="border-b border-gray-100 px-4 py-3 text-sm text-gray-700" {...props} />,
  a: ({node, ...props}) => <a className="text-blue-600 hover:text-blue-700 font-medium transition-colors duration-200 underline decoration-blue-200 hover:decoration-blue-400" target="_blank" rel="noopener noreferrer" {...props} />,
  // Modern financial data styling
  strong: ({node, children, ...props}) => {
    const text = typeof children === 'string' ? children : children?.toString() || '';
    // Detect financial amounts and style them with modern design
    if (text.match(/\$[\d,]+(?:\.\d{2})?/)) {
      // Different styling based on context/amount
      const amount = parseFloat(text.replace(/[$,]/g, ''));
      const isLarge = amount >= 1000;
      const isOverdue = text.toLowerCase().includes('overdue') || props.className?.includes('overdue');
      
      if (isOverdue) {
        return <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-red-50 text-red-700 font-semibold text-sm border border-red-100" {...props}>{children}</span>
      } else if (isLarge) {
        return <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 font-semibold text-sm border border-emerald-100" {...props}>{children}</span>
      } else {
        return <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 font-medium text-sm" {...props}>{children}</span>
      }
    }
    return <strong className="font-semibold text-gray-900" {...props}>{children}</strong>
  }
};

// Enhanced content preprocessor for better markdown formatting
const preprocessAIContent = (content) => {
  if (!content) return '';
  
  // Handle tool execution status messages differently
  if (content.includes('🔧') || content.includes('🤖')) {
    return content; // Keep tool status messages as-is
  }
  
  // Handle ugly tool output text - clean up tool execution artifacts
  if (content.includes('Executing tools...') || content.includes('Processing results...')) {
    // Remove the tool execution status text completely
    content = content
      .replace(/🔧\s*Executing tools\.\.\./g, '')
      .replace(/🤖\s*Processing results\.\.\./g, '')
      .replace(/😎/g, '')
      .trim();
    
    // If content is empty after cleaning, return empty to prevent showing empty bubbles
    if (!content) {
      return '';
    }
  }
  
  // Convert bullet characters to proper markdown
  let processed = content
    .replace(/• /g, '- ')
    .replace(/◦ /g, '  - ')
    .replace(/▪ /g, '- ')
    .replace(/‣ /g, '- ');
    
  // Convert sections with colons to headers
  processed = processed.replace(/^([A-Z][A-Za-z\s]+):\s*$/gm, '## $1\n');
  
  // Improve financial formatting - wrap dollar amounts in bold with context
  processed = processed.replace(/\$[\d,]+(?:\.\d{2})?(\s*\([^)]*overdue[^)]*\))?/gi, '**$&**');
  
  // Convert "Summary:" or similar patterns to h3
  processed = processed.replace(/^(Summary|Recommendations?|Details?|Revenue|Income|Expenses?|Properties?|Units?|Tenants?):\s*$/gmi, '### $1\n');
  
  // Add proper spacing around lists
  processed = processed.replace(/\n-/g, '\n\n-');
  
  // Clean up multiple newlines
  processed = processed.replace(/\n{3,}/g, '\n\n');
  
  return processed.trim();
};

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const isTyping = message.isStreaming && message.content === '';
  const isToolStatus = !isUser && (message.isToolStatus || (message.content?.includes('🔧') || message.content?.includes('🤖')));
  
  // Preprocess AI content for better formatting
  const processedContent = isUser ? message.content : preprocessAIContent(message.content);
  
  // Don't render empty messages
  if (!processedContent && !isTyping) {
    return null;
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div 
        className={`px-5 py-4 rounded-2xl shadow-sm ${
          isUser ? 'bg-blue-600 text-white' : 
          isError ? 'bg-red-50 text-red-700 border border-red-100' : 
          isToolStatus ? 'bg-amber-50 text-amber-700 border border-amber-100' :
          'bg-white text-gray-800 border border-gray-100'
        }`}
        style={{ maxWidth: MESSAGE_MAX_WIDTH }}
      >
        <div className="flex items-start space-x-2">
          {isTyping ? (
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <div className={`flex-1 ${isUser ? 'prose-invert' : 'prose ai-message-content'} prose-sm max-w-none prose-gray`}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={markdownComponents}
              >
                {processedContent}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <p className={`text-xs mt-2 ${
          isUser ? 'text-blue-200' : 
          isError ? 'text-red-500' : 
          isToolStatus ? 'text-amber-600' :
          'text-gray-400'
        }`}>
          {new Date(message.created_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};

const AskAIModal = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const messagesEndRef = useRef(null);
  const streamControllerRef = useRef(null);
  const scrollTimeoutRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    if (isStreaming) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' });
    } else {
      scrollTimeoutRef.current = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, SCROLL_TIMEOUT_MS);
    }
  }, [messages, isStreaming]);

  // Load chat history when modal opens
  useEffect(() => {
    if (isOpen) {
      loadChatHistory();
    } else {
      // Reset loading state when modal closes
      setIsLoadingHistory(true);
    }
    return cleanup;
  }, [isOpen]);

  const loadChatHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const history = await getChatHistory();
      setMessages(history.messages || []);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const cleanup = () => {
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
      streamControllerRef.current = null;
    }
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
      scrollTimeoutRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleSendWithText = async (messageText) => {
    if (!messageText.trim() || isStreaming || isLoadingHistory) return;

    const userMessage = {
      role: 'user',
      content: messageText,
      created_at: new Date().toISOString()
    };

    const assistantMessageId = Date.now().toString();
    
    setMessages(prev => [...prev, userMessage, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true
    }]);
    
    setInput('');
    setIsStreaming(true);

    try {
      const abortController = await streamChatMessage(
        messageText,
        // onMessage - append content chunks
        (contentChunk) => {
          setMessages(prev => prev.map(msg => {
            if (msg.id === assistantMessageId) {
              const isToolChunk = contentChunk.includes('🔧') || contentChunk.includes('🤖');
              
              // If this is tool status, mark it as such
              if (isToolChunk) {
                return {
                  ...msg,
                  content: contentChunk,
                  isStreaming: true,
                  isToolStatus: true,
                  isTemporary: true // Mark as temporary
                };
              }
              
              // If this is actual content and we had tool status, replace it
              if (msg.isToolStatus && !isToolChunk) {
                return {
                  ...msg,
                  content: contentChunk,
                  isStreaming: true,
                  isToolStatus: false,
                  isTemporary: false
                };
              }
              
              // Normal content accumulation
              return {
                ...msg,
                content: msg.content + contentChunk,
                isStreaming: true,
                isToolStatus: false
              };
            }
            return msg;
          }));
        },
        // onError
        (error) => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { 
                  ...msg, 
                  content: 'Sorry, I encountered an error processing your request. Please try again.',
                  isError: true,
                  isStreaming: false
                }
              : msg
          ));
          setIsStreaming(false);
        },
        // onComplete
        () => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, isStreaming: false }
              : msg
          ));
          setIsStreaming(false);
        }
      );
      
      streamControllerRef.current = abortController;
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessageId 
          ? { 
              ...msg, 
              content: 'Sorry, I couldn\'t send your message. Please check your connection and try again.',
              isError: true,
              isStreaming: false
            }
          : msg
      ));
      setIsStreaming(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming || isLoadingHistory) return;
    await handleSendWithText(input);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (suggestionText) => {
    if (isStreaming || isLoadingHistory) return;
    
    // Send the suggestion text directly without relying on input state
    handleSendWithText(suggestionText);
  };

  const handleClearChat = () => {
    setShowClearConfirm(true);
  };

  const confirmClearChat = async () => {
    try {
      setShowClearConfirm(false);
      setIsLoadingHistory(true);
      
      // Clear chat history on server
      await clearChatHistory();
      
      // Clear local messages
      setMessages([]);
      
    } catch (error) {
      // Still clear local messages even if server call fails
      setMessages([]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const cancelClearChat = () => {
    setShowClearConfirm(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl h-[80vh] flex flex-col border border-gray-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className="bg-gradient-to-br from-emerald-400 to-emerald-600 px-4 py-3 rounded-xl shadow-sm">
              <i className="fas fa-robot text-white text-xl"></i>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Brikli Assistant</h2>
              <p className="text-sm text-gray-500">Your AI property management assistant</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleClearChat}
              disabled={messages.length === 0 || isStreaming || isLoadingHistory}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 rounded-lg"
              aria-label="Clear chat history"
              title="Clear chat"
            >
              <i className="fas fa-trash-alt text-lg"></i>
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all duration-200 rounded-lg"
              aria-label="Close chat"
            >
              <i className="fas fa-times text-xl"></i>
            </button>
          </div>
        </div>

        {/* Clear Chat Confirmation */}
        {showClearConfirm && (
          <div className="bg-amber-50 border-b border-amber-100 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-1.5 bg-amber-100 rounded-lg">
                  <i className="fas fa-exclamation-triangle text-amber-600 text-sm"></i>
                </div>
                <span className="text-sm font-medium text-amber-800">
                  Are you sure you want to clear all chat messages?
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={cancelClearChat}
                  disabled={isLoadingHistory}
                  className="px-4 py-2 text-sm bg-white text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-all duration-200 border border-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmClearChat}
                  disabled={isLoadingHistory}
                  className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-all duration-200 flex items-center space-x-2 shadow-sm"
                >
                  {isLoadingHistory && <i className="fas fa-spinner fa-spin text-xs"></i>}
                  <span>Clear All</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50/30">
          {isLoadingHistory ? (
            <LoadingSpinner message="Loading chat history..." size="medium" />
          ) : messages.length === 0 ? (
            <div className="text-center mt-12">
              <div className="bg-gradient-to-br from-blue-400 to-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                <i className="fas fa-comments text-white text-2xl"></i>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Start a conversation</h3>
              <p className="text-gray-500 mb-8">Ask about your properties, tenants, or financials</p>
              <div className="space-y-3 text-sm max-w-md mx-auto">
                <button
                  onClick={() => handleSuggestionClick("Show me all vacant properties")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 bg-white rounded-xl border border-gray-100 text-left hover:shadow-md hover:border-blue-200 hover:bg-blue-50/50 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  <span className="text-gray-600">"Show me all vacant properties"</span>
                </button>
                <button
                  onClick={() => handleSuggestionClick("What's my rental income this month?")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 bg-white rounded-xl border border-gray-100 text-left hover:shadow-md hover:border-emerald-200 hover:bg-emerald-50/50 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                  <span className="text-gray-600">"What's my rental income this month?"</span>
                </button>
                <button
                  onClick={() => handleSuggestionClick("Which leases are expiring soon?")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 bg-white rounded-xl border border-gray-100 text-left hover:shadow-md hover:border-purple-200 hover:bg-purple-50/50 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                  <span className="text-gray-600">"Which leases are expiring soon?"</span>
                </button>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <MessageBubble 
                key={message.id || `${index}-${message.role}-${message.created_at}`} 
                message={message} 
              />
            ))
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-100 px-6 py-5 bg-white rounded-b-2xl">
          <div className="flex space-x-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask about properties, tenants, maintenance..."
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-500 transition-all duration-200"
              disabled={isStreaming || isLoadingHistory}
              aria-label="Chat message input"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming || isLoadingHistory}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm flex items-center space-x-2 min-w-[80px] justify-center"
              aria-label="Send message"
            >
              {isStreaming ? (
                <i className="fas fa-spinner fa-spin"></i>
              ) : (
                <i className="fas fa-paper-plane"></i>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AskAIModal;