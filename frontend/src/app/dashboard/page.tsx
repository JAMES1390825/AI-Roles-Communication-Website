// src/app/dashboard/page.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import api, { transcribeAudio, speakText, deleteChats } from '@/api'; // 导入新的 API 函数和 transcribeAudio, deleteChats

interface Role {
  id: string;
  name: string;
  description: string;
}
interface Chat {
  id: string;
  title: string;
  role_id: string;
  created_at: string;
}

interface Message {
  id: string;
  chat_id: string;
  sender_type: 'user' | 'ai';
  content: string;
  timestamp: string;
  order_in_chat: number;
}

export default function DashboardPage() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState<string>('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 语音相关状态
  const [isRecording, setIsRecording] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const [selectedChatIds, setSelectedChatIds] = useState<string[]>([]); // 新增：用于批量删除选中的聊天ID

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
    if (user) {
      fetchRoles();
      fetchChats();
    }
  }, [user, isLoading, router]);

  useEffect(() => {
    if (currentChatId) {
      fetchMessages(currentChatId);
    }
  }, [currentChatId]);

  const fetchRoles = async () => {
    try {
      const response = await api.get<Role[]>('/roles/');
      setRoles(response.data);
      if (response.data.length > 0 && !selectedRoleId) {
        setSelectedRoleId(response.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch roles:', err);
      setError('Failed to load roles.');
    }
  };

  const fetchChats = async () => {
    try {
      const response = await api.get<Chat[]>('/chats/');
      setChats(response.data);
      // if (response.data.length > 0 && !currentChatId) {
      //   setCurrentChatId(response.data[0].id);
      // }
    } catch (err) {
      console.error('Failed to fetch chats:', err);
      setError('Failed to load chats.');
    }
  };

  const fetchMessages = async (chatId: string) => {
    try {
      const response = await api.get<Message[]>(`/chats/${chatId}/messages`);
      setMessages(response.data);
    } catch (err) {
      console.error(`Failed to fetch messages for chat ${chatId}:`, err);
      setError('Failed to load messages.');
    }
  };

  const handleCreateChat = async () => {
    if (!selectedRoleId) {
      setError('Please select a role to start a chat.');
      return;
    }
    try {
      const role = roles.find(r => r.id === selectedRoleId);
      const chatTitle = `Chat with ${role?.name || 'AI'}`;
      const response = await api.post<Chat>('/chats/', { role_id: selectedRoleId, title: chatTitle });
      setChats([...chats, response.data]);
      setCurrentChatId(response.data.id);
      setNewMessage(''); // Clear message input after creating a new chat
    } catch (err) {
      console.error('Failed to create chat:', err);
      setError('Failed to create new chat.');
    }
  };

  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId);
    setNewMessage(''); // Clear message input when switching chats
  };

  const handleCheckboxChange = (chatId: string) => {
    setSelectedChatIds((prevSelected) =>
      prevSelected.includes(chatId)
        ? prevSelected.filter((id) => id !== chatId)
        : [...prevSelected, chatId]
    );
  };

  const handleBulkDelete = async () => {
    if (selectedChatIds.length === 0) {
      alert('Please select at least one chat to delete.');
      return;
    }
    if (!confirm(`Are you sure you want to delete ${selectedChatIds.length} selected chats?`)) {
      return;
    }
    try {
      await deleteChats(selectedChatIds);
      setChats((prevChats) => prevChats.filter((chat) => !selectedChatIds.includes(chat.id)));
      if (currentChatId && selectedChatIds.includes(currentChatId)) {
        setCurrentChatId(null);
        setMessages([]);
      }
      setSelectedChatIds([]); // 清空选中状态
    } catch (err) {
      console.error('Failed to bulk delete chats:', err);
      setError('Failed to delete selected chats.');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!newMessage.trim() || !currentChatId || isSending) return;

    setIsSending(true);
    setError(null);

    const userMessage: Message = {
      id: Date.now().toString(), // Temp ID for UI
      chat_id: currentChatId,
      sender_type: 'user',
      content: newMessage,
      timestamp: new Date().toISOString(),
      order_in_chat: messages.length, // Temp order
    };
    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');

    try {
      const response = await api.post<Message>(`/chats/${currentChatId}/message`, {
        content: userMessage.content,
        sender_type: 'user',
      });
      setMessages((prev) => prev.map((msg) => (msg.id === userMessage.id ? response.data : msg)));
      // 播放 AI 回复的语音
      await playAiResponse(response.data.content);
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message.');
      setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id)); // 移除临时消息
    } finally {
      setIsSending(false);
    }
  };

  // --- 语音相关功能 ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        try {
          const transcript = await transcribeAudio(audioBlob);
          setNewMessage(transcript);
        } catch (err) {
          console.error('Error transcribing audio:', err);
          setError('Failed to transcribe audio.');
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Failed to access microphone. Please ensure it is enabled.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const playAiResponse = async (text: string) => {
    try {
      setIsPlayingAudio(true);
      const audioBlob = await speakText(text);
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = audioUrl;
        audioPlayerRef.current.play();
        audioPlayerRef.current.onended = () => {
          setIsPlayingAudio(false);
          URL.revokeObjectURL(audioUrl); // 释放URL对象
        };
        audioPlayerRef.current.onerror = (e) => {
          console.error('Audio playback error:', e);
          setError('Failed to play audio.');
          setIsPlayingAudio(false);
          URL.revokeObjectURL(audioUrl);
        };
      } else {
        // 如果 audioPlayerRef.current 不存在，创建一个新的 Audio 对象
        const newAudio = new Audio(audioUrl);
        newAudio.play();
        newAudio.onended = () => {
          setIsPlayingAudio(false);
          URL.revokeObjectURL(audioUrl);
        };
        newAudio.onerror = (e) => {
          console.error('Audio playback error:', e);
          setError('Failed to play audio.');
          setIsPlayingAudio(false);
          URL.revokeObjectURL(audioUrl);
        };
        audioPlayerRef.current = newAudio; // 将新的 Audio 对象赋值给 ref
      }
    } catch (err) {
      console.error('Error playing AI response:', err);
      setError('Failed to play AI response.');
      setIsPlayingAudio(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading user data...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="h-screen bg-gray-100 flex">
      {/* Chats Sidebar */}
      <div className="w-64 bg-white shadow-md p-4 flex flex-col">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Your Chats</h2>
        <div className="mb-4">
          <select
            className="block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            value={selectedRoleId || ''}
            onChange={(e) => setSelectedRoleId(e.target.value)}
            disabled={isSending}
          >
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
          <button
            onClick={handleCreateChat}
            className="mt-2 w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            disabled={!selectedRoleId || isSending}
          >
            New Chat
          </button>
        </div>
        <div className="mb-4">
          <button
            onClick={handleBulkDelete}
            className={`w-full py-2 px-4 rounded-md text-white ${selectedChatIds.length > 0 ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-400 cursor-not-allowed'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500`}
            disabled={selectedChatIds.length === 0 || isSending}
          >
            Delete Selected Chats ({selectedChatIds.length})
          </button>
        </div>
        <div className="flex-grow overflow-y-auto">
          {chats.length === 0 ? (
            <p className="text-gray-500">No chats yet. Start a new one!</p>
          ) : (
            <ul>
              {chats.map((chat) => (
                <li key={chat.id} className="mb-2 flex items-center justify-between">
                  <input
                    type="checkbox"
                    className="mr-2 form-checkbox h-5 w-5 text-indigo-600 transition duration-150 ease-in-out"
                    checked={selectedChatIds.includes(chat.id)}
                    onChange={() => handleCheckboxChange(chat.id)}
                    disabled={isSending}
                  />
                  <button
                    onClick={() => handleSelectChat(chat.id)}
                    className={`flex-grow text-left p-2 rounded-md ${currentChatId === chat.id ? 'bg-indigo-100 text-indigo-800' : 'hover:bg-gray-50 text-gray-700'}`}
                  >
                    {chat.title || 'Untitled Chat'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          onClick={logout}
          className="mt-4 w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
        >
          Logout
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-lg shadow-md m-4">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-800">{currentChatId ? chats.find(chat => chat.id === currentChatId)?.title : 'Select or Start a Chat'}</h1>
        </div>

        {error && <p className="text-red-500 text-center p-2">{error}</p>}

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!currentChatId ? (
            <div className="text-center text-gray-500 mt-10">
              <p>Please select an existing chat or start a new one.</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-10">
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender_type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xl p-3 rounded-lg shadow-sm ${message.sender_type === 'user' ? 'bg-indigo-500 text-white' : 'bg-gray-200 text-gray-800'}`}
                >
                  <p className="font-semibold">{message.sender_type === 'user' ? 'You' : 'AI'}</p>
                  <p>{message.content}</p>
                  <span className="text-xs opacity-75 mt-1 block">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))
          )}
          {isSending && (
            <div className="flex justify-start">
              <div className="max-w-xl p-3 rounded-lg shadow-sm bg-gray-200 text-gray-800 animate-pulse">
                <p className="font-semibold">AI</p>
                <p>Thinking...</p>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 p-4 flex items-center">
          <input
            type="text"
            className="flex-1 border border-gray-300 rounded-l-md p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder={isRecording ? 'Listening...' : 'Type your message or record audio...'}
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={!currentChatId || isSending || isPlayingAudio}
          />
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`ml-2 p-2 rounded-md text-white ${isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
            disabled={!currentChatId || isSending || isPlayingAudio}
          >
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </button>
          <button
            onClick={() => handleSendMessage()}
            className="ml-2 p-2 bg-indigo-600 text-white rounded-r-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            disabled={!newMessage.trim() || !currentChatId || isSending || isPlayingAudio}
          >
            Send
          </button>
        </div>
        {/* Hidden audio player */}
        <audio ref={audioPlayerRef} className="hidden" />
      </div>
    </div>
  );
}