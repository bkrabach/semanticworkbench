import React, { useMemo } from 'react';
import { makeStyles, tokens, shorthands } from '@fluentui/react-components';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../hooks/useTheme';

// Define styles for the markdown content
const useStyles = makeStyles({
    markdownContainer: {
        fontFamily: tokens.fontFamilyBase,
        lineHeight: tokens.lineHeightBase500,
        '& p': {
            ...shorthands.margin(tokens.spacingVerticalXS, 0),
        },
        '& h1, & h2, & h3, & h4, & h5, & h6': {
            fontWeight: tokens.fontWeightSemibold,
            ...shorthands.margin(tokens.spacingVerticalM, 0, tokens.spacingVerticalXS, 0),
        },
        '& h1': {
            fontSize: tokens.fontSizeBase600,
        },
        '& h2': {
            fontSize: tokens.fontSizeBase500,
        },
        '& h3': {
            fontSize: tokens.fontSizeBase400,
        },
        '& h4, & h5, & h6': {
            fontSize: tokens.fontSizeBase300,
        },
        '& ul, & ol': {
            ...shorthands.margin(tokens.spacingVerticalXS, 0),
            ...shorthands.padding(0, 0, 0, tokens.spacingHorizontalL),
        },
        '& li': {
            ...shorthands.margin(tokens.spacingVerticalXXS, 0),
        },
        '& code': {
            fontFamily: tokens.fontFamilyMonospace,
            fontSize: tokens.fontSizeBase200,
            backgroundColor: tokens.colorNeutralBackground3,
            ...shorthands.padding(tokens.spacingVerticalXXS, tokens.spacingHorizontalXS),
            ...shorthands.borderRadius(tokens.borderRadiusSmall),
        },
        '& pre': {
            ...shorthands.margin(tokens.spacingVerticalS, 0),
            ...shorthands.padding(0),
            ...shorthands.overflow('auto'),
            ...shorthands.borderRadius(tokens.borderRadiusMedium),
            '& code': {
                ...shorthands.padding(0),
                backgroundColor: 'transparent',
            }
        },
        '& a': {
            color: tokens.colorBrandForeground1,
            textDecoration: 'none',
            '&:hover': {
                textDecoration: 'underline',
            }
        },
        '& blockquote': {
            ...shorthands.borderLeft(`4px solid ${tokens.colorNeutralStroke2}`),
            ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalM),
            ...shorthands.margin(tokens.spacingVerticalS, 0),
            backgroundColor: tokens.colorNeutralBackground2,
            ...shorthands.borderRadius(tokens.borderRadiusSmall),
        },
        '& table': {
            width: '100%',
            borderCollapse: 'collapse',
            ...shorthands.margin(tokens.spacingVerticalS, 0),
        },
        '& th, & td': {
            ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalS),
            ...shorthands.borderBottom(`1px solid ${tokens.colorNeutralStroke2}`),
            textAlign: 'left',
        },
        '& th': {
            fontWeight: tokens.fontWeightSemibold,
            backgroundColor: tokens.colorNeutralBackground3,
        }
    }
});

interface MarkdownRendererProps {
    content: string;
}

/**
 * Component for rendering markdown content with syntax highlighting
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
    const styles = useStyles();
    const { isDarkMode } = useTheme();

    // Choose syntax highlighting theme based on current app theme
    const syntaxTheme = useMemo(
        () => isDarkMode ? vscDarkPlus : vs,
        [isDarkMode]
    );

    // Safe cast using type assertion for SyntaxHighlighter's style prop
    const safeTheme = useMemo(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return syntaxTheme as any;
    }, [syntaxTheme]);

    return (
        <div className={styles.markdownContainer}>
            <ReactMarkdown
                components={{
                    // Type the props as any to overcome the type issue, then handle props carefully
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    code: (props: any) => {
                        const { className, children } = props;

                        // Check if this is a code block or inline code
                        const match = /language-(\w+)/.exec(className || '');
                        const isCodeBlock = !!match;
                        const language = match?.[1] || 'text';

                        if (!isCodeBlock) {
                            // For inline code, just render a code tag with className only
                            return <code className={className}>{children}</code>;
                        }

                        // For code blocks, use SyntaxHighlighter with minimal props
                        return (
                            <SyntaxHighlighter
                                style={safeTheme}
                                language={language}
                                PreTag="div"
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                        );
                    }
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;