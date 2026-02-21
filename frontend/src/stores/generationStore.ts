import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  GenerationState,
  GenerationHistoryItem,
  AppSettings,
  GenerateResponse,
} from '../types';
import { DEFAULT_GENERATION_STATE } from '../types';

interface GenerationStore {
  // Generation state
  formState: GenerationState;
  setFormState: (state: Partial<GenerationState>) => void;
  resetFormState: () => void;

  // Current generation
  currentGeneration: GenerateResponse | null;
  setCurrentGeneration: (generation: GenerateResponse | null) => void;

  // Status
  isGenerating: boolean;
  setIsGenerating: (status: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;

  // History
  history: GenerationHistoryItem[];
  addToHistory: (item: GenerationHistoryItem) => void;
  removeFromHistory: (id: string) => void;
  clearHistory: () => void;
}

export const useGenerationStore = create<GenerationStore>()(
  persist(
    (set) => ({
      // Generation state
      formState: DEFAULT_GENERATION_STATE,
      setFormState: (state) =>
        set((prev) => ({
          formState: { ...prev.formState, ...state },
        })),
      resetFormState: () => set({ formState: DEFAULT_GENERATION_STATE }),

      // Current generation
      currentGeneration: null,
      setCurrentGeneration: (generation) => set({ currentGeneration: generation }),

      // Status
      isGenerating: false,
      setIsGenerating: (status) => set({ isGenerating: status }),
      error: null,
      setError: (error) => set({ error }),

      // History
      history: [],
      addToHistory: (item) =>
        set((state) => ({
          history: [item, ...state.history].slice(0, 50),
        })),
      removeFromHistory: (id) =>
        set((state) => ({
          history: state.history.filter((item) => item.id !== id),
        })),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'cortex3d-generation-storage',
      partialize: (state) => ({
        history: state.history,
      }),
    }
  )
);

interface SettingsStore {
  settings: AppSettings;
  updateSettings: (settings: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: AppSettings = {
  apiKey: '',
  defaultMode: 'proxy',
  defaultViewMode: '4-view',
  defaultResolution: '1K',
  defaultModel: 'gemini-3-pro-image-preview',
  theme: 'dark',
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),
      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    {
      name: 'cortex3d-settings-storage',
    }
  )
);
