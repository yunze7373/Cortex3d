import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Download,
  Eye,
  RotateCcw,
  Grid3X3,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  PackageOpen,
  Loader2,
} from 'lucide-react';
import { Button, Card, ImageGrid, RealProgress } from '../common';
import type { GenerateResponse } from '../../types';
import type { ProgressEvent } from '../../services/api';

interface PreviewGalleryProps {
  generation: GenerateResponse | null;
  isGenerating: boolean;
  progressState?: ProgressEvent;
}

const viewOrder = ['front', 'frontRight', 'right', 'backRight', 'back', 'backLeft', 'left', 'frontLeft'];

/** 下载单张图片（通过 blob 确保触发保存） */
async function downloadImage(url: string, filename: string) {
  try {
    const res = await fetch(url);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
  } catch {
    // fallback: 直接链接下载
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  }
}

export const PreviewGallery: React.FC<PreviewGalleryProps> = ({
  generation,
  isGenerating,
  progressState,
}) => {
  const [selectedView, setSelectedView] = useState<string>('front');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);

  if (!generation && !isGenerating) {
    return (
      <Card variant="glass" className="h-full flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-bg-hover flex items-center justify-center">
            <Grid3X3 className="w-10 h-10 text-text-muted" />
          </div>
          <h3 className="text-lg font-medium text-text-primary mb-2">暂无生成的图像</h3>
          <p className="text-sm text-text-muted max-w-xs">
            输入描述并点击生成按钮来创建多视角角色图像
          </p>
        </div>
      </Card>
    );
  }

  const images = generation?.images
    ? Object.entries(generation.images)
      .filter(([_, url]) => url)
      .map(([view, url]) => ({ id: view, view, url: url! }))
    : [];

  const sortedImages = [...images].sort(
    (a, b) => viewOrder.indexOf(a.view) - viewOrder.indexOf(b.view)
  );

  const currentImage = selectedView
    ? images.find((img) => img.view === selectedView)
    : images[0];

  const handleDownload = useCallback(async (url: string, view: string) => {
    await downloadImage(url, `cortex3d-${view}-${Date.now()}.png`);
  }, []);

  /** 一键下载所有视角图片 */
  const handleDownloadAll = useCallback(async () => {
    if (sortedImages.length === 0) return;
    setIsDownloadingAll(true);
    const ts = Date.now();
    for (let i = 0; i < sortedImages.length; i++) {
      const img = sortedImages[i];
      await downloadImage(img.url, `cortex3d-${img.view}-${ts}.png`);
      // 间隔 300ms 避免浏览器拦截多次下载
      if (i < sortedImages.length - 1) {
        await new Promise((r) => setTimeout(r, 300));
      }
    }
    setIsDownloadingAll(false);
  }, [sortedImages]);

  const currentIndex = sortedImages.findIndex((img) => img.view === selectedView);

  const goToPrevious = () => {
    const newIndex = currentIndex > 0 ? currentIndex - 1 : sortedImages.length - 1;
    setSelectedView(sortedImages[newIndex].view);
  };

  const goToNext = () => {
    const newIndex = currentIndex < sortedImages.length - 1 ? currentIndex + 1 : 0;
    setSelectedView(sortedImages[newIndex].view);
  };

  return (
    <Card variant="default" className="h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Eye className="w-5 h-5 text-accent-primary" />
          预览
          {generation && (
            <span className="text-sm font-normal text-text-muted">
              ({sortedImages.length} 个视角)
            </span>
          )}
        </h3>
        {currentImage && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(true)}
          >
            <Maximize2 className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Main Preview */}
      <div className="relative aspect-square bg-bg-secondary rounded-lg overflow-hidden mb-4">
        <AnimatePresence mode="wait">
          {isGenerating ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 bg-bg-secondary w-full h-full relative" style={{ minHeight: '300px' }}>
                <RealProgress
                  isProcessing={isGenerating}
                  progress={progressState?.progress || 0}
                  message={progressState?.message || '正在准备生成...'}
                />
              </div>
            </motion.div>
          ) : currentImage ? (
            <motion.img
              key={currentImage.id}
              src={currentImage.url}
              alt={currentImage.view}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="w-full h-full object-contain"
            />
          ) : null}
        </AnimatePresence>

        {/* Navigation Arrows */}
        {sortedImages.length > 1 && !isGenerating && (
          <>
            <button
              onClick={goToPrevious}
              className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goToNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </>
        )}
      </div>

      {/* View Name */}
      {currentImage && (
        <div className="text-center mb-4">
          <span className="text-sm font-medium text-text-secondary capitalize">
            {currentImage.view.replace(/([A-Z])/g, ' $1').trim()}
          </span>
        </div>
      )}

      {/* ===== Download Actions ===== */}
      {sortedImages.length > 0 && !isGenerating && (
        <div className="flex gap-2 mb-4">
          {/* 下载当前 */}
          {currentImage && (
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              onClick={() => handleDownload(currentImage.url, currentImage.view)}
              leftIcon={<Download className="w-4 h-4" />}
            >
              下载当前
            </Button>
          )}
          {/* 下载全部 */}
          <Button
            variant="primary"
            size="md"
            className="flex-1"
            onClick={handleDownloadAll}
            disabled={isDownloadingAll}
            leftIcon={
              isDownloadingAll
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <PackageOpen className="w-4 h-4" />
            }
          >
            {isDownloadingAll ? '下载中...' : `全部下载 (${sortedImages.length})`}
          </Button>
        </div>
      )}

      {/* Image Grid */}
      {sortedImages.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-text-muted uppercase tracking-wider">全部视角</p>
          <ImageGrid
            images={sortedImages}
            selectedView={selectedView}
            onSelectView={setSelectedView}
          />
        </div>
      )}

      {/* Fullscreen Modal */}
      {isFullscreen && currentImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setIsFullscreen(false)}
        >
          <div className="absolute top-4 right-4 flex gap-2">
            <button
              className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                handleDownload(currentImage.url, currentImage.view);
              }}
              title="下载当前图片"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
              onClick={() => setIsFullscreen(false)}
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          </div>
          <motion.img
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            src={currentImage.url}
            alt={currentImage.view}
            className="max-w-full max-h-full object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </Card>
  );
};
