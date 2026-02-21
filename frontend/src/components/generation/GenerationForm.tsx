import React from 'react';
import { motion } from 'framer-motion';
import {
  Wand2,
  Settings2,
  Sparkles,
} from 'lucide-react';
import {
  Button,
  TextArea,
  Select,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Checkbox,
  ImageUploader,
  Input,
} from '../common';
import { useGenerationStore } from '../../stores/generationStore';
import {
  STYLE_OPTIONS,
  RESOLUTION_OPTIONS,
  MODEL_OPTIONS,
  ASPECT_RATIO_OPTIONS,
  PROPS_OPTIONS,
} from '../../types';

interface GenerationFormProps {
  onGenerate: () => void;
  isGenerating: boolean;
}

export const GenerationForm: React.FC<GenerationFormProps> = ({
  onGenerate,
  isGenerating,
}) => {
  const { formState, setFormState } = useGenerationStore();

  const handleImageSelect = (base64: string) => {
    setFormState({ referenceImage: base64 });
  };

  const handleImageRemove = () => {
    setFormState({ referenceImage: null });
  };

  const isDisabled = !formState.description.trim() && !formState.referenceImage;

  // Map view modes to Chinese labels
  const viewModeOptions = [
    { value: 'single', label: '单一视角 (仅正面)' },
    { value: '4-view', label: '4视角 (正面/右侧/背面/左侧)' },
    { value: '6-view', label: '6视角 (+右前/左前)' },
    { value: '8-view', label: '8视角 (+顶部/底部)' },
    { value: 'custom', label: '自定义视角' },
  ];

  // Handle props selection
  const handlePropToggle = (propValue: string) => {
    const currentProps = formState.withProps || [];
    if (currentProps.includes(propValue)) {
      setFormState({ withProps: currentProps.filter(p => p !== propValue) });
    } else {
      setFormState({ withProps: [...currentProps, propValue] });
    }
  };

  return (
    <div className="space-y-6">
      {/* Input Section */}
      <Card variant="glass">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wand2 className="w-5 h-5 text-accent-primary" />
            创建角色
          </CardTitle>
          <CardDescription>
            输入角色描述或上传参考图片
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Text Input */}
          <TextArea
            label="角色描述"
            placeholder="描述你的角色，例如：粉色头发的可爱动漫女孩，穿着校服..."
            value={formState.description}
            onChange={(e) => setFormState({ description: e.target.value })}
            rows={4}
            helperText="越详细的描述生成效果越好"
          />

          {/* Reference Image */}
          <ImageUploader
            label="或上传参考图片"
            onImageSelect={handleImageSelect}
            currentImage={formState.referenceImage}
            onImageRemove={handleImageRemove}
            helperText="上传图片生成多视角变体"
          />

          {/* Use Image Reference Prompt */}
          {formState.referenceImage && (
            <Checkbox
              label="使用图片参考专用提示词"
              checked={formState.useImageReferencePrompt}
              onChange={(e) => setFormState({ useImageReferencePrompt: e.target.checked })}
            />
          )}
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card variant="default">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="w-5 h-5 text-accent-secondary" />
            生成设置
          </CardTitle>
          <CardDescription>
            配置输出参数
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Model */}
          <Select
            label="模型"
            options={MODEL_OPTIONS}
            value={formState.model}
            onChange={(value) => setFormState({ model: value })}
          />

          {/* View Mode */}
          <Select
            label="视角模式"
            options={viewModeOptions}
            value={formState.viewMode}
            onChange={(value) => setFormState({ viewMode: value as any })}
          />

          {/* Custom Views Input */}
          {formState.viewMode === 'custom' && (
            <Input
              label="自定义视角"
              placeholder="front, right, back, left, top"
              value={formState.customViews?.join(', ') || ''}
              onChange={(e) => setFormState({
                customViews: e.target.value.split(',').map(v => v.trim()).filter(v => v)
              })}
              helperText="输入视角名称，用逗号分隔"
            />
          )}

          {/* Style */}
          <Select
            label="风格"
            options={STYLE_OPTIONS}
            value={formState.style}
            onChange={(value) => setFormState({ style: value })}
          />

          {/* Resolution */}
          <Select
            label="分辨率"
            options={RESOLUTION_OPTIONS}
            value={formState.resolution}
            onChange={(value) => setFormState({ resolution: value as any })}
          />

          {/* Aspect Ratio */}
          <Select
            label="宽高比"
            options={ASPECT_RATIO_OPTIONS}
            value={formState.aspectRatio}
            onChange={(value) => setFormState({ aspectRatio: value })}
          />

          {/* With Props */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              包含道具
            </label>
            <div className="flex flex-wrap gap-2">
              {PROPS_OPTIONS.map((prop) => (
                <button
                  key={prop.value}
                  type="button"
                  onClick={() => handlePropToggle(prop.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${
                    (formState.withProps || []).includes(prop.value)
                      ? 'border-accent-primary bg-accent-primary/20 text-accent-primary'
                      : 'border-border-subtle text-text-secondary hover:border-accent-primary/50'
                  }`}
                >
                  {prop.label}
                </button>
              ))}
            </div>
          </div>

          {/* Negative Prompt */}
          <TextArea
            label="负面提示词"
            placeholder="不想出现的内容，例如：模糊，多余的手指..."
            value={formState.negativePrompt}
            onChange={(e) => setFormState({ negativePrompt: e.target.value })}
            rows={2}
            helperText="指定不想在图像中出现的内容"
          />

          {/* Use Negative Prompt */}
          <Checkbox
            label="启用负面提示词优化"
            checked={formState.useNegativePrompt}
            onChange={(e) => setFormState({ useNegativePrompt: e.target.checked })}
          />

          {/* Options */}
          <div className="space-y-3 pt-2">
            <Checkbox
              label="仅主体 (移除背景)"
              checked={formState.subjectOnly}
              onChange={(e) => setFormState({ subjectOnly: e.target.checked })}
            />
            <Checkbox
              label="严格复制模式 (100%基于参考图)"
              checked={formState.useStrictMode}
              onChange={(e) => setFormState({ useStrictMode: e.target.checked })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Generate Button */}
      <motion.div
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <Button
          className="w-full py-4 text-lg font-semibold"
          size="lg"
          onClick={onGenerate}
          disabled={isDisabled || isGenerating}
          isLoading={isGenerating}
          leftIcon={isGenerating ? undefined : <Sparkles className="w-5 h-5" />}
        >
          {isGenerating ? '生成中...' : '生成多视角图像'}
        </Button>
      </motion.div>

      {!formState.description.trim() && !formState.referenceImage && (
        <p className="text-center text-sm text-text-muted">
          请输入角色描述或上传参考图片
        </p>
      )}
    </div>
  );
};
