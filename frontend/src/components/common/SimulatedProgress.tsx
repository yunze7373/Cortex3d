import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface SimulatedProgressProps {
    isProcessing: boolean;
    estimatedTime?: number; // in seconds
    messages?: string[];
}

export const SimulatedProgress: React.FC<SimulatedProgressProps> = ({
    isProcessing,
    estimatedTime = 30,
    messages = ["正在初始化...", "正在生成详情...", "正在优化图像...", "即将完成..."]
}) => {
    const [progress, setProgress] = useState(0);
    const [messageIndex, setMessageIndex] = useState(0);

    useEffect(() => {
        if (!isProcessing) {
            setProgress(0);
            setMessageIndex(0);
            return;
        }

        // Every 100ms update
        const updateInterval = 100;
        const totalSteps = (estimatedTime * 1000) / updateInterval;
        let currentStep = 0;

        const timer = setInterval(() => {
            currentStep++;
            const rawProgress = (currentStep / totalSteps) * 100;

            // Asymptotically approach 95%
            const newProgress = Math.min(
                100 - (100 * Math.exp(-rawProgress / 30)),
                95
            );

            setProgress(newProgress);
        }, updateInterval);

        return () => clearInterval(timer);
    }, [isProcessing, estimatedTime]);

    useEffect(() => {
        if (!isProcessing || messages.length <= 1) return;

        // Change message evenly over the estimated time
        const messageInterval = Math.max(2000, (estimatedTime * 1000) / (messages.length + 1));

        const timer = setInterval(() => {
            setMessageIndex(prev => Math.min(prev + 1, messages.length - 1));
        }, messageInterval);

        return () => clearInterval(timer);
    }, [isProcessing, estimatedTime, messages.length]);

    if (!isProcessing) return null;

    return (
        <div className="w-full max-w-sm mx-auto flex flex-col items-center justify-center py-8">
            <Loader2 className="w-12 h-12 text-accent-primary animate-spin mb-4" />
            <p className="text-text-secondary mb-3 font-medium text-center">
                {messages[messageIndex] || "正在处理..."}
            </p>

            {/* Progress Bar Container */}
            <div className="w-full h-1.5 bg-bg-hover rounded-full overflow-hidden mb-2">
                <motion.div
                    className="h-full bg-accent-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ ease: "linear", duration: 0.1 }}
                />
            </div>

            {/* Time estimate */}
            <p className="text-xs text-text-muted">
                预计需要 {estimatedTime} 秒左右，请耐心等待
            </p>
        </div>
    );
};
