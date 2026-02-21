export type GenerationMode = 'proxy' | 'direct' | 'local';

export type ViewMode = '4-view' | '6-view' | '8-view' | 'single' | 'custom';

export type Resolution = '1K' | '2K' | '4K';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error';

export type FeatureTab = 'generate' | 'extract-clothes' | 'change-clothes' | 'change-style';

// 负面提示词类别
export const NEGATIVE_CATEGORIES = [
  { value: 'anatomy', label: '解剖结构问题', labelEn: 'Anatomy' },
  { value: 'quality', label: '质量问题', labelEn: 'Quality' },
  { value: 'layout', label: '布局问题', labelEn: 'Layout' },
  { value: 'color', label: '颜色问题', labelEn: 'Color' },
  { value: 'style', label: '风格问题', labelEn: 'Style' },
];

// 道具选项
export const PROPS_OPTIONS = [
  { value: 'weapon', label: '武器', labelEn: 'Weapon' },
  { value: 'accessory', label: '配饰', labelEn: 'Accessory' },
  { value: 'backpack', label: '背包', labelEn: 'Backpack' },
  { value: 'hat', label: '帽子', labelEn: 'Hat' },
  { value: 'glasses', label: '眼镜', labelEn: 'Glasses' },
  { value: 'shield', label: '盾牌', labelEn: 'Shield' },
  { value: 'staff', label: '法杖', labelEn: 'Staff' },
  { value: 'book', label: '书籍', labelEn: 'Book' },
];

// 宽高比选项
export const ASPECT_RATIO_OPTIONS = [
  { value: '1:1', label: '1:1 (方形)' },
  { value: '2:3', label: '2:3 (竖向)' },
  { value: '3:2', label: '3:2 (横向)' },
  { value: '16:9', label: '16:9 (宽屏)' },
  { value: '9:16', label: '9:16 (竖屏)' },
];

// 模型选项
export const MODEL_OPTIONS = [
  { value: 'gemini-3-pro-image-preview', label: 'Nano Banana Pro (推荐)', labelEn: 'Nano Banana Pro (Recommended)' },
  { value: 'gemini-2.5-flash-image', label: 'Nano Banana (快速)', labelEn: 'Nano Banana (Fast)' },
];

export interface GenerateRequest {
  description: string;
  mode: GenerationMode;
  viewMode: ViewMode;
  customViews?: string[];
  style: string;
  resolution: Resolution;
  referenceImage?: string;
  negativePrompt?: string;
  subjectOnly: boolean;
  withProps?: string[];
  // 新增参数
  model?: string;
  useNegativePrompt?: boolean;
  negativeCategories?: string[];
  useStrictMode?: boolean;
  useImageReferencePrompt?: boolean;
  aspectRatio?: string;
}

export interface ExtractClothesRequest {
  image: string;
  extractProps?: boolean;
}

export interface ChangeClothesRequest {
  characterImage: string;
  clothesDescription?: string;
  clothesImage?: string;
  targetStyle?: string;
  viewMode?: string;
}

export interface ChangeStyleRequest {
  image: string;
  style: string;
  strength?: number;
}

export interface GeneratedImage {
  id: string;
  view: string;
  url: string;
}

export interface GenerateResponse {
  assetId: string;
  status: 'success' | 'processing' | 'error';
  images: {
    master?: string;
    front?: string;
    right?: string;
    back?: string;
    left?: string;
    frontRight?: string;
    frontLeft?: string;
    top?: string;
    bottom?: string;
  };
  metadata: {
    description: string;
    style: string;
    model: string;
    createdAt: string;
  };
}

export interface ExtractClothesResponse {
  assetId: string;
  status: 'success' | 'processing' | 'error';
  originalImage?: string;
  extractedClothes?: string;
  extractedProps?: string[];
}

export interface ChangeClothesResponse {
  assetId: string;
  status: 'success' | 'processing' | 'error';
  images: {
    master?: string;
    front?: string;
    right?: string;
    back?: string;
    left?: string;
  };
}

export interface ChangeStyleResponse {
  assetId: string;
  status: 'success' | 'processing' | 'error';
  originalImage?: string;
  styledImage?: string;
}

