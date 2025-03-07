import React from 'react';
import { makeStyles, tokens, Spinner, Text } from '@fluentui/react-components';

// Define styles for the typing indicator
const useStyles = makeStyles({
    container: {
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacingHorizontalS,
        marginTop: tokens.spacingVerticalS,
    },
    dots: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
    },
    dot: {
        height: '6px',
        width: '6px',
        borderRadius: '50%',
        backgroundColor: tokens.colorNeutralForeground3,
        opacity: 0.7,
    },
    // Use CSS animations defined as strings
    dot1: {
        animationName: 'pulse',
        animationDuration: '0.8s',
        animationIterationCount: 'infinite',
        animationDirection: 'alternate',
    },
    dot2: {
        animationName: 'pulse',
        animationDuration: '0.8s',
        animationDelay: '0.2s',
        animationIterationCount: 'infinite',
        animationDirection: 'alternate',
    },
    dot3: {
        animationName: 'pulse',
        animationDuration: '0.8s',
        animationDelay: '0.4s',
        animationIterationCount: 'infinite',
        animationDirection: 'alternate',
    },
    '@keyframes pulse': {
        from: { opacity: 0.3 },
        to: { opacity: 1 }
    },
    text: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
    }
});

interface StreamingIndicatorProps {
    text?: string;
    showSpinner?: boolean;
}

/**
 * Animated typing indicator for streaming responses
 */
const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
    text = 'Typing',
    showSpinner = false
}) => {
    const styles = useStyles();

    return (
        <div className={styles.container}>
            {showSpinner && <Spinner size="tiny" />}
            <Text className={styles.text}>{text}</Text>
            <div className={styles.dots}>
                <div className={`${styles.dot} ${styles.dot1}`}></div>
                <div className={`${styles.dot} ${styles.dot2}`}></div>
                <div className={`${styles.dot} ${styles.dot3}`}></div>
            </div>
        </div>
    );
};

export default StreamingIndicator;