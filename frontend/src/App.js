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
  ClockIcon
} from '@heroicons/react/24/outline';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ChatMessage = ({ message, isUser }) => (
  <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
      isUser 
        ? 'bg-blue-500 text-white' 
        : 'bg-gray-200 text-gray-800'
    }`}>
      <p className="text-sm whitespace-pre-line">{message}</p>
    </div>
  </div>
);

const ClusterStatus = ({ operation }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Cluster Operation</h3>
        <div className="flex items-center space-x-2">
          {getStatusIcon(operation.status)}
          <span className={`text-sm font-medium ${
            operation.status === 'success' ? 'text-green-600' : 
            operation.status === 'failed' ? 'text-red-600' : 'text-yellow-600'
          }`}>
            {operation.status.toUpperCase()}
          </span>
        </div>
      </div>
      
      {operation.data && operation.data.dns_records && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">DNS Records Created:</h4>
          <div className="space-y-2">
            {operation.data.dns_records.map((record, index) => (
              <div key={index} className="flex justify-between items-center text-sm bg-gray-50 p-2 rounded">
                <span className="font-mono">{record.fqdn}</span>
                <span className="text-gray-600">{record.ip}</span>
                <span className={`px-2 py-1 rounded text-xs ${
                  record.status === 'created' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {record.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const DNSRecordForm = ({ onSubmit, loading }) => {
  const [fqdn, setFqdn] = useState('');
  const [ipAddress, setIpAddress] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (fqdn && ipAddress) {
      onSubmit({ fqdn, ip_address: ipAddress });
      setFqdn('');
      setIpAddress('');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <ServerIcon className="h-5 w-5 mr-2 text-blue-500" />
        Create Individual DNS Record
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            FQDN (Fully Qualified Domain Name)
          </label>
          <input
            type="text"
            value={fqdn}
            onChange={(e) => setFqdn(e.target.value)}
            placeholder="node-01.cluster.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            IP Address
          </label>
          <input
            type="text"
            value={ipAddress}
            onChange={(e) => setIpAddress(e.target.value)}
            placeholder="192.168.1.10"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Creating...' : 'Create DNS Record'}
        </button>
      </form>
    </div>
  );
};

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [operations, setOperations] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [dnsLoading, setDnsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadChatHistory();
    loadOperations();
  }, []);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat-history`);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const loadOperations = async () => {
    try {
      const response = await axios.get(`${API}/operations`);
      setOperations(response.data.operations || []);
    } catch (error) {
      console.error('Error loading operations:', error);
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
      // Check if message contains Google Sheets URL
      if (inputMessage.includes('google.com/spreadsheets') || inputMessage.includes('docs.google.com')) {
        // Process as cluster creation
        const clusterResponse = await axios.post(`${API}/process-cluster`, {
          sheets_url: inputMessage,
          action: 'create_cluster'
        });
        
        const assistantMessage = {
          id: uuidv4(),
          message: clusterResponse.data.status === 'success' 
            ? 'Successfully processed your OpenShift cluster request! Check the Operations tab for details.'
            : `Failed to process cluster request: ${clusterResponse.data.error || 'Unknown error'}`,
          sender: 'assistant',
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        await loadOperations(); // Refresh operations
      } else {
        // Regular chat
        const response = await axios.post(`${API}/chat`, userMessage);
        setMessages(prev => [...prev, response.data]);
      }
    } catch (error) {
      const errorMessage = {
        id: uuidv4(),
        message: `Error: ${error.response?.data?.detail || error.message}`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setInputMessage('');
    }
  };

  const createDNSRecord = async (recordData) => {
    setDnsLoading(true);
    try {
      const response = await axios.post(`${API}/create-dns-record`, recordData);
      
      const successMessage = {
        id: uuidv4(),
        message: `DNS record created successfully!\nFQDN: ${response.data.fqdn}\nIP: ${response.data.ip_address}`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, successMessage]);
    } catch (error) {
      const errorMessage = {
        id: uuidv4(),
        message: `Failed to create DNS record: ${error.response?.data?.detail || error.message}`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setDnsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-6xl mx-auto p-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <CloudIcon className="h-8 w-8 text-blue-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-800">OpenShift Cluster Manager</h1>
                <p className="text-gray-600">AI-powered DNS management for OpenShift clusters</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <CogIcon className="h-6 w-6 text-gray-400" />
              <span className="text-sm text-gray-500">Infoblox + OLLAMA</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'chat' 
                ? 'bg-blue-500 text-white' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Chat Assistant
          </button>
          <button
            onClick={() => setActiveTab('dns')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'dns' 
                ? 'bg-blue-500 text-white' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            DNS Records
          </button>
          <button
            onClick={() => setActiveTab('operations')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'operations' 
                ? 'bg-blue-500 text-white' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Operations
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chat Interface */}
            <div className="bg-white rounded-lg shadow-md">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold">Chat with Assistant</h2>
              </div>
              
              <div className="h-96 overflow-y-auto p-4">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-500 mt-8">
                    <p>Welcome! I can help you:</p>
                    <ul className="mt-4 space-y-2 text-sm">
                      <li>• Create OpenShift cluster DNS records from Google Sheets</li>
                      <li>• Parse cluster information from spreadsheets</li>
                      <li>• Manage individual DNS records</li>
                    </ul>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <ChatMessage
                      key={msg.id}
                      message={msg.message}
                      isUser={msg.sender === 'user'}
                    />
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              <form onSubmit={sendMessage} className="p-4 border-t">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Paste Google Sheets URL or ask a question..."
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
                  >
                    {loading ? (
                      <ClockIcon className="h-5 w-5 animate-spin" />
                    ) : (
                      <PaperAirplaneIcon className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Instructions */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">How to Use</h3>
              
              <div className="space-y-4">
                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-medium">1. OpenShift Cluster Creation</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Share a Google Sheets URL containing cluster information. The AI will parse FQDN, subnet, and node IPs to create DNS records.
                  </p>
                </div>
                
                <div className="border-l-4 border-green-500 pl-4">
                  <h4 className="font-medium">2. Individual DNS Records</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Use the DNS Records tab to create individual host records by providing FQDN and IP address.
                  </p>
                </div>
                
                <div className="border-l-4 border-purple-500 pl-4">
                  <h4 className="font-medium">3. IP Allocation Logic</h4>
                  <p className="text-sm text-gray-600 mt-1">
                    First 3 IPs → master-00, master-01, master-02<br />
                    Remaining IPs → worker-00, worker-01, etc.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'dns' && (
          <div className="max-w-2xl mx-auto">
            <DNSRecordForm onSubmit={createDNSRecord} loading={dnsLoading} />
          </div>
        )}

        {activeTab === 'operations' && (
          <div className="space-y-4">
            {operations.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>No operations yet. Create your first OpenShift cluster!</p>
              </div>
            ) : (
              operations.map((operation) => (
                <ClusterStatus key={operation.id} operation={operation} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;