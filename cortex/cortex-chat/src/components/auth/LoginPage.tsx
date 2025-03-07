import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    makeStyles,
    tokens,
    shorthands,
    Button,
    Input,
    Card,
    CardHeader,
    Text,
    Spinner,
    Divider
} from '@fluentui/react-components';
import { Key24Regular } from '@fluentui/react-icons';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';

// Define styles for the login page
const useStyles = makeStyles({
    container: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        ...shorthands.padding(tokens.spacingVerticalXL),
        backgroundColor: tokens.colorNeutralBackground2,
    },
    loginCard: {
        maxWidth: '450px',
        width: '100%',
    },
    cardContent: {
        ...shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalL),
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap(tokens.spacingVerticalL),
    },
    formField: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap(tokens.spacingVerticalS),
    },
    label: {
        fontWeight: tokens.fontWeightSemibold,
    },
    errorMessage: {
        color: tokens.colorStatusDangerForeground1,
        fontSize: tokens.fontSizeBase200,
        ...shorthands.margin(tokens.spacingVerticalS, 0, 0, 0),
    },
    buttonContainer: {
        display: 'flex',
        justifyContent: 'flex-end',
        ...shorthands.margin(tokens.spacingVerticalL, 0, 0, 0),
    },
    helpText: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
    },
    header: {
        textAlign: 'center',
    },
    themeToggle: {
        display: 'flex',
        justifyContent: 'center',
        ...shorthands.padding(tokens.spacingVerticalS),
    },
    title: {
        ...shorthands.margin(0),
        fontSize: tokens.fontSizeBase600,
        fontWeight: tokens.fontWeightSemibold,
    }
});

/**
 * Login page component for token-based authentication
 */
const LoginPage: React.FC = () => {
    const styles = useStyles();
    const navigate = useNavigate();
    const { login, isLoading, error: authError } = useAuth();
    const { isDarkMode, setThemeMode } = useTheme();

    const [token, setToken] = useState('');
    const [error, setError] = useState<string | null>(null);

    // Handle form submission
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!token.trim()) {
            setError('Please enter an authentication token');
            return;
        }

        try {
            await login(token.trim());
            navigate('/');
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : 'Authentication failed. Please check your token and try again.'
            );
        }
    };

    // Toggle theme
    const toggleTheme = () => {
        setThemeMode(isDarkMode ? 'light' : 'dark');
    };

    return (
        <div className={styles.container}>
            <Card className={styles.loginCard}>
                <CardHeader
                    className={styles.header}
                    header={<h1 className={styles.title}>Cortex Chat</h1>}
                />

                <div className={styles.cardContent}>
                    <Text size={400} align="center">Sign in with your API token</Text>

                    <form onSubmit={handleSubmit}>
                        <div className={styles.formField}>
                            <label className={styles.label} htmlFor="token">
                                Authentication Token
                            </label>
                            <Input
                                id="token"
                                type="password"
                                contentBefore={<Key24Regular />}
                                value={token}
                                onChange={(_, data) => setToken(data.value)}
                                placeholder="Enter your token"
                                required
                            />
                            <Text className={styles.helpText}>
                                Enter the API token provided by your administrator.
                            </Text>

                            {(error || authError) && (
                                <Text className={styles.errorMessage}>
                                    {error || (authError instanceof Error ? authError.message : String(authError))}
                                </Text>
                            )}
                        </div>

                        <div className={styles.buttonContainer}>
                            <Button
                                appearance="primary"
                                type="submit"
                                disabled={isLoading}
                                icon={isLoading ? <Spinner size="tiny" /> : undefined}
                            >
                                {isLoading ? 'Signing in...' : 'Sign in'}
                            </Button>
                        </div>
                    </form>

                    <Divider />

                    <div className={styles.themeToggle}>
                        <Button
                            appearance="subtle"
                            onClick={toggleTheme}
                        >
                            Switch to {isDarkMode ? 'Light' : 'Dark'} Mode
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};

export default LoginPage;