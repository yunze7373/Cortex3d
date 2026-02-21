import axios from 'axios';
import type { GenerateRequest, GenerateResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============ 图像生成 ============

export const generateFromText = async (request: GenerateRequest): Promise<GenerateResponse> => {
  const response = await apiClient.post<GenerateResponse>('/api/generate/multiview', request);
  return response.data;
};

export const generateFromImage = async (
  request: GenerateRequest & { referenceImage: string }
): Promise<GenerateResponse> => {
  const response = await apiClient.post<GenerateResponse>('/api/generate/from-image', request);
  return response.data;
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

export const extractClothes = async (request: ExtractClothesRequest): Promise<ExtractClothesResponse> => {
  const response = await apiClient.post<ExtractClothesResponse>('/api/extract/clothes', request);
  return response.data;
};

// ============ 换衣服 ============

export interface ChangeClothesRequest {
  characterImage: string;
  clothesDescription?: string;
  clothesImage?: string;
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

export const changeClothes = async (request: ChangeClothesRequest): Promise<ChangeClothesResponse> => {
  const response = await apiClient.post<ChangeClothesResponse>('/api/edit/change-clothes', request);
  return response.data;
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

export const changeStyle = async (request: ChangeStyleRequest): Promise<ChangeStyleResponse> => {
  const response = await apiClient.post<ChangeStyleResponse>('/api/edit/change-style', request);
  return response.data;
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
