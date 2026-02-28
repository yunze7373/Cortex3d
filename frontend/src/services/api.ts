import axios from 'axios';
import type { GenerateRequest, GenerateResponse } from '../types';

// 智能检测 API 地址
const getAPIBaseURL = (): string => {
  const env = import.meta.env.VITE_API_BASE_URL;
  
  // 如果环境变量中明确指定了，直接使用
  if (env) {
    return env;
  }
  
  // 否则根据当前访问地址动态生成
  const host = window.location.hostname;
  const protocol = window.location.protocol;
  
  // 如果是 localhost 或 127.0.0.1，使用本地后端
  if (host === 'localhost' || host === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // 否则假设后端在同一个 IP 的 8000 端口（例如 172.28.124.41:8000）
  return `${protocol}//${host}:8000`;
};

const API_BASE_URL = getAPIBaseURL();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============ NDJSON 流式请求工具 ============

export interface ProgressEvent {
  message: string;
  progress: number;
}

async function streamingFetch<T>(
  url: string,
  body: any,
  onProgress?: (event: ProgressEvent) => void
): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;

  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('响应缺少 body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  return new Promise((resolve, reject) => {
    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          // 留着最后一行不完整的JSON留到下次解析
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;

            try {
              const parsed = JSON.parse(line);

              if (parsed.type === 'error') {
                reject(new Error(parsed.message || '服务器内部错误'));
                return;
              } else if (parsed.type === 'progress') {
                if (onProgress) {
                  onProgress({
                    message: parsed.message || '处理中...',
                    progress: parsed.progress || 0
                  });
                }
              } else if (parsed.type === 'result') {
                resolve(parsed.data as T);
                return;
              }
            } catch (e) {
              console.error('Invalid JSON line:', line, e);
            }
          }
        }

        // 处理最后可能剩下的内容
        if (buffer.trim()) {
          try {
            const parsed = JSON.parse(buffer);
            if (parsed.type === 'error') {
              reject(new Error(parsed.message || '服务器内部错误'));
              return;
            } else if (parsed.type === 'result') {
              resolve(parsed.data as T);
              return;
            }
          } catch (e) {
            console.error('Invalid final JSON line:', buffer, e);
          }
        }

        // 如果流已结束但依然没有 resolve 也没有 reject，抛出异常避免前端死锁
        reject(new Error('数据流异常关闭或解析失败，未收到最终生成的图片'));

      } catch (e) {
        reject(e);
      }
    };

    processStream();
  });
}

// ============ 图像生成 ============

export const generateFromText = async (
  request: GenerateRequest,
  onProgress?: (event: ProgressEvent) => void
): Promise<GenerateResponse> => {
  return streamingFetch<GenerateResponse>('/api/generate/multiview', request, onProgress);
};

export const generateFromImage = async (
  request: GenerateRequest & { referenceImage: string },
  onProgress?: (event: ProgressEvent) => void
): Promise<GenerateResponse> => {
  return streamingFetch<GenerateResponse>('/api/generate/from-image', request, onProgress);
};

// ============ 服装提取 ============

export interface ExtractClothesRequest {
  image: string;
  extractProps?: boolean;
}

export interface ExtractClothesResponse {
  assetId: string;
  status: string;
  originalImage?: string;
  extractedClothes?: string;
  extractedProps?: string[];
}

export const extractClothes = async (
  request: ExtractClothesRequest,
  onProgress?: (event: ProgressEvent) => void
): Promise<ExtractClothesResponse> => {
  return streamingFetch<ExtractClothesResponse>('/api/extract/clothes', request, onProgress);
};

// ============ 换衣服 ============

export interface ChangeClothesRequest {
  characterImage: string;
  clothesDescription?: string;
  clothesImage?: string;
  propsImage?: string;
  targetStyle?: string;
  viewMode?: string;
}

export interface ChangeClothesResponse {
  assetId: string;
  status: string;
  images: {
    master?: string;
    front?: string;
    right?: string;
    back?: string;
    left?: string;
  };
}

export const changeClothes = async (
  request: ChangeClothesRequest,
  onProgress?: (event: ProgressEvent) => void
): Promise<ChangeClothesResponse> => {
  return streamingFetch<ChangeClothesResponse>('/api/edit/change-clothes', request, onProgress);
};

// ============ 风格切换 ============

export interface ChangeStyleRequest {
  image: string;
  style: string;
  strength?: number;
}

export interface ChangeStyleResponse {
  assetId: string;
  status: string;
  originalImage?: string;
  styledImage?: string;
}

export const changeStyle = async (
  request: ChangeStyleRequest,
  onProgress?: (event: ProgressEvent) => void
): Promise<ChangeStyleResponse> => {
  return streamingFetch<ChangeStyleResponse>('/api/edit/change-style', request, onProgress);
};

// ============ 其他功能 ============

export const editImage = async (
  imageId: string,
  edits: { action: 'add' | 'remove' | 'modify'; prompt: string; mask?: string }
): Promise<GenerateResponse> => {
  const response = await apiClient.post<GenerateResponse>('/api/edit/elements', {
    imageId,
    ...edits,
  });
  return response.data;
};

export const analyzeCharacter = async (
  imageBase64: string
): Promise<{ description: string; attributes: Record<string, string> }> => {
  const response = await apiClient.post('/api/analyze/character', {
    image: imageBase64,
  });
  return response.data;
};

export const getHistory = async (): Promise<GenerateResponse[]> => {
  const response = await apiClient.get('/api/history');
  return response.data;
};

export const downloadAsset = async (assetId: string): Promise<Blob> => {
  const response = await apiClient.get(`/api/download/${assetId}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const checkServerStatus = async (): Promise<{ status: string }> => {
  const response = await apiClient.get('/api/health');
  return response.data;
};
