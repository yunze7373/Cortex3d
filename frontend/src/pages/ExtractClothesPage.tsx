import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Scissors, Upload, Download } from 'lucide-react';
import { MainLayout } from '../components/layout';
import { Button, Card, CardHeader, CardTitle, CardDescription, CardContent, ImageUploader, RealProgress } from '../components/common';
import { extractClothes, type ProgressEvent } from '../services/api';
import type { FeatureTab } from '../types';

interface ExtractClothesPageProps {
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

const ExtractClothesPage: React.FC<ExtractClothesPageProps> = ({ activeTab, onTabChange }) => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [extractProps, setExtractProps] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    originalImage?: string;
    extractedClothes?: string;
    extractedProps?: string[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progressState, setProgressState] = useState<ProgressEvent>({ message: '', progress: 0 });

  const handleImageSelect = (base64: string) => {
    setSelectedImage(base64);
    setResult(null);
    setError(null);
  };

  const handleExtract = useCallback(async () => {
    if (!selectedImage) {
      setError('请上传一张图片');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      setProgressState({ message: '正在初始化...', progress: 0 });
      const response = await extractClothes({
        image: selectedImage,
        extractProps,
      }, (event) => setProgressState(event));

      setResult({
        originalImage: response.originalImage,
        extractedClothes: response.extractedClothes,
        extractedProps: response.extractedProps,
      });
    } catch (err: unknown) {
      console.error('提取失败:', err);
      const errorMessage = err instanceof Error ? err.message : '提取失败，请重试';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedImage, extractProps]);

  const handleReset = () => {
    setSelectedImage(null);
    setResult(null);
    setError(null);
  };

  return (
    <MainLayout
      activeTab={activeTab}
      onTabChange={onTabChange}
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            服装<span className="text-gradient">提取</span>
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            从角色图像中提取服装和道具，生成独立的透明背景图像。
          </p>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left - Input */}
          <Card variant="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Scissors className="w-5 h-5 text-accent-primary" />
                上传角色图片
              </CardTitle>
              <CardDescription>
                选择包含角色的图像进行服装提取
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ImageUploader
                label="角色图片"
                onImageSelect={handleImageSelect}
                currentImage={selectedImage}
                onImageRemove={handleReset}
                helperText="支持 PNG、JPG、WEBP 格式"
              />

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="extractProps"
                  checked={extractProps}
                  onChange={(e) => setExtractProps(e.target.checked)}
                  className="w-4 h-4 rounded border-border-subtle bg-bg-secondary text-accent-primary focus:ring-accent-primary"
                />
                <label htmlFor="extractProps" className="text-sm text-text-secondary">
                  同时提取道具
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  className="flex-1"
                  onClick={handleExtract}
                  disabled={!selectedImage || isProcessing}
                  isLoading={isProcessing}
                  leftIcon={isProcessing ? undefined : <Scissors className="w-4 h-4" />}
                >
                  {isProcessing ? '提取中...' : '开始提取'}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleReset}
                  disabled={isProcessing}
                >
                  重置
                </Button>
              </div>

              {error && (
                <p className="text-sm text-accent-error">{error}</p>
              )}
            </CardContent>
          </Card>

          {/* Right - Result */}
          <Card variant="default">
            <CardHeader>
              <CardTitle>提取结果</CardTitle>
            </CardHeader>
            <CardContent>
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <RealProgress
                    isProcessing={isProcessing}
                    progress={progressState.progress}
                    message={progressState.message}
                  />
                </div>
              ) : result ? (
                <div className="space-y-4">
                  {result.originalImage && (
                    <div>
                      <p className="text-sm text-text-muted mb-2">原图</p>
                      <img
                        src={result.originalImage}
                        alt="Original"
                        className="w-full rounded-lg"
                      />
                    </div>
                  )}
                  {result.extractedClothes && (
                    <div>
                      <p className="text-sm text-text-muted mb-2">提取的服装</p>
                      <img
                        src={result.extractedClothes}
                        alt="Extracted clothes"
                        className="w-full rounded-lg"
                      />
                      <Button
                        variant="outline"
                        className="w-full mt-2"
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = result.extractedClothes!;
                          link.download = 'extracted-clothes.png';
                          link.click();
                        }}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        下载服装图片
                      </Button>
                    </div>
                  )}
                  {result.extractedProps && result.extractedProps.length > 0 && (
                    <div>
                      <p className="text-sm text-text-muted mb-2">提取的道具</p>
                      <div className="grid grid-cols-2 gap-2">
                        {result.extractedProps.map((prop, index) => (
                          <div
                            key={index}
                            className="p-2 bg-bg-secondary rounded-lg text-center text-sm text-text-secondary"
                          >
                            {prop}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-text-muted">
                  <Upload className="w-12 h-12 mb-4 opacity-50" />
                  <p>上传图片后点击提取按钮</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
};

export default ExtractClothesPage;
