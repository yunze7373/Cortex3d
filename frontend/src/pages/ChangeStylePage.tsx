import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Palette, Upload, Download, Loader2, RefreshCw } from 'lucide-react';
import { MainLayout } from '../components/layout';
import { Button, Card, CardHeader, CardTitle, CardDescription, CardContent, ImageUploader, Select, Slider } from '../components/common';
import { changeStyle } from '../services/api';
import { STYLE_OPTIONS } from '../types';
import type { FeatureTab } from '../types';

interface ChangeStylePageProps {
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

const ChangeStylePage: React.FC<ChangeStylePageProps> = ({ activeTab, onTabChange }) => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedStyle, setSelectedStyle] = useState('anime');
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    originalImage?: string;
    styledImage?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelect = (base64: string) => {
    setSelectedImage(base64);
    setResult(null);
    setError(null);
  };

  const handleChangeStyle = useCallback(async () => {
    if (!selectedImage) {
      setError('请上传一张图片');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await changeStyle({
        image: selectedImage,
        style: selectedStyle,
        strength: styleStrength,
      });

      setResult({
        originalImage: response.originalImage,
        styledImage: response.styledImage,
      });
    } catch (err: unknown) {
      console.error('风格切换失败:', err);
      const errorMessage = err instanceof Error ? err.message : '风格切换失败，请重试';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedImage, selectedStyle, styleStrength]);

  const handleReset = () => {
    setSelectedImage(null);
    setResult(null);
    setError(null);
  };

  const handleStyleChange = (value: string) => {
    setSelectedStyle(value);
    setResult(null);
  };

  return (
    <MainLayout
      activeTab={activeTab}
      onTabChange={onTabChange}
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            风格<span className="text-gradient">切换</span>
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            将图像转换为不同的艺术风格，支持多种风格选择和强度调节。
          </p>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Input */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card variant="glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5 text-accent-primary" />
                  输入内容
                </CardTitle>
                <CardDescription>
                  上传图片并选择目标风格
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ImageUploader
                  label="原图"
                  onImageSelect={handleImageSelect}
                  currentImage={selectedImage}
                  onImageRemove={() => setSelectedImage(null)}
                  helperText="支持 JPG、PNG 格式"
                />

                <Select
                  label="目标风格"
                  options={STYLE_OPTIONS}
                  value={selectedStyle}
                  onChange={handleStyleChange}
                />

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    风格强度: {Math.round(styleStrength * 100)}%
                  </label>
                  <Slider
                    value={styleStrength}
                    onChange={setStyleStrength}
                    min={0.1}
                    max={1}
                    step={0.1}
                    labels={['柔和', '强烈']}
                  />
                  <p className="text-xs text-text-muted mt-1">
                    较低的值保留更多原图特征，较高的值更接近目标风格
                  </p>
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    className="flex-1"
                    onClick={handleChangeStyle}
                    disabled={!selectedImage || isProcessing}
                    isLoading={isProcessing}
                    leftIcon={isProcessing ? undefined : <Palette className="w-4 h-4" />}
                  >
                    {isProcessing ? '处理中...' : '应用风格'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    disabled={isProcessing}
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </div>

                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                    {error}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Right Column - Result */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card variant="default">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="w-5 h-5 text-accent-secondary" />
                  风格转换结果
                </CardTitle>
                <CardDescription>
                  转换后的图像
                </CardDescription>
              </CardHeader>
              <CardContent>
                {result ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      {result.originalImage && (
                        <div>
                          <p className="text-sm text-text-muted mb-2">原图</p>
                          <img
                            src={result.originalImage}
                            alt="Original"
                            className="w-full rounded-lg border border-border-subtle"
                          />
                        </div>
                      )}
                      {result.styledImage && (
                        <div>
                          <p className="text-sm text-text-muted mb-2">
                            {STYLE_OPTIONS.find(s => s.value === selectedStyle)?.label || selectedStyle} 风格
                          </p>
                          <img
                            src={result.styledImage}
                            alt="Styled"
                            className="w-full rounded-lg border border-border-subtle"
                          />
                        </div>
                      )}
                    </div>
                    {result.styledImage && (
                      <Button
                        className="w-full"
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = result.styledImage!;
                          link.download = `styled_${selectedStyle}.png`;
                          link.click();
                        }}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        下载风格化图片
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-text-muted">
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-12 h-12 animate-spin text-accent-primary mb-4" />
                        <p>正在应用 {STYLE_OPTIONS.find(s => s.value === selectedStyle)?.label || selectedStyle} 风格...</p>
                        <p className="text-sm mt-2">这可能需要一些时间</p>
                      </>
                    ) : (
                      <>
                        <Palette className="w-16 h-16 mb-4 opacity-50" />
                        <p>上传图片并选择风格</p>
                        <p className="text-sm mt-1">点击"应用风格"开始转换</p>
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Style Preview Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-12"
        >
          <h2 className="text-2xl font-bold text-text-primary mb-6 text-center">
            可用风格预览
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {STYLE_OPTIONS.map((style) => (
              <button
                key={style.value}
                onClick={() => handleStyleChange(style.value)}
                className={`p-4 rounded-lg border transition-all ${
                  selectedStyle === style.value
                    ? 'border-accent-primary bg-accent-primary/10'
                    : 'border-border-subtle hover:border-accent-primary/50'
                }`}
              >
                <div className="aspect-square bg-gradient-to-br from-bg-hover to-bg-secondary rounded-lg mb-2 flex items-center justify-center">
                  <Palette className="w-8 h-8 text-text-muted" />
                </div>
                <p className="text-sm font-medium text-text-primary">{style.label}</p>
                <p className="text-xs text-text-muted">{style.labelEn}</p>
              </button>
            ))}
          </div>
        </motion.div>
      </div>
    </MainLayout>
  );
};

export default ChangeStylePage;
