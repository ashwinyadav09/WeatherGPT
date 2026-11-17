import React, { useEffect } from 'react';
import { LanguageProvider } from './i18n/LanguageContext';
import { AppLayout } from './layout/AppLayout';
import { installMockApiFallback } from './mocks/mockClient';

export const App: React.FC = () => {
  useEffect(() => {
    // Automatically fall back to mock data if backend server is not running
    installMockApiFallback();
  }, []);

  return (
    <LanguageProvider>
      <AppLayout />
    </LanguageProvider>
  );
};

export default App;
