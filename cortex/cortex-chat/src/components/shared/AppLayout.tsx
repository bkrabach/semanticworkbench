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
        backgroundColor: tokens.colorNeutralBackground2,
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('12px', '16px'),
        backgroundColor: tokens.colorBrandBackground,
        color: tokens.colorNeutralForegroundOnBrand,
        height: '56px',
    },
    logo: {
        fontWeight: 'bold',
        fontSize: '1.25rem',
    },
    userInfo: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('8px'),
    },
    username: {
        fontWeight: 'semibold',
    },
    userMenuButton: {
        color: tokens.colorNeutralForegroundOnBrand,
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('8px'),
        ...shorthands.padding('4px', '8px'),
        ...shorthands.borderRadius('16px'),
        ':hover': {
            backgroundColor: tokens.colorBrandBackgroundHover,
        },
    },
    main: {
        display: 'flex',
        flex: 1,
        position: 'relative',
        ...shorthands.overflow('hidden'),
    },
    sidebarContainer: {
        width: '280px',
        backgroundColor: tokens.colorNeutralBackground1,
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.borderRight('1px', 'solid', tokens.colorNeutralStroke2),
        height: 'calc(100vh - 56px)',
        position: 'relative',
        transition: 'transform 0.3s ease',
    },
    sidebarHidden: {
        transform: 'translateX(-100%)',
        position: 'absolute',
        zIndex: 10,
        height: 'calc(100vh - 56px)',
    },
    sidebarToggleButton: {
        position: 'absolute',
        top: '16px',
        right: '-18px',
        width: '36px',
        height: '36px',
        ...shorthands.borderRadius('50%'),
        backgroundColor: tokens.colorNeutralBackground1,
        zIndex: 20,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...shorthands.border('1px', 'solid', tokens.colorNeutralStroke2),
        boxShadow: tokens.shadow4,
    },
    contentContainer: {
        flex: 1,
        ...shorthands.overflow('hidden'),
        transition: 'width 0.3s ease, margin-left 0.3s ease',
    },
    contentWithSidebar: {
        width: 'calc(100% - 280px)',
    },
    contentFullWidth: {
        width: '100%',
    },
    sidebarContent: {
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        ...shorthands.padding('16px'),
        ...shorthands.overflow('hidden'),
    },
    footer: {
        ...shorthands.padding('8px', '16px'),
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke2),
        backgroundColor: tokens.colorNeutralBackground1,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    footerText: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
    },
    mobileMenuButton: {
        display: 'none',
        '@media (max-width: 768px)': {
            display: 'block',
        },
    },
    '@media (max-width: 768px)': {
        sidebarContainer: {
            position: 'absolute',
            zIndex: 100,
            width: '280px',
        },
        contentContainer: {
            width: '100% !important',
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
    const [isSidebarVisible, setIsSidebarVisible] = useState(true);

    const toggleSidebar = () => {
        setIsSidebarVisible(!isSidebarVisible);
    };

    const formatUserName = (user: User | null) => {
        if (!user) return 'User';
        return user.name || user.email.split('@')[0];
    };

    return (
        <div className={mergeClasses(styles.container, className)}>
            <header className={styles.header}>
                <div className={styles.logo}>Cortex Chat</div>
                
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
                {sidebar && (
                    <aside className={`${styles.sidebarContainer} ${!isSidebarVisible ? styles.sidebarHidden : ''}`}>
                        <Button 
                            className={styles.sidebarToggleButton} 
                            appearance="subtle"
                            icon={isSidebarVisible ? <DismissRegular /> : <ChevronRight20Regular />}
                            onClick={toggleSidebar}
                            aria-label={isSidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
                        />
                        <div className={styles.sidebarContent}>
                            {sidebar}
                        </div>
                    </aside>
                )}
                
                <div className={`${styles.contentContainer} ${isSidebarVisible && sidebar ? styles.contentWithSidebar : styles.contentFullWidth}`}>
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