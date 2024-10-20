// Copyright (c) Microsoft. All rights reserved.

import { convertToExcalidrawElements, Excalidraw } from '@excalidraw/excalidraw';
import { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types/types';
import { parseMermaidToExcalidraw } from '@excalidraw/mermaid-to-excalidraw';
import {
    Button,
    makeStyles,
    Popover,
    PopoverSurface,
    PopoverTrigger,
    shorthands,
    Text,
    tokens,
    Tooltip,
} from '@fluentui/react-components';
import { ErrorCircle20Regular, Info20Regular, ZoomFit24Regular } from '@fluentui/react-icons';
import React from 'react';
import { DebugInspector } from '../DebugInspector';

const useClasses = makeStyles({
    root: {
        whiteSpace: 'normal',
        display: 'flex',
        flexDirection: 'column',
    },
    inspectorTrigger: {
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        color: tokens.colorStatusDangerForeground1,
        gap: tokens.spacingHorizontalXXS,
        cursor: 'pointer',
    },
    dialogTrigger: {
        position: 'relative',
    },
    inlineActions: {
        position: 'absolute',
        top: 0,
        right: 0,
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: tokens.spacingHorizontalS,
    },
    dialogSurface: {
        position: 'fixed',
        zIndex: tokens.zIndexPopup,
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        textAlign: 'center',
        backgroundColor: tokens.colorNeutralBackground1,
    },
    dialogContent: {
        ...shorthands.padding(tokens.spacingVerticalM),
    },
    dialogActions: {
        position: 'absolute',
        bottom: tokens.spacingVerticalM,
        right: tokens.spacingHorizontalM,
    },
    excalidraw: {
        height: '500px',
        width: '50vw',
        '& .mobile-misc-tools-container': {
            display: 'none !important',
        },
    },
});

interface ExcalidrawContentRenderProps {
    content: string;
    clickToZoom?: boolean;
}

export const ExcalidrawContentRenderer: React.FC<ExcalidrawContentRenderProps> = (props) => {
    const { content, clickToZoom } = props;
    const classes = useClasses();
    const [excalidrawAPI, setExcalidrawAPI] = React.useState<ExcalidrawImperativeAPI | null>(null);
    const [parseError, setParseError] = React.useState<Error | null>(null);
    const [isPopupOpen, setIsPopupOpen] = React.useState(false);

    // use regex to extract the mermaid definition from the content
    const match = content.match(/```mermaid([\s\S]+?)```/);
    const mermaidDefinition = match ? match[1] : content;

    React.useEffect(() => {
        if (!excalidrawAPI) {
            return;
        }

        if (mermaidDefinition === '') {
            excalidrawAPI.resetScene();
            return;
        }

        const getExcalidrawElements = async () => {
            try {
                const { elements, files } = await parseMermaidToExcalidraw(content, {
                    themeVariables: {
                        fontSize: '18px',
                    },
                });

                excalidrawAPI.updateScene({
                    elements: convertToExcalidrawElements(elements),
                });
                excalidrawAPI.scrollToContent(excalidrawAPI.getSceneElements(), {
                    fitToContent: true,
                });

                if (files) {
                    excalidrawAPI.addFiles(Object.values(files));
                }
            } catch (error) {
                setParseError(error as Error);
                return;
            }
        };
        getExcalidrawElements();
    }, [content, excalidrawAPI, mermaidDefinition]);

    const mermaidDiagram = (
        <div className={classes.excalidraw}>
            <Excalidraw
                initialData={{
                    appState: {
                        viewBackgroundColor: '#fafafa',
                        currentItemFontFamily: 1,
                    },
                }}
                excalidrawAPI={(api) => setExcalidrawAPI(api)}
            />
        </div>
    );

    return (
        <div className={classes.root}>
            {parseError && (
                <DebugInspector
                    trigger={
                        <Tooltip
                            content="Display debug information to indicate how this content was created."
                            relationship="label"
                        >
                            <div className={classes.inspectorTrigger}>
                                <ErrorCircle20Regular />
                                <Text>Error parsing mermaid content. Click for more information.</Text>
                            </div>
                        </Tooltip>
                    }
                    debug={{
                        parseError,
                    }}
                />
            )}
            {clickToZoom && (
                <div className={classes.dialogTrigger}>
                    <div className={classes.inlineActions}>
                        <Popover openOnHover>
                            <PopoverTrigger>
                                <Info20Regular />
                            </PopoverTrigger>
                            <PopoverSurface>
                                <pre>{content.trim()}</pre>
                            </PopoverSurface>
                        </Popover>
                        <Tooltip content="Zoom diagram" relationship="label">
                            <Button icon={<ZoomFit24Regular />} onClick={() => setIsPopupOpen(true)} />
                        </Tooltip>
                    </div>
                    {mermaidDiagram}
                </div>
            )}
            {clickToZoom && isPopupOpen && (
                <div className={classes.dialogSurface}>
                    <div className={classes.dialogContent}>
                        <ExcalidrawContentRenderer content={content} />
                    </div>
                    <div className={classes.dialogActions}>
                        <Button appearance="primary" onClick={() => setIsPopupOpen(false)}>
                            Close
                        </Button>
                    </div>
                </div>
            )}
            {!clickToZoom && mermaidDiagram}
        </div>
    );
};
