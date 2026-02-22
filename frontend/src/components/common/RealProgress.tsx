import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface RealProgressProps {
    isProcessing: boolean;
    progress: number; // 0-100
    message: string;
}

export const RealProgress: React.FC<RealProgressProps> = ({
    isProcessing,
    progress,
    message
}) => {
    if (!isProcessing) return null;

    return (
        <div className="w-full max-w-sm mx-auto flex flex-col items-center justify-center py-8">
            <Loader2 className="w-12 h-12 text-accent-primary animate-spin mb-4" />

            <p className="text-text-secondary mb-3 font-medium text-center">
                {message || "正在处理..."}
            </p>

            {/* Progress Bar Container */}
            <div className="w-full h-1.5 bg-bg-hover rounded-full overflow-hidden mb-2 relative">
                <motion.div
                    className="h-full bg-accent-primary absolute left-0 top-0"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
                    transition={{ ease: "linear", duration: 0.3 }}
                />
            </div>

            {/* Percentage estimate */}
            <p className="text-xs text-text-muted">
                当前进度: {Math.round(progress)}%
            </p>
        </div>
    );
};
