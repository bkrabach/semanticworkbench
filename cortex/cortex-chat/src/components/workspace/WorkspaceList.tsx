import React from 'react';
import {
    List,
    ListItem,
    Button,
    makeStyles,
    tokens,
    shorthands,
    Text,
    Subtitle1,
    Divider,
    Menu,
    MenuItem,
    MenuList,
    MenuPopover,
    MenuTrigger
} from '@fluentui/react-components';
import { Add20Regular, MoreHorizontal20Regular } from '@fluentui/react-icons';
import { Workspace } from '@/types';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap('8px'),
        width: '100%',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('4px', '8px'),
    },
    list: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap('4px'),
        maxHeight: '300px',
        overflowY: 'auto',
        ...shorthands.padding('4px', '0'),
    },
    listItem: {
        ...shorthands.borderRadius('4px'),
        ':hover': {
            backgroundColor: tokens.colorNeutralBackground1Hover,
        },
        ':focus': {
            outlineWidth: '2px',
            outlineStyle: 'solid',
            outlineColor: tokens.colorBrandStroke1,
        },
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        ...shorthands.padding('8px', '12px'),
    },
    selectedItem: {
        backgroundColor: tokens.colorNeutralBackground1Selected,
        ':hover': {
            backgroundColor: tokens.colorNeutralBackground1Selected,
        },
    },
    emptyState: {
        textAlign: 'center',
        color: tokens.colorNeutralForeground3,
        ...shorthands.padding('16px', '8px'),
    },
    itemText: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        flex: 1,
    },
});

export interface WorkspaceListProps {
    workspaces: Workspace[];
    selectedWorkspaceId?: string;
    onSelectWorkspace: (workspaceId: string) => void;
    onCreateWorkspace: () => void;
    onDeleteWorkspace?: (workspaceId: string) => void;
}

export const WorkspaceList: React.FC<WorkspaceListProps> = ({
    workspaces,
    selectedWorkspaceId,
    onSelectWorkspace,
    onCreateWorkspace,
    onDeleteWorkspace,
}) => {
    const styles = useStyles();

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <Subtitle1>Workspaces</Subtitle1>
                <Button 
                    appearance="subtle"
                    icon={<Add20Regular />}
                    onClick={onCreateWorkspace}
                    title="Create new workspace"
                    aria-label="Create new workspace"
                />
            </div>
            <Divider />
            
            {workspaces.length === 0 ? (
                <div className={styles.emptyState}>
                    <Text>No workspaces found</Text>
                    <Button 
                        appearance="primary"
                        onClick={onCreateWorkspace}
                        size="small"
                        style={{ marginTop: '8px' }}
                    >
                        Create Workspace
                    </Button>
                </div>
            ) : (
                <List className={styles.list}>
                    {workspaces.map((workspace) => (
                        <ListItem
                            key={workspace.id}
                            className={`${styles.listItem} ${selectedWorkspaceId === workspace.id ? styles.selectedItem : ''}`}
                            onClick={() => onSelectWorkspace(workspace.id)}
                        >
                            <Text className={styles.itemText}>{workspace.name}</Text>
                            
                            {onDeleteWorkspace && (
                                <Menu>
                                    <MenuTrigger disableButtonEnhancement>
                                        <Button
                                            appearance="subtle"
                                            icon={<MoreHorizontal20Regular />}
                                            aria-label="More options"
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                    </MenuTrigger>
                                    <MenuPopover>
                                        <MenuList>
                                            <MenuItem onClick={() => onDeleteWorkspace(workspace.id)}>
                                                Delete
                                            </MenuItem>
                                        </MenuList>
                                    </MenuPopover>
                                </Menu>
                            )}
                        </ListItem>
                    ))}
                </List>
            )}
        </div>
    );
};