import React from 'react';
import { Navbar } from './Navbar';
import type { FeatureTab } from '../../types';

interface MainLayoutProps {
  children: React.ReactNode;
  onSettingsClick?: () => void;
  activeTab: FeatureTab;
  onTabChange: (tab: FeatureTab) => void;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, onSettingsClick, activeTab, onTabChange }) => {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Navbar onSettingsClick={onSettingsClick} activeTab={activeTab} onTabChange={onTabChange} />
      <main className="pt-16 min-h-screen">
        {children}
      </main>
    </div>
  );
};
