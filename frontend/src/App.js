import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { 
  PaperAirplaneIcon, 
  CloudIcon, 
  ServerIcon, 
  CogIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  SparklesIcon,
  DocumentTextIcon,
  TableCellsIcon
} from '@heroicons/react/24/outline';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ChatMessage = ({ message, isUser }) => (
  <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
    <div className={`max-w-4xl px-6 py-4 rounded-lg ${
      isUser 
        ? 'bg-blue-500 text-white' 
        : 'bg-gray-100 text-gray-800'
    }`}>
      <div className="flex items-start space-x-3">
        {!isUser && (
          <div className="flex-shrink-0 mt-1">
            <SparklesIcon className="h-5 w-5 text-blue-500" />
          </div>
        )}
        <div className="flex-1">
          <p className="text-sm whitespace-pre-line leading-relaxed">{message.message}</p>
          {message.table_data && message.table_data.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(message.table_data[0]).map((header) => (
                      <th key={header} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {message.table_data.map((row, index) => (
                    <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      {Object.values(row).map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-4 py-2 text-sm text-gray-900 border-b">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  </div>
);

const WelcomeMessage = () => (
  <div className="text-center py-12 px-6">
    <div className="max-w-2xl mx-auto">
      <div className="flex justify-center mb-6">
        <div className="bg-blue-100 p-4 rounded-full">
          <CloudIcon className="h-12 w-12 text-blue-600" />
        </div>
      </div>
      
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        Welcome to OpenShift Cluster Manager
      </h2>
      
      <p className="text-gray-600 mb-8">
        AI-powered DNS management for OpenShift clusters with Google Gemini and Infoblox integration
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
        <div className="bg-blue-50 p-6 rounded-lg">
          <div className="flex items-center mb-3">
            <ServerIcon className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-800">Create Cluster</h3>
          </div>
          <p className="text-sm text-gray-600 mb-2">
            "Hey, I want to build new openshift cluster, details are at google sheet &lt;link&gt;"
          </p>
          <span className="text-xs text-blue-600">Parses sheets → Allocates IPs → Creates DNS</span>
        </div>
        
        <div className="bg-green-50 p-6 rounded-lg">
          <div className="flex items-center mb-3">
            <DocumentTextIcon className="h-5 w-5 text-green-600 mr-2" />
            <h3 className="font-semibold text-gray-800">Create DNS Record</h3>
          </div>
          <p className="text-sm text-gray-600 mb-2">
            "Hey, can you create a DNS A record for IP 1.2.3.4 and FQDN is abc.com"
          </p>
          <span className="text-xs text-green-600">Direct DNS record creation</span>
        </div>
        
        <div className="bg-purple-50 p-6 rounded-lg">
          <div className="flex items-center mb-3">
            <TableCellsIcon className="h-5 w-5 text-purple-600 mr-2" />
            <h3 className="font-semibold text-gray-800">Parse Sheets</h3>
          </div>
          <p className="text-sm text-gray-600 mb-2">
            "Hey, can you parse google sheet at &lt;link&gt; and provide FQDN and subnet and list console IPs"
          </p>
          <span className="text-xs text-purple-600">Extract cluster information</span>
        </div>
        
        <div className="bg-orange-50 p-6 rounded-lg">
          <div className="flex items-center mb-3">
            <CogIcon className="h-5 w-5 text-orange-600 mr-2" />
            <h3 className="font-semibold text-gray-800">Allocate IPs</h3>
          </div>
          <p className="text-sm text-gray-600 mb-2">
            "Hey, allocate IPs for all the nodes listed in google sheet &lt;link&gt; with the subnet"
          </p>
          <span className="text-xs text-orange-600">IP allocation with subnet mapping</span>
        </div>
      </div>
      
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600">
          <strong>💡 Tip:</strong> Just type your request naturally! I'll understand your intent and help you manage your OpenShift infrastructure.
        </p>
      </div>
    </div>
  </div>
);

const TypingIndicator = () => (
  <div className="flex justify-start mb-6">
    <div className="bg-gray-100 px-6 py-4 rounded-lg">
      <div className="flex items-center space-x-2">
        <SparklesIcon className="h-5 w-5 text-blue-500" />
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
        <span className="text-sm text-gray-600">Processing your request...</span>
      </div>
    </div>
  </div>
);

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat-history`);
      const history = response.data.messages || [];
      setMessages(history);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: uuidv4(),
      message: inputMessage,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, userMessage);
      setMessages(prev => [...prev, response.data]);
    } catch (error) {
      const errorMessage = {
        id: uuidv4(),
        message: `❌ Error: ${error.response?.data?.detail || error.message}`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white shadow-sm border-b">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <CloudIcon className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-800">OpenShift Cluster Manager</h1>
                  <p className="text-gray-600">AI-powered DNS management with Google Gemini</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Gemini 2.0 Flash</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <ServerIcon className="h-4 w-4" />
                  <span>Infoblox Ready</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex flex-col h-[calc(100vh-120px)]">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {messages.length === 0 ? (
              <WelcomeMessage />
            ) : (
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  isUser={msg.sender === 'user'}
                />
              ))
            )}
            
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <div className="border-t bg-white px-6 py-4">
            <form onSubmit={sendMessage} className="flex space-x-4">
              <div className="flex-1">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your request... (e.g., 'I want to build openshift cluster, details are at google sheet https://...')"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows="3"
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition-colors flex items-center space-x-2"
              >
                {loading ? (
                  <>
                    <ClockIcon className="h-5 w-5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <PaperAirplaneIcon className="h-5 w-5" />
                    <span>Send</span>
                  </>
                )}
              </button>
            </form>
            
            <div className="mt-2 text-xs text-gray-500">
              Press Enter to send, Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;