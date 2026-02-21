import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { History, Trash2 } from 'lucide-react';
import { MainLayout } from '../components/layout';
import { GenerationForm } from '../components/generation';
import { PreviewGallery } from '../components/preview';
import { Button, Modal, Input } from '../components/common';
import { useGenerationStore, useSettingsStore } from '../stores/generationStore';
import type { GenerateResponse, GenerationHistoryItem, FeatureTab } from '../types';
import { generateFromText, generateFromImage } from '../services/api';

interface GenerationPageProps {
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

const GenerationPage: React.FC<GenerationPageProps> = ({ activeTab, onTabChange }) => {
  const [settingsOpen, setSettingsOpen] = useState(false);

  const {
    formState,
    isGenerating,
    setIsGenerating,
    currentGeneration,
    setCurrentGeneration,
    setError,
    history,
    addToHistory,
    clearHistory,
  } = useGenerationStore();

  const { settings, updateSettings } = useSettingsStore();

  const handleGenerate = useCallback(async () => {
    if (!formState.description.trim() && !formState.referenceImage) {
      setError('请输入角色描述或上传参考图片');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      let response: GenerateResponse;

      // Prepare request - filter out null values
      const request = {
        description: formState.description,
        mode: formState.mode,
        viewMode: formState.viewMode,
        customViews: formState.customViews,
        style: formState.style,
        resolution: formState.resolution,
        negativePrompt: formState.negativePrompt,
        subjectOnly: formState.subjectOnly,
        withProps: formState.withProps,
      };

      if (formState.referenceImage) {
        response = await generateFromImage({
          ...request,
          referenceImage: formState.referenceImage,
        });
      } else {
        response = await generateFromText(request);
      }

      setCurrentGeneration(response);

      // Add to history
      const firstImage = response.images.front || Object.values(response.images)[0];
      const historyItem: GenerationHistoryItem = {
        id: Date.now().toString(),
        assetId: response.assetId,
        description: formState.description,
        thumbnail: firstImage || '',
        images: Object.entries(response.images)
          .filter(([, url]) => url)
          .map(([view, url]) => ({ id: view, view, url: url! })),
        status: 'success',
        createdAt: new Date().toISOString(),
        featureType: 'generate',
      };
      addToHistory(historyItem);
    } catch (err: unknown) {
      console.error('生成失败:', err);
      const errorMessage = err instanceof Error ? err.message : '生成失败，请重试';
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  }, [formState, setIsGenerating, setCurrentGeneration, setError, addToHistory]);

  return (
    <MainLayout onSettingsClick={() => setSettingsOpen(true)} activeTab={activeTab} onTabChange={onTabChange}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            图像<span className="text-gradient">生成</span>
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            通过文字描述或参考图片生成多视角角色图像。AI驱动，高质量输出。
          </p>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Input Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <GenerationForm onGenerate={handleGenerate} isGenerating={isGenerating} />
          </motion.div>

          {/* Right Column - Preview */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <PreviewGallery generation={currentGeneration} isGenerating={isGenerating} />
          </motion.div>
        </div>

        {/* History Section */}
        {history.filter(h => h.featureType === 'generate').length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-12"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
                <History className="w-6 h-6 text-accent-primary" />
                生成历史
              </h2>
              <Button variant="ghost" size="sm" onClick={clearHistory}>
                <Trash2 className="w-4 h-4 mr-1" />
                清空全部
              </Button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {history.filter(h => h.featureType === 'generate').map((item) => (
                <motion.div
                  key={item.id}
                  whileHover={{ scale: 1.02 }}
                  className="group relative aspect-square rounded-lg overflow-hidden border border-border-subtle cursor-pointer hover:border-accent-primary transition-colors"
                  onClick={() => {
                    const response: GenerateResponse = {
                      assetId: item.assetId,
                      status: 'success',
                      images: item.images.reduce(
                        (acc, img) => ({ ...acc, [img.view]: img.url }),
                        {}
                      ) as GenerateResponse['images'],
                      metadata: {
                        description: item.description,
                        style: '',
                        model: '',
                        createdAt: item.createdAt,
                      },
                    };
                    setCurrentGeneration(response);
                  }}
                >
                  <img
                    src={item.thumbnail}
                    alt={item.description}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      <p className="text-xs text-white truncate">{item.description}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </div>

      {/* Settings Modal */}
      <Modal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="设置"
        description="配置您的生成设置"
        size="md"
      >
        <div className="space-y-4">
          <Input
            label="API 密钥"
            type="password"
            value={settings.apiKey}
            onChange={(e) => updateSettings({ apiKey: e.target.value })}
            helperText="您的认证API密钥"
          />
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setSettingsOpen(false)}>
              关闭
            </Button>
          </div>
        </div>
      </Modal>
    </MainLayout>
  );
};

export default GenerationPage;
