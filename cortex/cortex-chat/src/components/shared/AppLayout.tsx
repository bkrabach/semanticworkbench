import React, { useState } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Button,
    Avatar,
    Menu,
    MenuTrigger,
    MenuList,
    MenuItem,
    MenuPopover,
    Divider,
    mergeClasses
} from '@fluentui/react-components';
import { 
    Navigation24Regular, 
    Person24Regular, 
    Settings24Regular, 
    DismissRegular,
    ChevronRight20Regular
} from '@fluentui/react-icons';
import { User } from '@/types';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        height: '100vh', // Full viewport height
        maxHeight: '100vh', // Prevent overflow
        backgroundColor: tokens.colorNeutralBackground2,
        position: 'relative',
        overflow: 'hidden',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('0.75rem', '1rem'),
        backgroundColor: tokens.colorBrandBackground,
        color: tokens.colorNeutralForegroundOnBrand,
        height: '3.5rem',
        width: '100%',
        position: 'relative',
        zIndex: 30,
    },
    logo: {
        fontWeight: 'bold',
        fontSize: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('0.5rem'),
    },
    userInfo: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('0.5rem'),
    },
    username: {
        fontWeight: 'semibold',
        // Hide username text on smaller screens, show only avatar
        '@media (max-width: 640px)': {
            display: 'none',
        },
    },
    userMenuButton: {
        color: tokens.colorNeutralForegroundOnBrand,
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('0.5rem'),
        ...shorthands.padding('0.25rem', '0.5rem'),
        ...shorthands.borderRadius('1rem'),
        ':hover': {
            backgroundColor: tokens.colorBrandBackgroundHover,
        },
        // Increase touch target size on mobile
        '@media (max-width: 640px)': {
            ...shorthands.padding('0.5rem'),
        },
    },
    main: {
        display: 'flex',
        flex: 1,
        position: 'relative',
        height: 'calc(100vh - 3.5rem - 2.5rem)', // Full height minus header and footer
        ...shorthands.overflow('hidden'),
    },
    sidebarContainer: {
        width: '100%', // Full width on mobile
        maxWidth: '280px',
        backgroundColor: tokens.colorNeutralBackground1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'absolute', // Absolutely positioned on mobile
        top: 0,
        left: 0,
        zIndex: 20,
        transform: 'translateX(-100%)', // Hidden by default on mobile
        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
        ...shorthands.borderRight('1px', 'solid', tokens.colorNeutralStroke2),
        boxShadow: 'none',
        
        // On larger screens, make it a normal part of the layout
        '@media (min-width: 768px)': {
            position: 'relative',
            transform: 'translateX(0)',
            boxShadow: 'none',
        },
    },
    sidebarVisible: {
        transform: 'translateX(0)',
        boxShadow: tokens.shadow16,
    },
    sidebarToggleButton: {
        position: 'absolute',
        top: '1rem',
        right: '-1.125rem',
        width: '2.25rem',
        height: '2.25rem',
        ...shorthands.borderRadius('50%'),
        backgroundColor: tokens.colorNeutralBackground1,
        zIndex: 25,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...shorthands.border('1px', 'solid', tokens.colorNeutralStroke2),
        boxShadow: tokens.shadow4,
        // Larger touch target on mobile
        '@media (max-width: 640px)': {
            width: '2.5rem',
            height: '2.5rem',
            top: '0.75rem',
        },
    },
    mobileOverlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.4)',
        zIndex: 15,
        display: 'none',
        '@media (max-width: 768px)': {
            display: 'block',
        },
    },
    contentContainer: {
        flex: 1,
        width: '100%', // Mobile first: full width
        height: '100%',
        ...shorthands.overflow('hidden'),
        transition: 'margin-left 0.3s ease, width 0.3s ease',
        position: 'relative',
        
        // On large screens, adjust width based on sidebar visibility
        '@media (min-width: 768px)': {
            width: 'calc(100% - 280px)',
            marginLeft: '280px',
        },
    },
    contentFullWidth: {
        // For desktop when sidebar is hidden
        '@media (min-width: 768px)': {
            width: '100%',
            marginLeft: 0,
        },
    },
    sidebarContent: {
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        ...shorthands.padding('1rem'),
        ...shorthands.overflow('hidden'),
    },
    footer: {
        ...shorthands.padding('0.5rem', '1rem'),
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke2),
        backgroundColor: tokens.colorNeutralBackground1,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        height: '2.5rem',
        width: '100%',
        position: 'relative',
        zIndex: 10,
    },
    footerText: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
    },
    hamburgerButton: {
        marginRight: '0.5rem',
        display: 'none',
        '@media (max-width: 768px)': {
            display: 'flex',
        },
    },
});

