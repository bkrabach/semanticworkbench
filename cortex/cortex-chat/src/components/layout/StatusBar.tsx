import React from 'react';
import {
    makeStyles,
    tokens,
    Text,
    Badge,
    Tooltip,
    shorthands
} from '@fluentui/react-components';
import { useConversationStream } from '../../api/hooks/useSSE';
import { useParams } from 'react-router-dom';

// Define styles for the status bar
const useStyles = makeStyles({
    statusBar: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: tokens.colorNeutralBackground3,
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke1),
        ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalM),
        minHeight: '28px',
    },
    statusItem: {
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacingHorizontalS,
    },
    statusText: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
    },
    statusGroup: {
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacingHorizontalM,
    }
});

// Map connection status to badge colors
const getConnectionBadgeProps = (status: string) => {
    switch (status) {
        case 'connected':
            return { color: 'success', text: 'Connected' };
        case 'connecting':
            return { color: 'warning', text: 'Connecting...' };
        case 'error':
            return { color: 'danger', text: 'Connection Error' };
        default:
            return { color: 'informative', text: 'Disconnected' };
    }
};

/**
 * Status bar component showing connection status and other info
 */
const StatusBar: React.FC = () => {
    const styles = useStyles();
    const { conversationId } = useParams<{ conversationId?: string }>();
    const { status: sseStatus } = useConversationStream(conversationId);

    const connectionStatus = getConnectionBadgeProps(sseStatus);

    return (
        <div className={styles.statusBar}>
            <div className={styles.statusGroup}>
                <div className={styles.statusItem}>
                    <Text className={styles.statusText}>Server:</Text>
                    <Tooltip content={connectionStatus.text} relationship="label">
                        <Badge
                            appearance="filled"
                            color={connectionStatus.color as 'success' | 'warning' | 'danger' | 'informative'}
                            shape="rounded"
                            size="small"
                        />
                    </Tooltip>
                </div>
            </div>

            <div className={styles.statusGroup}>
                <Text className={styles.statusText}>Cortex Chat</Text>
            </div>
        </div>
    );
};

export default StatusBar;