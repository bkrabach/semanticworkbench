import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { FluentProvider, teamsLightTheme, teamsDarkTheme, Theme } from '@fluentui/react-components';

// Theme type
export type ThemeMode = 'light' | 'dark' | 'system';

// Theme context type
interface ThemeContextType {
    currentTheme: Theme;
    themeMode: ThemeMode;
    setThemeMode: (mode: ThemeMode) => void;
    isDarkMode: boolean;
}

// Create the context
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
    children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
    // Initialize theme from localStorage or default to 'system'
    const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
        const savedMode = localStorage.getItem('themeMode');
        return (savedMode as ThemeMode) || 'system';
    });

    const [isDarkMode, setIsDarkMode] = useState<boolean>(false);
    const [currentTheme, setCurrentTheme] = useState<Theme>(teamsLightTheme);

    // Effect to detect system theme preference
    useEffect(() => {
        const updateThemeBasedOnMode = () => {
            if (themeMode === 'system') {
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                setIsDarkMode(prefersDark);
                setCurrentTheme(prefersDark ? teamsDarkTheme : teamsLightTheme);
            } else {
                const isDark = themeMode === 'dark';
                setIsDarkMode(isDark);
                setCurrentTheme(isDark ? teamsDarkTheme : teamsLightTheme);
            }
        };

        // Set initial theme
        updateThemeBasedOnMode();

        // Handle system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = () => {
            if (themeMode === 'system') {
                updateThemeBasedOnMode();
            }
        };

        // Add event listener for theme changes
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleChange);
        } else {
            // Fallback for browsers that don't support addEventListener
            mediaQuery.addListener(handleChange);
        }

        // Clean up
        return () => {
            if (mediaQuery.removeEventListener) {
                mediaQuery.removeEventListener('change', handleChange);
            } else {
                // Fallback for browsers that don't support removeEventListener
                mediaQuery.removeListener(handleChange);
            }
        };
    }, [themeMode]);

    // Save theme preference to localStorage when it changes
    useEffect(() => {
        localStorage.setItem('themeMode', themeMode);
    }, [themeMode]);

    // Handler to update theme mode
    const handleSetThemeMode = (mode: ThemeMode) => {
        setThemeMode(mode);
    };

    // Context value
    const contextValue: ThemeContextType = {
        currentTheme,
        themeMode,
        setThemeMode: handleSetThemeMode,
        isDarkMode,
    };

    return (
        <ThemeContext.Provider value={contextValue}>
            <FluentProvider theme={currentTheme}>
                {children}
            </FluentProvider>
        </ThemeContext.Provider>
    );
}

// Custom hook to use the theme context
export function useTheme(): ThemeContextType {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}