export interface AppLayoutProps {
    children: React.ReactNode;
    sidebar?: React.ReactNode;
    user: User | null;
    onLogout: () => void;
    className?: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
    children,
    sidebar,
    user,
    onLogout,
    className,
}) => {
    const styles = useStyles();
    const [isSidebarVisible, setIsSidebarVisible] = useState(false); // Default hidden on mobile, visible on desktop handled by CSS media query

    const toggleSidebar = () => {
        setIsSidebarVisible(!isSidebarVisible);
    };

    const formatUserName = (user: User | null) => {
        if (!user) return 'User';
        return user.name || user.email.split('@')[0];
    };

    // Function to handle clicks on the mobile overlay (to close the sidebar)
    const handleOverlayClick = () => {
        if (isSidebarVisible) {
            setIsSidebarVisible(false);
        }
    };

    return (
        <div className={mergeClasses(styles.container, className)}>
            <header className={styles.header}>
                <div className={styles.logo}>
                    {/* Mobile hamburger menu button */}
                    <Button
                        className={styles.hamburgerButton}
                        appearance="subtle"
                        icon={<Navigation24Regular />}
                        onClick={toggleSidebar}
                        aria-label="Menu"
                        size="small"
                    />
                    Cortex Chat
                </div>
                
                {user && (
                    <div className={styles.userInfo}>
                        <Menu>
                            <MenuTrigger disableButtonEnhancement>
                                <button className={styles.userMenuButton}>
                                    <Avatar 
                                        name={formatUserName(user)} 
                                        size={32} 
                                        color="colorful" 
                                    />
                                    <span className={styles.username}>{formatUserName(user)}</span>
                                </button>
                            </MenuTrigger>
                            <MenuPopover>
                                <MenuList>
                                    <MenuItem icon={<Person24Regular />}>Profile</MenuItem>
                                    <MenuItem icon={<Settings24Regular />}>Settings</MenuItem>
                                    <Divider />
                                    <MenuItem onClick={onLogout}>Logout</MenuItem>
                                </MenuList>
                            </MenuPopover>
                        </Menu>
                    </div>
                )}
            </header>
            
            <main className={styles.main}>
                {/* Mobile overlay - only visible when sidebar is open on mobile */}
                {isSidebarVisible && (
                    <div className={styles.mobileOverlay} onClick={handleOverlayClick} />
                )}
                
                {sidebar && (
                    <aside className={`${styles.sidebarContainer} ${isSidebarVisible ? styles.sidebarVisible : ''}`}>
                        <Button 
                            className={styles.sidebarToggleButton} 
                            appearance="subtle"
                            icon={<DismissRegular />}
                            onClick={toggleSidebar}
                            aria-label="Toggle sidebar"
                        />
                        <div className={styles.sidebarContent}>
                            {sidebar}
                        </div>
                    </aside>
                )}
                
                <div className={`${styles.contentContainer} ${!isSidebarVisible ? styles.contentFullWidth : ''}`}>
                    {children}
                </div>
            </main>
            
            <footer className={styles.footer}>
                <div className={styles.footerText}>
                    Cortex Chat &copy; {new Date().getFullYear()}
                </div>
            </footer>
        </div>
    );
};