import React, { useState } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Card,
    CardHeader,
    Text,
    Button,
    Badge,
    Tooltip,
    Spinner
} from '@fluentui/react-components';
import {
    ChevronDown16Regular,
    ChevronRight16Regular,
    Code16Regular,
    DocumentCopy16Regular,
    CheckmarkCircle16Regular,
    DismissCircle16Regular
} from '@fluentui/react-icons';
import { ToolExecution } from '../../api/types';
import MarkdownRenderer from './MarkdownRenderer';

// Define styles for the tool result view
const useStyles = makeStyles({
    toolCard: {
        ...shorthands.margin(tokens.spacingVerticalS, 0),
        backgroundColor: tokens.colorNeutralBackground2,
        ...shorthands.borderRadius(tokens.borderRadiusMedium),
    },
    toolHeader: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.gap(tokens.spacingHorizontalS),
        cursor: 'pointer',
    },
    toolName: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap(tokens.spacingHorizontalXS),
        fontWeight: tokens.fontWeightSemibold,
    },
    toolIcon: {
        color: tokens.colorBrandForeground1,
    },
    headerActions: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap(tokens.spacingHorizontalXS),
    },
    toolContent: {
        ...shorthands.padding(0, tokens.spacingHorizontalS, tokens.spacingVerticalS, tokens.spacingHorizontalS),
    },
    toolStatusSuccess: {
        backgroundColor: tokens.colorStatusSuccessBackground1,
        color: tokens.colorStatusSuccessForeground1,
    },
    toolStatusError: {
        backgroundColor: tokens.colorStatusDangerBackground1,
        color: tokens.colorStatusDangerForeground1,
    },
    toolStatusRunning: {
        backgroundColor: tokens.colorStatusWarningBackground1,
        color: tokens.colorStatusWarningForeground1,
    },
    toolContentItem: {
        ...shorthands.margin(tokens.spacingVerticalXS, 0),
    },
    copyButton: {
        minWidth: 'auto',
    },
    copySuccess: {
        color: tokens.colorStatusSuccessForeground1,
    },
    paramsTable: {
        width: '100%',
        fontSize: tokens.fontSizeBase200,
        tableLayout: 'fixed',
        borderCollapse: 'collapse',
        '& th, & td': {
            ...shorthands.padding(tokens.spacingVerticalXXS, tokens.spacingHorizontalXS),
            ...shorthands.borderBottom(`1px solid ${tokens.colorNeutralStroke3}`),
            textAlign: 'left',
        },
        '& th': {
            fontWeight: tokens.fontWeightSemibold,
            width: '30%',
        },
        '& td': {
            wordBreak: 'break-all',
        }
    }
});

interface ToolResultViewProps {
    toolExecution: ToolExecution;
}

/**
 * Component for displaying tool execution results
 */
const ToolResultView: React.FC<ToolResultViewProps> = ({ toolExecution }) => {
    const styles = useStyles();
    const [isExpanded, setIsExpanded] = useState(true);
    const [copySuccess, setCopySuccess] = useState(false);

    // Handle copying content to clipboard
    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text)
            .then(() => {
                setCopySuccess(true);
                setTimeout(() => setCopySuccess(false), 2000);
            })
            .catch(err => {
                console.error('Failed to copy text: ', err);
            });
    };

    // Determine tool status badge props
    const getStatusBadge = () => {
        if (!toolExecution.isComplete) {
            return {
                className: styles.toolStatusRunning,
                icon: <Spinner size="tiny" />,
                text: 'Running',
            };
        }

        if (toolExecution.error) {
            return {
                className: styles.toolStatusError,
                icon: <DismissCircle16Regular />,
                text: 'Error',
            };
        }

        return {
            className: styles.toolStatusSuccess,
            icon: <CheckmarkCircle16Regular />,
            text: 'Success',
        };
    };

    const statusBadge = getStatusBadge();

    return (
        <Card className={styles.toolCard}>
            <CardHeader
                className={styles.toolHeader}
                onClick={() => setIsExpanded(!isExpanded)}
                header={
                    <div className={styles.toolName}>
                        {isExpanded ? <ChevronDown16Regular /> : <ChevronRight16Regular />}
                        <Code16Regular className={styles.toolIcon} />
                        <Text>Tool: {toolExecution.name}</Text>
                    </div>
                }
                action={
                    <div className={styles.headerActions}>
                        <Badge
                            appearance="filled"
                            icon={statusBadge.icon}
                            className={statusBadge.className}
                        >
                            {statusBadge.text}
                        </Badge>
                        <Tooltip content="Copy result" relationship="label">
                            <Button
                                appearance="subtle"
                                icon={copySuccess ? <CheckmarkCircle16Regular className={styles.copySuccess} /> : <DocumentCopy16Regular />}
                                size="small"
                                className={styles.copyButton}
                                onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                                    e.stopPropagation();
                                    handleCopy(toolExecution.result || '');
                                }}
                                disabled={!toolExecution.result}
                            />
                        </Tooltip>
                    </div>
                }
            />

            {isExpanded && (
                <div className={styles.toolContent}>
                    {/* Tool parameters */}
                    {toolExecution.parameters && Object.keys(toolExecution.parameters).length > 0 && (
                        <div className={styles.toolContentItem}>
                            <Text weight="semibold" size={200}>Parameters:</Text>
                            <table className={styles.paramsTable}>
                                <tbody>
                                    {Object.entries(toolExecution.parameters).map(([key, value]) => (
                                        <tr key={key}>
                                            <th>{key}</th>
                                            <td>{typeof value === 'string' ? value : JSON.stringify(value)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Tool result */}
                    {toolExecution.result && (
                        <div className={styles.toolContentItem}>
                            <Text weight="semibold" size={200}>Result:</Text>
                            <MarkdownRenderer content={toolExecution.result} />
                        </div>
                    )}

                    {/* Tool error */}
                    {toolExecution.error && (
                        <div className={styles.toolContentItem}>
                            <Text weight="semibold" size={200} style={{ color: tokens.colorStatusDangerForeground1 }}>Error:</Text>
                            <Text style={{ color: tokens.colorStatusDangerForeground1 }}>{toolExecution.error}</Text>
                        </div>
                    )}

                    {/* Still running */}
                    {!toolExecution.isComplete && !toolExecution.result && !toolExecution.error && (
                        <div className={styles.toolContentItem}>
                            <Text size={200}>Executing tool...</Text>
                            <Spinner size="tiny" label="Running tool" />
                        </div>
                    )}
                </div>
            )}
        </Card>
    );
};

export default ToolResultView;