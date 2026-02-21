import React from 'react';
import { motion } from 'framer-motion';
import { Settings, Github, Menu, X, Wand2, Shirt, Sparkles, Palette } from 'lucide-react';
import { Button } from '../common';
import type { FeatureTab } from '../../types';

interface NavbarProps {
  onSettingsClick?: () => void;
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

const tabs: { id: FeatureTab; label: string; icon: React.ReactNode }[] = [
  { id: 'generate', label: '图像生成', icon: <Wand2 className="w-4 h-4" /> },
  { id: 'extract-clothes', label: '服装提取', icon: <Shirt className="w-4 h-4" /> },
  { id: 'change-clothes', label: '换衣服', icon: <Sparkles className="w-4 h-4" /> },
  { id: 'change-style', label: '风格切换', icon: <Palette className="w-4 h-4" /> },
];

export const Navbar: React.FC<NavbarProps> = ({ onSettingsClick, activeTab, onTabChange }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-lg border-b border-border-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center">
              <span className="text-white font-bold text-lg">C</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">Cortex3d</h1>
              <p className="text-xs text-text-muted hidden sm:block">AI图像生成工作室</p>
            </div>
          </motion.div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {/* Feature Tabs */}
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-accent-primary/20 text-accent-primary'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Settings */}
          <div className="hidden md:flex items-center gap-2 ml-4">
            <Button variant="ghost" size="sm" onClick={onSettingsClick}>
              <Settings className="w-4 h-4 mr-2" />
              设置
            </Button>
            <Button variant="ghost" size="sm">
              <Github className="w-4 h-4 mr-2" />
              GitHub
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="md:hidden border-t border-border-subtle bg-bg-secondary"
        >
          <div className="px-4 py-3 space-y-2">
            {/* Mobile Tabs */}
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  onTabChange(tab.id);
                  setIsMobileMenuOpen(false);
                }}
                className={`flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-accent-primary/20 text-accent-primary'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
            <div className="border-t border-border-subtle my-2" />
            <Button
              variant="ghost"
              className="w-full justify-start"
              size="sm"
              onClick={() => {
                onSettingsClick?.();
                setIsMobileMenuOpen(false);
              }}
            >
              <Settings className="w-4 h-4 mr-2" />
              设置
            </Button>
            <Button variant="ghost" className="w-full justify-start" size="sm">
              <Github className="w-4 h-4 mr-2" />
              GitHub
            </Button>
          </div>
        </motion.div>
      )}
    </nav>
  );
};
