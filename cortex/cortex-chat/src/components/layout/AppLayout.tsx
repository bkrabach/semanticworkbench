import React, { ReactNode } from 'react';
import {
    makeStyles,
    tokens,
    shorthands
} from '@fluentui/react-components';
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'

// Define styles for the layout
const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: tokens.colorNeutralBackground2,
    },
    main: {
        display: 'flex',
        flexGrow: 1,
        overflow: 'hidden',
    },
    contentWrapper: {
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        height: '100%',
        overflow: 'hidden',
        backgroundColor: tokens.colorNeutralBackground1,
    },
    content: {
        flexGrow: 1,
        overflow: 'auto',
        ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalM),
    }
});

interface AppLayoutProps {
    children: ReactNode;
    showSidebar?: boolean;
}

/**
 * Main application layout component with sidebar, content area, and status bar
 */
const AppLayout: React.FC<AppLayoutProps> = ({
    children,
    showSidebar = true
}) => {
    const styles = useStyles();

    return (
        <div className={styles.container}>
            <div className={styles.main}>
                {showSidebar && <Sidebar />}
                <div className={styles.contentWrapper}>
                    <main className={styles.content}>
                        {children}
                    </main>
                    <StatusBar />
                </div>
            </div>
        </div>
    );
};

export default AppLayout;