export interface GenerationHistoryItem {
  id: string;
  assetId: string;
  description: string;
  thumbnail: string;
  images: GeneratedImage[];
  status: GenerationStatus;
  createdAt: string;
  featureType?: FeatureTab;
}

export interface GenerationState {
  description: string;
  mode: GenerationMode;
  viewMode: ViewMode;
  customViews: string[];
  style: string;
  resolution: Resolution;
  referenceImage: string | null;
  negativePrompt: string;
  subjectOnly: boolean;
  withProps: string[];
  // 新功能参数
  clothesImage: string | null;
  targetClothes: string;
  targetStyle: string;
  styleStrength: number;
  // 新增参数
  model: string;
  useNegativePrompt: boolean;
  negativeCategories: string[];
  useStrictMode: boolean;
  useImageReferencePrompt: boolean;
  aspectRatio: string;
}

export interface AppSettings {
  apiKey: string;
  defaultMode: GenerationMode;
  defaultViewMode: ViewMode;
  defaultResolution: Resolution;
  defaultModel: string;
  theme: 'dark' | 'light';
}

export const DEFAULT_GENERATION_STATE: GenerationState = {
  description: '',
  mode: 'proxy',
  viewMode: '4-view',
  customViews: [],
  style: 'realistic',
  resolution: '1K',
  referenceImage: null,
  negativePrompt: '',
  subjectOnly: true,
  withProps: [],
  clothesImage: null,
  targetClothes: '',
  targetStyle: 'realistic',
  styleStrength: 0.7,
  model: 'gemini-3-pro-image-preview',
  useNegativePrompt: true,
  negativeCategories: ['anatomy', 'quality', 'layout'],
  useStrictMode: false,
  useImageReferencePrompt: false,
  aspectRatio: '3:2',
};

export const VIEW_OPTIONS = {
  'single': ['front'],
  '4-view': ['front', 'right', 'back', 'left'],
  '6-view': ['front', 'frontRight', 'right', 'back', 'left', 'frontLeft'],
  '8-view': ['front', 'frontRight', 'right', 'backRight', 'back', 'backLeft', 'left', 'frontLeft'],
  'custom': [],
};

export const VIEW_OPTIONS_CN = {
  'single': ['正面'],
  '4-view': ['正面', '右侧', '背面', '左侧'],
  '6-view': ['正面', '右前', '右侧', '背面', '左侧', '左前'],
  '8-view': ['正面', '右前', '右侧', '右后', '背面', '左后', '左侧', '左前'],
  'custom': [],
};

export const STYLE_OPTIONS = [
  { value: 'realistic', label: '写实风格', labelEn: 'Realistic' },
  { value: 'anime', label: '动漫风格', labelEn: 'Anime' },
  { value: 'cartoon', label: '卡通风格', labelEn: 'Cartoon' },
  { value: '3d-render', label: '3D渲染', labelEn: '3D Render' },
  { value: 'sketch', label: '素描风格', labelEn: 'Sketch' },
  { value: 'watercolor', label: '水彩风格', labelEn: 'Watercolor' },
  { value: 'oil-painting', label: '油画风格', labelEn: 'Oil Painting' },
  { value: 'pixel-art', label: '像素风格', labelEn: 'Pixel Art' },
  { value: 'cinematic', label: '电影风格', labelEn: 'Cinematic' },
];

export const RESOLUTION_OPTIONS = [
  { value: '1K', label: '1024 x 1024' },
  { value: '2K', label: '2048 x 2048 (推荐)' },
  { value: '4K', label: '4096 x 4096' },
];

export const CLOTHES_PRESETS = [
  { value: 'school-uniform', label: '校服', labelEn: 'School Uniform' },
  { value: 'casual', label: '休闲装', labelEn: 'Casual' },
  { value: 'formal', label: '正装', labelEn: 'Formal' },
  { value: 'costume', label: 'Cosplay服装', labelEn: 'Costume' },
  { value: 'medieval', label: '中世纪风格', labelEn: 'Medieval' },
  { value: 'fantasy', label: '奇幻风格', labelEn: 'Fantasy' },
  { value: 'sci-fi', label: '科幻风格', labelEn: 'Sci-Fi' },
  { value: 'traditional', label: '传统服饰', labelEn: 'Traditional' },
];
