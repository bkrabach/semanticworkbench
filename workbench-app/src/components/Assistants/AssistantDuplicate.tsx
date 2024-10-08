// Copyright (c) Microsoft. All rights reserved.

import { Button, DialogTrigger } from '@fluentui/react-components';
import { SaveCopy24Regular } from '@fluentui/react-icons';
import React from 'react';
import { useWorkbenchService } from '../../libs/useWorkbenchService';
import { Assistant } from '../../models/Assistant';
import { CommandButton } from '../App/CommandButton';

interface AssistantDuplicateProps {
    assistant: Assistant;
    iconOnly?: boolean;
    asToolbarButton?: boolean;
    onDuplicate?: (assistantId: string) => void;
    onDuplicateError?: (error: Error) => void;
}

export const AssistantDuplicate: React.FC<AssistantDuplicateProps> = (props) => {
    const { assistant, iconOnly, asToolbarButton, onDuplicate, onDuplicateError } = props;
    const workbenchService = useWorkbenchService();

    const duplicateAssistant = async () => {
        try {
            const newAssistantId = await workbenchService.duplicateAssistantAsync(assistant.id);
            onDuplicate?.(newAssistantId);
        } catch (error) {
            onDuplicateError?.(error as Error);
        }
    };

    return (
        <CommandButton
            description="Duplicate assistant"
            icon={<SaveCopy24Regular />}
            iconOnly={iconOnly}
            asToolbarButton={asToolbarButton}
            label="Duplicate"
            dialogContent={{
                title: 'Duplicate assistant',
                content: <p>Are you sure you want to duplicate this assistant?</p>,
                closeLabel: 'Cancel',
                additionalActions: [
                    <DialogTrigger key="duplicate">
                        <Button appearance="primary" onClick={duplicateAssistant}>
                            Duplicate
                        </Button>
                    </DialogTrigger>,
                ],
            }}
        />
    );
};
