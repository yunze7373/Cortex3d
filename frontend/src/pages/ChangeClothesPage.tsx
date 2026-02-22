import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Shirt, Download, Loader2, Sparkles } from 'lucide-react';
import { MainLayout } from '../components/layout';
import { Button, Card, CardHeader, CardTitle, CardDescription, CardContent, ImageUploader, TextArea, Select } from '../components/common';
import { changeClothes } from '../services/api';
import { CLOTHES_PRESETS, STYLE_OPTIONS } from '../types';
import type { FeatureTab } from '../types';

interface ChangeClothesPageProps {
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

const ChangeClothesPage: React.FC<ChangeClothesPageProps> = ({ activeTab, onTabChange }) => {
  const [characterImage, setCharacterImage] = useState<string | null>(null);
  const [clothesImage, setClothesImage] = useState<string | null>(null);
  const [propsImage, setPropsImage] = useState<string | null>(null);
  const [clothesDescription, setClothesDescription] = useState('');
  const [propsDescription, setPropsDescription] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('');
  const [targetStyle, setTargetStyle] = useState('realistic');
  const [mode, setMode] = useState<'text' | 'image'>('text');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    images: {
      master?: string;
      front?: string;
      right?: string;
      back?: string;
      left?: string;
    };
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCharacterSelect = (base64: string) => {
    setCharacterImage(base64);
    setResult(null);
    setError(null);
  };

  const handleClothesSelect = (base64: string) => {
    setClothesImage(base64);
    setResult(null);
    setError(null);
  };

  const handlePropsImageSelect = (base64: string) => {
    setPropsImage(base64);
    setResult(null);
    setError(null);
  };

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    const preset = CLOTHES_PRESETS.find(p => p.value === value);
    if (preset) {
      setClothesDescription(preset.label);
    }
  };

  const handleChangeClothes = useCallback(async () => {
    // Validation
    if (!characterImage) {
      setError('请上传角色图片');
      return;
    }

    if (mode === 'text' && !clothesDescription.trim()) {
      setError('请输入服装描述或选择预设');
      return;
    }

    if (mode === 'image' && !clothesImage) {
      setError('请上传衣服图片');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      let finalDescription = '';
      if (mode === 'text') {
        finalDescription = clothesDescription;
      } else {
        // Build base description for props text
        const basePropsText = propsDescription.trim()
          ? `给这个人穿上这件衣服，并添加这些道具：${propsDescription.trim()}`
          : '';

        // If props image is provided, explicitly tell the model that IMAGE 3 is a prop
        if (propsImage) {
          finalDescription = `图片3 (IMAGE 3) 是需要添加的道具图像，请提取并在人物身上自然地穿戴或手持。\n${basePropsText}`;
        } else {
          finalDescription = basePropsText;
        }
      }

      const response = await changeClothes({
        characterImage,
        clothesDescription: finalDescription,
        clothesImage: mode === 'image' && clothesImage ? clothesImage : undefined,
        propsImage: mode === 'image' && propsImage ? propsImage : undefined,
        targetStyle,
        viewMode: '4-view',
      });

      setResult({
        images: response.images,
      });
    } catch (err: unknown) {
      console.error('换装失败:', err);
      const errorMessage = err instanceof Error ? err.message : '换装失败，请重试';
      setError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  }, [characterImage, clothesDescription, clothesImage, mode, targetStyle]);

  const handleReset = () => {
    setCharacterImage(null);
    setClothesImage(null);
    setPropsImage(null);
    setClothesDescription('');
    setPropsDescription('');
    setSelectedPreset('');
    setResult(null);
    setError(null);
  };

  const presetOptions = [
    { value: '', label: '选择预设...' },
    ...CLOTHES_PRESETS.map(p => ({ value: p.value, label: p.label })),
  ];

  const styleOptions = STYLE_OPTIONS.map(s => ({ value: s.value, label: s.label }));

  return (
    <MainLayout activeTab={activeTab} onTabChange={onTabChange}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            换<span className="text-gradient">衣服</span>
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            为角色更换服装，支持文字描述或上传衣服图片进行替换。
          </p>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left - Input */}
          <Card variant="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shirt className="w-5 h-5 text-accent-primary" />
                上传角色图片
              </CardTitle>
              <CardDescription>
                选择需要换装的角色图像
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ImageUploader
                label="角色图片"
                onImageSelect={handleCharacterSelect}
                currentImage={characterImage}
                onImageRemove={handleReset}
                helperText="支持 PNG、JPG、WEBP 格式"
              />

              {/* Mode Selection */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  换装方式
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setMode('text')}
                    className={`flex-1 px-4 py-2 rounded-lg border transition-all ${mode === 'text'
                      ? 'border-accent-primary bg-accent-primary/20 text-accent-primary'
                      : 'border-border-subtle text-text-secondary hover:border-accent-primary/50'
                      }`}
                  >
                    文字描述
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('image')}
                    className={`flex-1 px-4 py-2 rounded-lg border transition-all ${mode === 'image'
                      ? 'border-accent-primary bg-accent-primary/20 text-accent-primary'
                      : 'border-border-subtle text-text-secondary hover:border-accent-primary/50'
                      }`}
                  >
                    上传衣服图片
                  </button>
                </div>
              </div>

