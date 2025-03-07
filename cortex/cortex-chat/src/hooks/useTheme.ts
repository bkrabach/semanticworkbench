import { useContext } from 'react';
import { ThemeContext, ThemeContextType } from '../context/theme-context';

// Custom hook to use the theme context
export function useTheme(): ThemeContextType {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}