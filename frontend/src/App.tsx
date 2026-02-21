import { useState } from 'react';
import GenerationPage from './pages/GenerationPage';
import ExtractClothesPage from './pages/ExtractClothesPage';
import ChangeClothesPage from './pages/ChangeClothesPage';
import ChangeStylePage from './pages/ChangeStylePage';
import type { FeatureTab } from './types';

function App() {
  const [activeTab, setActiveTab] = useState<FeatureTab>('generate');

  switch (activeTab) {
    case 'generate':
      return <GenerationPage activeTab={activeTab} onTabChange={setActiveTab} />;
    case 'extract-clothes':
      return <ExtractClothesPage activeTab={activeTab} onTabChange={setActiveTab} />;
    case 'change-clothes':
      return <ChangeClothesPage activeTab={activeTab} onTabChange={setActiveTab} />;
    case 'change-style':
      return <ChangeStylePage activeTab={activeTab} onTabChange={setActiveTab} />;
    default:
      return <GenerationPage activeTab={activeTab} onTabChange={setActiveTab} />;
  }
}

export default App;
