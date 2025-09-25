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
      return <code className="bg-slate-100 dark:bg-gray-700 text-slate-700 dark:text-gray-200 px-2 py-0.5 rounded-md font-mono text-sm font-medium transition-colors" {...props}>{children}</code>
    }
    return <code className="block bg-slate-50 dark:bg-gray-800 p-4 rounded-xl text-sm overflow-x-auto border border-slate-200 dark:border-gray-600 font-mono transition-colors" {...props}>{children}</code>
  },
  pre: ({node, ...props}) => <pre className="bg-slate-50 dark:bg-gray-800 p-4 rounded-xl overflow-x-auto border border-slate-200 dark:border-gray-600 transition-colors" {...props} />,
  ul: ({node, ...props}) => <ul className="list-none space-y-3 mb-5 pl-0" {...props} />,
  ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-3 mb-5 pl-4" {...props} />,
  li: ({node, children, ...props}) => {
    // Modern bullet styling with subtle design
    return (
      <li className="flex items-start space-x-3 group" {...props}>
        <span className="flex-shrink-0 w-1.5 h-1.5 bg-blue-500 dark:bg-blue-400 rounded-full mt-2.5 group-hover:bg-blue-600 dark:group-hover:bg-blue-300 transition-colors"></span>
        <span className="flex-1 text-gray-700 dark:text-gray-200">{children}</span>
      </li>
    )
  },
  blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-blue-500 dark:border-blue-400 pl-4 py-3 bg-blue-50/50 dark:bg-blue-900/20 italic rounded-r-lg my-4 transition-colors" {...props} />,
  h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100 border-b border-gray-100 dark:border-gray-700 pb-3 transition-colors" {...props} />,
  h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100 mt-6 transition-colors" {...props} />,
  h3: ({node, ...props}) => <h3 className="text-lg font-semibold mb-3 text-gray-800 dark:text-gray-200 mt-5 transition-colors" {...props} />,
  h4: ({node, ...props}) => <h4 className="text-sm font-semibold mb-2 text-gray-600 dark:text-gray-400 uppercase tracking-wider transition-colors" {...props} />,
  table: ({node, ...props}) => (
    <div className="overflow-x-auto mb-6 rounded-xl border border-gray-200 dark:border-gray-600 shadow-sm transition-colors">
      <table className="min-w-full border-collapse" {...props} />
    </div>
  ),
  th: ({node, ...props}) => <th className="border-b border-gray-200 dark:border-gray-600 px-4 py-3 bg-gray-50/80 dark:bg-gray-700/80 font-semibold text-left text-sm text-gray-700 dark:text-gray-200 transition-colors" {...props} />,
  td: ({node, ...props}) => <td className="border-b border-gray-100 dark:border-gray-700 px-4 py-3 text-sm text-gray-700 dark:text-gray-200 transition-colors" {...props} />,
  a: ({node, ...props}) => <a className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors duration-200 underline decoration-blue-200 dark:decoration-blue-500 hover:decoration-blue-400 dark:hover:decoration-blue-300" target="_blank" rel="noopener noreferrer" {...props} />,
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
        return <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 font-semibold text-sm border border-red-100 dark:border-red-700 transition-colors" {...props}>{children}</span>
      } else if (isLarge) {
        return <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-semibold text-sm border border-emerald-100 dark:border-emerald-700 transition-colors" {...props}>{children}</span>
      } else {
        return <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium text-sm transition-colors" {...props}>{children}</span>
      }
    }
    return <strong className="font-semibold text-gray-900 dark:text-gray-100 transition-colors" {...props}>{children}</strong>
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
        className={`message-bubble transition-all duration-300 ${isUser ? 'user' : 'assistant'} ${
          isError ? 'bg-red-50/90 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200/50 dark:border-red-700/50' : 
          isToolStatus ? 'bg-amber-50/90 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200/50 dark:border-amber-700/50' :
          ''
        }`}
        style={{ maxWidth: MESSAGE_MAX_WIDTH }}
      >
        <div className="flex items-start space-x-2">
          {isTyping ? (
            <div className="typing-indicator flex items-center space-x-1 px-3 py-2">
              <div className="flex space-x-1.5">
                <div className="w-2 h-2 bg-green-500 dark:bg-green-400 rounded-full animate-pulse-green"></div>
                <div className="w-2 h-2 bg-green-500 dark:bg-green-400 rounded-full animate-pulse-green" style={{animationDelay: '0.2s'}}></div>
                <div className="w-2 h-2 bg-green-500 dark:bg-green-400 rounded-full animate-pulse-green" style={{animationDelay: '0.4s'}}></div>
              </div>
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
        <p className={`text-xs mt-2 transition-colors duration-300 ${
          isUser ? 'text-blue-200 dark:text-blue-300' : 
          isError ? 'text-red-500 dark:text-red-400' : 
          isToolStatus ? 'text-amber-600 dark:text-amber-400' :
          'text-gray-400 dark:text-gray-500'
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
    <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4 transition-all duration-300">
      <div className="glassmorphism-strong rounded-3xl dark-modal-shadow w-full max-w-4xl h-[80vh] flex flex-col overflow-hidden transition-all duration-300 bg-gradient-to-br from-white/95 via-white/90 to-white/85 dark:from-[#181B20]/95 dark:via-[#181B20]/90 dark:to-[#181B20]/85">
        {/* Header with glassmorphism effect */}
        <div className="px-6 py-5 dark-divider border-b flex justify-between items-center glassmorphism bg-white/40 dark:bg-[#1F2329]/40 transition-all duration-300">
          <div className="flex items-center space-x-4">
            <div className="bg-gradient-to-br from-emerald-400 to-emerald-600 px-4 py-3 rounded-xl shadow-sm">
              <i className="fas fa-robot text-white text-xl"></i>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 transition-colors duration-300">Brikli Assistant</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-300">Your AI property management assistant</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleClearChat}
              disabled={messages.length === 0 || isStreaming || isLoadingHistory}
              className="p-2 text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 rounded-lg"
              aria-label="Clear chat history"
              title="Clear chat"
            >
              <i className="fas fa-trash-alt text-lg"></i>
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200 rounded-lg"
              aria-label="Close chat"
            >
              <i className="fas fa-times text-xl"></i>
            </button>
          </div>
        </div>

        {/* Clear Chat Confirmation with glassmorphism */}
        {showClearConfirm && (
          <div className="bg-amber-50/80 dark:bg-amber-900/30 glassmorphism dark-divider border-b px-6 py-4 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-1.5 bg-amber-100 dark:bg-amber-800/50 rounded-lg transition-colors duration-300">
                  <i className="fas fa-exclamation-triangle text-amber-600 dark:text-amber-400 text-sm transition-colors duration-300"></i>
                </div>
                <span className="text-sm font-medium text-amber-800 dark:text-amber-200 transition-colors duration-300">
                  Are you sure you want to clear all chat messages?
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={cancelClearChat}
                  disabled={isLoadingHistory}
                  className="px-4 py-2 text-sm bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-all duration-200 border border-gray-200 dark:border-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmClearChat}
                  disabled={isLoadingHistory}
                  className="px-4 py-2 text-sm bg-red-600 dark:bg-red-500 text-white rounded-lg hover:bg-red-700 dark:hover:bg-red-600 disabled:opacity-50 transition-all duration-200 flex items-center space-x-2 shadow-sm"
                >
                  {isLoadingHistory && <i className="fas fa-spinner fa-spin text-xs"></i>}
                  <span>Clear All</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Messages with enhanced glassmorphism background */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 glassmorphism bg-gradient-to-br from-gray-50/30 via-white/20 to-gray-100/30 dark:from-[#0E0F11]/30 dark:via-[#181B20]/20 dark:to-[#1F2329]/30 transition-all duration-300">
          {isLoadingHistory ? (
            <LoadingSpinner message="Loading chat history..." size="medium" />
          ) : messages.length === 0 ? (
            <div className="text-center mt-12">
              <div className="bg-gradient-to-br from-blue-400 to-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                <i className="fas fa-comments text-white text-2xl"></i>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 transition-colors duration-300">Start a conversation</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-8 transition-colors duration-300">Ask about your properties, tenants, or financials</p>
              <div className="space-y-3 text-sm max-w-md mx-auto">
                <button
                  onClick={() => handleSuggestionClick("Show me all vacant properties")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 dark-panel rounded-xl dark-divider border text-left hover:shadow-md hover:border-blue-200 dark:hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-blue-400 dark:bg-blue-500 rounded-full transition-colors duration-300"></div>
                  <span className="text-gray-600 dark:text-gray-300 transition-colors duration-300">"Show me all vacant properties"</span>
                </button>
                <button
                  onClick={() => handleSuggestionClick("What's my rental income this month?")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 dark-panel rounded-xl dark-divider border text-left hover:shadow-md hover:border-emerald-200 dark:hover:border-emerald-500 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/20 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-emerald-400 dark:bg-emerald-500 rounded-full transition-colors duration-300"></div>
                  <span className="text-gray-600 dark:text-gray-300 transition-colors duration-300">"What's my rental income this month?"</span>
                </button>
                <button
                  onClick={() => handleSuggestionClick("Which leases are expiring soon?")}
                  disabled={isStreaming || isLoadingHistory}
                  className="flex items-center space-x-3 p-3 dark-panel rounded-xl dark-divider border text-left hover:shadow-md hover:border-purple-200 dark:hover:border-purple-500 hover:bg-purple-50/50 dark:hover:bg-purple-900/20 transition-all duration-200 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="w-2 h-2 bg-purple-400 dark:bg-purple-500 rounded-full transition-colors duration-300"></div>
                  <span className="text-gray-600 dark:text-gray-300 transition-colors duration-300">"Which leases are expiring soon?"</span>
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

        {/* Input with glassmorphism footer */}
        <div className="dark-divider border-t px-6 py-5 glassmorphism bg-white/80 dark:bg-[#1F2329]/80 rounded-b-3xl transition-all duration-300">
          <div className="flex space-x-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask about properties, tenants, maintenance..."
              className="flex-1 px-4 py-3 dark-divider border glassmorphism bg-white/70 dark:bg-[#1F2329]/70 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 dark:focus:ring-blue-400/50 focus:border-blue-500/50 dark:focus:border-blue-400/50 disabled:bg-gray-50/50 dark:disabled:bg-gray-800/50 disabled:text-gray-500 dark:disabled:text-gray-500 transition-all duration-200 dark-shadow"
              disabled={isStreaming || isLoadingHistory}
              aria-label="Chat message input"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming || isLoadingHistory}
              className="px-6 py-3 bg-blue-600/90 dark:bg-blue-500/90 backdrop-blur-sm text-white rounded-xl hover:bg-blue-700/90 dark:hover:bg-blue-600/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg border border-blue-500/30 flex items-center space-x-2 min-w-[80px] justify-center"
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