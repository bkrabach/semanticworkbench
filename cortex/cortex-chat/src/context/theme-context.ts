import { createContext } from 'react';
import { Theme } from '@fluentui/react-components';

// Theme type
export type ThemeMode = 'light' | 'dark' | 'system';

// Theme context type
export interface ThemeContextType {
    currentTheme: Theme;
    themeMode: ThemeMode;
    setThemeMode: (mode: ThemeMode) => void;
    isDarkMode: boolean;
}

// Create the context
export const ThemeContext = createContext<ThemeContextType | undefined>(undefined);