              {mode === 'text' ? (
                <>
                  <Select
                    label="服装预设"
                    options={presetOptions}
                    value={selectedPreset}
                    onChange={handlePresetChange}
                  />

                  <TextArea
                    label="服装描述"
                    placeholder={"描述你想要的服装，例如：红色连衣裙，蕾丝边..."}
                    value={clothesDescription}
                    onChange={(e) => {
                      setClothesDescription(e.target.value);
                      setSelectedPreset('');
                    }}
                    rows={3}
                    helperText="详细描述可以获得更好的效果"
                  />
                </>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ImageUploader
                      label="衣服图片"
                      onImageSelect={handleClothesSelect}
                      currentImage={clothesImage}
                      onImageRemove={() => setClothesImage(null)}
                      helperText="要替换的基础衣服图片"
                    />

                    <ImageUploader
                      label="附加道具图片 (可选)"
                      onImageSelect={handlePropsImageSelect}
                      currentImage={propsImage}
                      onImageRemove={() => setPropsImage(null)}
                      helperText="想要添加的头盔、墨镜、包等"
                    />
                  </div>

                  <TextArea
                    label="附加道具/要求补充 (可选)"
                    placeholder="例如：戴上图片3里的赛车头盔，头盔要抱在腰间..."
                    value={propsDescription}
                    onChange={(e) => setPropsDescription(e.target.value)}
                    rows={2}
                    helperText="如果你上传了道具图片，请在这里说明道具该如何佩戴或如何与角色交互"
                  />
                </div>
              )}

              <Select
                label="目标风格"
                options={styleOptions}
                value={targetStyle}
                onChange={setTargetStyle}
              />

              <div className="flex gap-3 pt-4">
                <Button
                  className="flex-1"
                  onClick={handleChangeClothes}
                  disabled={
                    !characterImage ||
                    (mode === 'text' && !clothesDescription.trim()) ||
                    (mode === 'image' && !clothesImage) ||
                    isProcessing
                  }
                  isLoading={isProcessing}
                  leftIcon={isProcessing ? undefined : <Sparkles className="w-4 h-4" />}
                >
                  {isProcessing ? '处理中...' : '开始换装'}
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
              <CardTitle>换装结果</CardTitle>
            </CardHeader>
            <CardContent>
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="w-12 h-12 text-accent-primary animate-spin mb-4" />
                  <p className="text-text-secondary">正在处理...</p>
                </div>
              ) : result && result.images.front ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-text-muted mb-2">正面</p>
                    <img
                      src={result.images.front}
                      alt="Front"
                      className="w-full rounded-lg"
                    />
                    <Button
                      variant="outline"
                      className="w-full mt-2"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = result.images.front!;
                        link.download = 'changed-clothes-front.png';
                        link.click();
                      }}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      下载
                    </Button>
                  </div>

                  {result.images.right && (
                    <div className="grid grid-cols-3 gap-2">
                      {result.images.right && (
                        <div>
                          <p className="text-xs text-text-muted mb-1">右侧</p>
                          <img src={result.images.right} alt="Right" className="w-full rounded-lg" />
                        </div>
                      )}
                      {result.images.back && (
                        <div>
                          <p className="text-xs text-text-muted mb-1">背面</p>
                          <img src={result.images.back} alt="Back" className="w-full rounded-lg" />
                        </div>
                      )}
                      {result.images.left && (
                        <div>
                          <p className="text-xs text-text-muted mb-1">左侧</p>
                          <img src={result.images.left} alt="Left" className="w-full rounded-lg" />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-text-muted">
                  <Shirt className="w-12 h-12 mb-4 opacity-50" />
                  <p>上传角色图片并选择换装方式</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
};

export default ChangeClothesPage;
