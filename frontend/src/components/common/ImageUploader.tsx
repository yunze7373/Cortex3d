import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Upload, X, Loader2 } from 'lucide-react';

interface ImageUploaderProps {
  onImageSelect: (base64: string) => void;
  currentImage?: string | null;
  onImageRemove?: () => void;
  label?: string;
  helperText?: string;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onImageSelect,
  currentImage,
  onImageRemove,
  label = 'Upload Image',
  helperText,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setIsLoading(true);
      try {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          onImageSelect(base64);
          setIsLoading(false);
        };
        reader.onerror = () => {
          setIsLoading(false);
        };
        reader.readAsDataURL(file);
      } catch (error) {
        setIsLoading(false);
      }
    },
    [onImageSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
    },
    maxFiles: 1,
    disabled: !!currentImage,
  });

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text-secondary mb-1.5">
          {label}
        </label>
      )}

      <AnimatePresence mode="wait">
        {currentImage ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative aspect-square rounded-lg overflow-hidden border border-border-subtle bg-bg-secondary"
          >
            <img
              src={currentImage}
              alt="Uploaded"
              className="w-full h-full object-cover"
            />
            {onImageRemove && (
              <button
                onClick={onImageRemove}
                className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white hover:bg-accent-error transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </motion.div>
        ) : (
          <div
            {...getRootProps()}
            className={cn(
              'relative aspect-square rounded-lg border-2 border-dashed cursor-pointer',
              'transition-all duration-200',
              isDragActive
                ? 'border-accent-primary bg-accent-primary/10'
                : 'border-border-subtle hover:border-accent-primary/50 hover:bg-bg-hover',
              isLoading && 'pointer-events-none opacity-50'
            )}
          >
            <input {...getInputProps()} />
            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
              {isLoading ? (
                <Loader2 className="w-8 h-8 text-accent-primary animate-spin mb-2" />
              ) : (
                <div className="p-3 rounded-full bg-bg-hover mb-3">
                  <Upload className="w-6 h-6 text-text-muted" />
                </div>
              )}
              <p className="text-sm text-text-secondary">
                {isDragActive ? '拖放图片到这里' : '拖放或点击上传图片'}
              </p>
              <p className="text-xs text-text-muted mt-1">支持 PNG、JPG、WEBP 格式，最大 10MB</p>
            </div>
          </div>
        )}
      </AnimatePresence>

      {helperText && !currentImage && (
        <p className="mt-1.5 text-sm text-text-muted">{helperText}</p>
      )}
    </div>
  );
};

interface ImageGridProps {
  images: { id: string; view: string; url: string }[];
  selectedView?: string;
  onSelectView?: (view: string) => void;
}

export const ImageGrid: React.FC<ImageGridProps> = ({ images, selectedView, onSelectView }) => {
  return (
    <div className="grid grid-cols-2 gap-2">
      {images.map((image) => (
        <motion.button
          key={image.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={() => onSelectView?.(image.view)}
          className={cn(
            'relative aspect-square rounded-lg overflow-hidden border-2 transition-all duration-200',
            selectedView === image.view
              ? 'border-accent-primary shadow-glow'
              : 'border-transparent hover:border-border-subtle'
          )}
        >
          <img src={image.url} alt={image.view} className="w-full h-full object-cover" />
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
            <span className="text-xs text-white font-medium capitalize">{image.view}</span>
          </div>
        </motion.button>
      ))}
    </div>
  );
};
