// src/api.ts
import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

const api = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加认证token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token 过期或无效，重定向到登录页
      localStorage.removeItem('access_token');
      window.location.href = '/login'; 
    }
    return Promise.reject(error);
  }
);

export const transcribeAudio = async (audioBlob: Blob) => {
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm'); // 文件名可以自定义
  const response = await api.post('/audio/transcribe', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data.transcript;
};

export const speakText = async (text: string) => {
  const response = await api.post('/audio/speak', { input_text: text }, {
    responseType: 'blob', // 期望后端返回的是二进制数据
  });
  return response.data; // 返回 Blob 数据
};

export const deleteChats = async (chatIds: string[]) => {
  await api.delete('/chats/bulk', { data: { chat_ids: chatIds } });
};

export default api;