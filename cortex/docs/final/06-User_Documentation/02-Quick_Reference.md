# Cortex Platform: Quick Reference Guide

_Version: 1.0_  
_Date: 2025-03-05_

## Common Commands

### Chat Interface

| Action                 | Command/Shortcut                                   |
| ---------------------- | -------------------------------------------------- |
| Start new conversation | Click "New Chat" or Ctrl+N (Cmd+N on Mac)          |
| Send message           | Type in input box and press Enter                  |
| Multi-line message     | Press Shift+Enter for new line                     |
| Clear context          | Type `/clear` in chat                              |
| Format text            | Use Markdown: `**bold**`, `*italic*`, `` `code` `` |
| Code block             | ``python print("Hello")`                           |
| Attach file            | Drag & drop or click paperclip icon                |
| Export conversation    | Click ⋮ menu → "Export"                            |

### Voice Interface

| Action         | Command/Shortcut                                                        |
| -------------- | ----------------------------------------------------------------------- |
| Activate voice | Click microphone icon or Ctrl+Shift+V (Cmd+Shift+V on Mac)              |
| Wake word      | Say "Hey Cortex" (if enabled)                                           |
| End listening  | Click microphone icon again or say "Stop listening"                     |
| Voice commands | "Cortex, summarize this", "Cortex, remember this", "Cortex, show me..." |

### Canvas Interface

| Action           | Command/Shortcut                                          |
| ---------------- | --------------------------------------------------------- |
| Open canvas      | Click canvas icon or Ctrl+Shift+C (Cmd+Shift+C on Mac)    |
| Draw             | Click and drag with mouse/stylus                          |
| Add text         | Click "T" icon then click on canvas                       |
| Add shapes       | Select shape tool then click/drag on canvas               |
| Analyze image    | Drag image to canvas, then ask about it                   |
| Generate diagram | "Create a flowchart of..." or "Draw a diagram showing..." |

### Dashboard Interface

| Action               | Command/Shortcut                                          |
| -------------------- | --------------------------------------------------------- |
| Open dashboard       | Click dashboard icon or Ctrl+Shift+D (Cmd+Shift+D on Mac) |
| Create visualization | "Create a chart showing..."                               |
| Add panel            | Click "+ Add Panel" button                                |
| Customize panel      | Click ⋮ menu on panel → "Edit"                            |
| Save dashboard       | Click "Save" button                                       |
| Export data          | Click ⋮ menu on panel → "Export"                          |

## Task-Based Reference

### Research Tasks

| Task              | Example Command                                |
| ----------------- | ---------------------------------------------- |
| Basic question    | "What is quantum computing?"                   |
| With sources      | "Explain neural networks with sources"         |
| Compare topics    | "Compare REST and GraphQL APIs"                |
| Follow-up         | "Tell me more about the security implications" |
| Timeline          | "Create a timeline of AI development"          |
| Summarize article | "Summarize this article: [paste URL or text]"  |

### Coding Tasks

| Task          | Example Command                                                               |
| ------------- | ----------------------------------------------------------------------------- |
| Generate code | "Write a Python function that sorts a list of dictionaries by the 'date' key" |
| Explain code  | "Explain what this code does: [paste code]"                                   |
| Debug code    | "Debug this code: [paste code and error message]"                             |
| Optimize code | "Optimize this function for performance: [paste code]"                        |
| Create test   | "Write unit tests for this function: [paste code]"                            |
| Document code | "Generate documentation for this class: [paste code]"                         |

### Content Creation

| Task              | Example Command                                                     |
| ----------------- | ------------------------------------------------------------------- |
| Draft email       | "Draft an email to my team about the project deadline change"       |
| Create outline    | "Create an outline for a blog post about AI ethics"                 |
| Improve text      | "Improve this paragraph: [paste text]"                              |
| Proofread         | "Proofread this document: [paste text]"                             |
| Generate slides   | "Create a 5-slide presentation outline on our new product features" |
| Write social post | "Write a LinkedIn post announcing our new service"                  |

### Task Management

| Task              | Example Command                                          |
| ----------------- | -------------------------------------------------------- |
| Set reminder      | "Remind me about the client meeting tomorrow at 2pm"     |
| Create to-do list | "Create a to-do list for my website redesign project"    |
| Add to list       | "Add 'review analytics report' to my work tasks list"    |
| Check lists       | "Show me my to-do lists"                                 |
| Project plan      | "Create a project plan for launching our new product"    |
| Track progress    | "Update my project progress: completed the design phase" |

## Environment-Specific Features

### Browser Extension

| Feature        | Description                                          |
| -------------- | ---------------------------------------------------- |
| Page summary   | Click extension icon → "Summarize page"              |
| Research info  | Select text → right-click → "Research with Cortex"   |
| Extract data   | On page with table → extension icon → "Extract data" |
| Translate      | Select text → right-click → "Translate with Cortex"  |
| Save to memory | Select text → right-click → "Save to Cortex memory"  |

### VS Code Extension

| Feature          | Description                                               |
| ---------------- | --------------------------------------------------------- |
| Inline code help | Highlight code → right-click → "Explain with Cortex"      |
| Generate code    | Open Command Palette → "Cortex: Generate Code"            |
| Code review      | Open Command Palette → "Cortex: Review Current File"      |
| Documentation    | Highlight function → right-click → "Document with Cortex" |
| Debug help       | Highlight error → right-click → "Debug with Cortex"       |

### M365 Integration

| Application | Key Features                                                                                                                                                                 |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Word        | Rewrite selection (select text → Cortex tab → "Rewrite")<br>Generate content (Cortex tab → "Generate")<br>Summarize document (Cortex tab → "Summarize")                      |
| Excel       | Formula help (select cells → Cortex tab → "Create Formula")<br>Data analysis (select data → Cortex tab → "Analyze")<br>Create chart (select data → Cortex tab → "Visualize") |
| PowerPoint  | Generate slides (Cortex tab → "Generate Slides")<br>Improve content (select text → Cortex tab → "Improve")<br>Create visuals (Cortex tab → "Create Visual")                  |

## Prompt Engineering Tips

### Effective Prompting Patterns

| Goal                   | Pattern to Use                                                 |
| ---------------------- | -------------------------------------------------------------- |
| Specific format        | "Generate [content] in the format of [example]"                |
| Step-by-step           | "Explain [topic] step-by-step"                                 |
| Comparative            | "Compare [A] and [B] in terms of [criteria]"                   |
| Creative ideas         | "Generate 5 creative ideas for [topic]"                        |
| Detailed response      | "Provide a detailed explanation of [topic] covering [aspects]" |
| Simplified explanation | "Explain [complex topic] in simple terms"                      |

### Refining Results

| Goal               | Pattern to Use                                          |
| ------------------ | ------------------------------------------------------- |
| More detail        | "Expand on [specific point]"                            |
| Simplify           | "Simplify your last explanation"                        |
| Different approach | "Approach this from a different perspective"            |
| Specific format    | "Format this as a [table/list/diagram]"                 |
| Change tone        | "Rewrite this in a more [formal/casual/technical] tone" |
| Concrete examples  | "Provide specific examples of [concept]"                |

## System Status Indicators

| Icon | Meaning                                |
| ---- | -------------------------------------- |
| 🟢   | System fully operational               |
| 🟡   | System operational with minor issues   |
| 🟠   | System partially degraded              |
| 🔴   | System experiencing significant issues |
| ⚪   | Offline mode active                    |
| 🔵   | Processing request                     |
| ✓    | Request completed successfully         |

## Keyboard Shortcuts Reference

### Global Shortcuts

| Action           | Windows/Linux | Mac         |
| ---------------- | ------------- | ----------- |
| New conversation | Ctrl+N        | Cmd+N       |
| Focus search     | Ctrl+F        | Cmd+F       |
| Toggle sidebar   | Ctrl+B        | Cmd+B       |
| Settings         | Ctrl+,        | Cmd+,       |
| Help             | F1            | F1          |
| Switch theme     | Ctrl+Shift+T  | Cmd+Shift+T |
| Switch device    | Ctrl+Shift+D  | Cmd+Shift+D |

### Chat Shortcuts

| Action              | Windows/Linux | Mac         |
| ------------------- | ------------- | ----------- |
| Send message        | Enter         | Enter       |
| New line            | Shift+Enter   | Shift+Enter |
| Previous message    | Up arrow      | Up arrow    |
| Next message        | Down arrow    | Down arrow  |
| Cancel generation   | Esc           | Esc         |
| Select conversation | Alt+1-9       | Option+1-9  |

### Input Modality Shortcuts

| Action          | Windows/Linux | Mac         |
| --------------- | ------------- | ----------- |
| Toggle voice    | Ctrl+Shift+V  | Cmd+Shift+V |
| Open canvas     | Ctrl+Shift+C  | Cmd+Shift+C |
| Open dashboard  | Ctrl+Shift+D  | Cmd+Shift+D |
| Attach file     | Ctrl+Shift+A  | Cmd+Shift+A |
| Take screenshot | Ctrl+Shift+S  | Cmd+Shift+S |

## Quick Troubleshooting

| Issue                 | Solution                                                                                                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cortex not responding | Refresh the page/restart the application                                                                                                                                                                             |
| Slow responses        | Check internet connection<br>Close unused applications/tabs<br>Clear cache in Settings > Advanced                                                                                                                    |
| Can't log in          | Reset password at [account.cortex-platform.example.com](https://account.cortex-platform.example.com)<br>Check if service is down at [status.cortex-platform.example.com](https://status.cortex-platform.example.com) |
| Missing conversation  | Check if you're signed into the correct account<br>Look in trash folder<br>Check conversation filters                                                                                                                |
| Feature not working   | Update to the latest version<br>Check if feature requires specific subscription<br>Check permissions in Settings > Features                                                                                          |

## Additional Resources

- **Full User Guide**: [docs.cortex-platform.example.com/user-guide](https://docs.cortex-platform.example.com/user-guide)
- **Video Tutorials**: [learn.cortex-platform.example.com/videos](https://learn.cortex-platform.example.com/videos)
- **Community Forums**: [community.cortex-platform.example.com](https://community.cortex-platform.example.com)
- **Support**: support@cortex-platform.example.com or in-app chat (Help > Contact Support)
