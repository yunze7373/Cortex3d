import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Loader2, Sparkles } from 'lucide-react';

interface ProgressIndicatorProps {
  progress?: number;
  status?: 'idle' | 'generating' | 'processing' | 'complete' | 'error';
  message?: string;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  progress,
  status = 'idle',
  message,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'generating':
        return {
          icon: <Loader2 className="w-5 h-5 animate-spin" />,
          text: message || '正在生成图像...',
          color: 'bg-accent-primary',
        };
      case 'processing':
        return {
          icon: <Sparkles className="w-5 h-5 animate-pulse" />,
          text: message || '处理中...',
          color: 'bg-accent-secondary',
        };
      case 'complete':
        return {
          icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ),
          text: '完成!',
          color: 'bg-accent-success',
        };
      case 'error':
        return {
          icon: (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          ),
          text: message || '发生错误',
          color: 'bg-accent-error',
        };
      default:
        return {
          icon: null,
          text: '',
          color: 'bg-accent-primary',
        };
    }
  };

  const config = getStatusConfig();

  if (status === 'idle') return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <div className="flex items-center gap-3 mb-2">
        <span className={cn('text-accent-primary', config.icon && 'animate-spin')}>{config.icon}</span>
        <span className="text-sm text-text-secondary">{config.text}</span>
      </div>
      {progress !== undefined && (
        <div className="w-full h-1.5 bg-bg-secondary rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
            className={cn('h-full rounded-full', config.color)}
          />
        </div>
      )}
    </motion.div>
  );
};

interface LoadingOverlayProps {
  isLoading: boolean;
  message?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ isLoading, message }) => {
  if (!isLoading) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-bg-primary/80 backdrop-blur-sm flex items-center justify-center z-10"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <Loader2 className="w-12 h-12 text-accent-primary animate-spin" />
          <div className="absolute inset-0 w-12 h-12 border-2 border-accent-primary/30 rounded-full animate-ping" />
        </div>
        {message && <p className="text-text-secondary">{message}</p>}
      </div>
    </motion.div>
  );
};
