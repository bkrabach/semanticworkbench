import React, { useMemo } from 'react';
import { makeStyles, tokens, shorthands } from '@fluentui/react-components';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../context/ThemeContext';

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

    return (
        <div className={styles.markdownContainer}>
            <ReactMarkdown
                components={{
                    code({ inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match && match[1] ? match[1] : 'text';

                        return !inline ? (
                            <SyntaxHighlighter
                                style={syntaxTheme}
                                language={language}
                                PreTag="div"
                                {...props}
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                        ) : (
                            <code className={className} {...props}>
                                {children}
                            </code>
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