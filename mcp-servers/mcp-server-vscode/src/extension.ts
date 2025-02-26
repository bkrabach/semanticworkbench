import { FastMCP } from 'fastmcp';
import * as vscode from 'vscode';
import { z } from 'zod';
import packageJson from '../package.json';
import { codeCheckerTool } from './tools/code_checker';
import { focusEditorTool } from './tools/focus_editor';
import { resolvePort } from './utils/port';

const extensionName = 'vscode-mcp-server';
const extensionDisplayName = 'VSCode MCP Server';

export const activate = async (context: vscode.ExtensionContext) => {
    // Create the output channel for logging
    const outputChannel = vscode.window.createOutputChannel(extensionDisplayName);

    // Write an initial message to ensure the channel appears in the Output dropdown
    outputChannel.appendLine(`Activating ${extensionDisplayName}...`);
    // Uncomment to automatically switch to the output tab and this extension channel on activation
    // outputChannel.show();

    // Initialize the MCP server instance using FastMCP
    const server = new FastMCP({
        name: extensionName,
        version: packageJson.version,
    });

    // Register the "code_checker" tool
    server.addTool({
        name: 'code_checker',
        description: dedent`
            Retrieve diagnostics from VSCode's language services for the active workspace.
            Use this tool after making changes to any code in the filesystem to ensure no new
            errors were introduced, or when requested by the user.
        `.trim(),
        parameters: z.object({
            severityLevel: z
                .enum(['Error', 'Warning', 'Information', 'Hint'])
                .default('Warning')
                .describe("Minimum severity level for checking issues: 'Error', 'Warning', 'Information', or 'Hint'."),
        }),
        execute: async ({ severityLevel }: { severityLevel?: 'Error' | 'Warning' | 'Information' | 'Hint' }) => {
            const result = await codeCheckerTool(severityLevel);
            return {
                content: result.content.map((c) => ({
                    ...c,
                    text: typeof c.text === 'string' ? c.text : String(c.text),
                    type: 'text',
                })),
            };
        },
    });

    // Register "focus_editor" tool
    server.addTool({
        name: 'focus_editor',
        description: dedent`
            Open the specified file in the VSCode editor and navigate to a specific line and column.
            Use this tool to bring a file into focus and position the editor's cursor where desired.
            Note: This tool operates on the editor visual environment so that the user can see the file. It does not return the file contents in the tool call result.
        `.trim(),
        parameters: z.object({
            filePath: z.string().describe('The absolute path to the file to focus in the editor.'),
            line: z.number().int().min(0).default(0).describe('The line number to navigate to (default: 0).'),
            column: z.number().int().min(0).default(0).describe('The column position to navigate to (default: 0).'),
            startLine: z.number().int().min(0).optional().describe('The starting line number for highlighting.'),
            startColumn: z.number().int().min(0).optional().describe('The starting column number for highlighting.'),
            endLine: z.number().int().min(0).optional().describe('The ending line number for highlighting.'),
            endColumn: z.number().int().min(0).optional().describe('The ending column number for highlighting.'),
        }),
        execute: async (params: { filePath: string; line?: number; column?: number }) => {
            const result = await focusEditorTool(params);
            return result;
        },
    });

    // FIXME: This doesn't return results yet
    // // Register 'search_symbol' tool
    // server.addTool({
    //     name: 'search_symbol',
    //     description: dedent`
    //         Search for a symbol within the workspace.
    //         - Tries to resolve the definition via VSCode’s "Go to Definition".
    //         - If not found, searches the entire workspace for the text, similar to Ctrl+Shift+F.
    //     `.trim(),
    //     parameters: z.object({
    //         query: z.string().describe('The symbol or text to search for.'),
    //         useDefinition: z.boolean().default(true).describe("Whether to use 'Go to Definition' as the first method."),
    //         maxResults: z.number().default(50).describe('Maximum number of global search results to return.'),
    //         openFile: z.boolean().default(false).describe('Whether to open the found file in the editor.'),
    //     }),
    //     execute: async (params: { query: string; useDefinition?: boolean; maxResults?: number; openFile?: boolean }) => {
    //         const result = await searchSymbolTool(params);
    //         return {
    //             ...result,
    //             content: [
    //                 {
    //                     text: JSON.stringify(result),
    //                     type: 'text',
    //                 },
    //             ],
    //         };
    //     }
    // });

    // Register 'list_debug_sessions' tool
    server.addTool({
        name: 'list_debug_sessions',
        description: 'List all active debug sessions in the workspace.',
        parameters: listDebugSessionsSchema.shape,
        execute: async () => {
            const result = await listDebugSessions();
            return {
                ...result,
                content: result.content.map((item) => ({ type: 'text', text: JSON.stringify(item.json) })),
            };
        },
    });

    // Register 'start_debug_session' tool
    server.addTool({
        name: 'start_debug_session',
        description: 'Start a new debug session with the provided configuration.',
        parameters: startDebugSessionSchema.shape,
        execute: async (params) => {
            const result = await startDebugSession(params);
            return {
                ...result,
                content: result.content.map((item) => ({
                    ...item,
                    type: 'text' as const,
                })),
            };
        },
    });

    // Register 'restart_debug_session' tool
    server.addTool({
        name: 'restart_debug_session',
        description: 'Restart a debug session by stopping it and then starting it with the provided configuration.',
        parameters: startDebugSessionSchema.start,
        execute: async (params) => {
            // Stop current session using the provided session name
            await stopDebugSession({ sessionName: params.configuration.name });

            // Then start a new debug session with the given configuration
            const result = await startDebugSession(params);
            return {
                ...result,
                content: result.content.map((item) => ({
                    ...item,
                    type: 'text' as const,
                })),
            };
        },
    });

    // Register 'stop_debug_session' tool
    server.addTool({
        name: 'stop_debug_session',
        description: 'Stop all debug sessions that match the provided session name.',
        parameters: stopDebugSessionSchema.shape,
        execute: async (params) => {
            const result = await stopDebugSession(params);
            return {
                ...result,
                content: result.content.map((item) => ({
                    ...item,
                    type: 'text' as const,
                })),
            };
        },
    });

    // Retrieve port from configuration
    const mcpConfig = vscode.workspace.getConfiguration('mcpServer');
    const port = await resolvePort(mcpConfig.get<number>('port', 6010));

    // Start the server with SSE support
    server.start({
        transportType: 'sse',
        sse: {
            endpoint: '/sse',
            port,
        },
    });

    outputChannel.appendLine(`${extensionDisplayName} activated on port ${port}.`);

    context.subscriptions.push({
        dispose: () => {
            server.stop();
            outputChannel.dispose();
        },
    });

    // COMMAND PALETTE COMMAND: Stop the MCP Server
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpServer.stopServer', () => {
            server.stop();
            outputChannel.appendLine('MCP Server stopped.');
            vscode.window.showInformationMessage('MCP Server stopped.');
        }),
    );

    // COMMAND PALETTE COMMAND: Start the MCP Server
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpServer.startServer', async () => {
            const newPort = await resolvePort(mcpConfig.get<number>('port', 6010));
            server.start({
                transportType: 'sse',
                sse: {
                    endpoint: '/sse',
                    port: newPort,
                },
            });
            outputChannel.appendLine(`MCP Server started on port ${newPort}.`);
            vscode.window.showInformationMessage(`MCP Server started on port ${newPort}.`);
        }),
    );

    // COMMAND PALETTE COMMAND: Set the MCP server port and restart the server
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpServer.setPort', async () => {
            const newPortInput = await vscode.window.showInputBox({
                prompt: 'Enter new port number for the MCP Server:',
                value: String(port),
                validateInput: (input) => {
                    const num = Number(input);
                    if (isNaN(num) || num < 1 || num > 65535) {
                        return 'Please enter a valid port number (1-65535).';
                    }
                    return null;
                },
            });
            if (newPortInput && newPortInput.trim().length > 0) {
                const newPort = Number(newPortInput);
                await vscode.workspace
                    .getConfiguration('mcpServer')
                    .update('port', newPort, vscode.ConfigurationTarget.Global);
                server.stop();
                server.start({
                    transportType: 'sse',
                    sse: {
                        endpoint: '/sse',
                        port: newPort,
                    },
                });
                outputChannel.appendLine(`MCP Server restarted on port ${newPort}`);
                vscode.window.showInformationMessage(`MCP Server restarted on port ${newPort}`);
            }
        }),
    );

    // COMMAND PALETTE COMMAND: Get the MCP Server status
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpServer.getStatus', async () => {
            const status = server.listening
                ? `MCP Server is running on port ${(server.address() as any).port}. Active sessions: ${Array.from(
                      activeSessions,
                  ).join(', ')}`
                : 'MCP Server is not running.';
            vscode.window.showInformationMessage(status);
            outputChannel.appendLine(status);
        }),
    );

    // COMMAND PALETTE COMMAND: Get the current MCP Server port
    context.subscriptions.push(
        vscode.commands.registerCommand('mcpServer.getCurrentPort', async () => {
            if (!server.listening) {
                vscode.window.showWarningMessage('MCP Server is not running.');
                outputChannel.appendLine('MCP Server is not running. Cannot retrieve port.');
                return;
            }
            const address = server.address() as { port: number };
            if (address?.port) {
                const message = `MCP Server is running on port ${address.port}.`;
                vscode.window.showInformationMessage(message);
                outputChannel.appendLine(message);
            } else {
                vscode.window.showWarningMessage('Failed to retrieve MCP Server port.');
                outputChannel.appendLine('Failed to retrieve MCP Server port.');
            }
        }),
    );
};

export function deactivate() {
    // Clean-up is managed by the disposables added in the activate method.
}
