# Skill Seekers Source Note

## Purpose

This file is the built-in backup note for the upstream Skill Seekers documentation used by `skill-seekers-windows`.

- Source note path:
  `D:\Program Files (x86)\obsidian\obsidian_vault\obsidian_vault\main\03_Resources-资源\Tutorials-教程\260413_yusufkaraaslan_Skill_Seekers.md`
- Upstream project:
  `https://github.com/yusufkaraaslan/Skill_Seekers`
- Priority:
  this note is a local backup for general capability lookup; Windows execution details still defer to `windows-verified-workflows.md`

## Core Idea

Skill Seekers is a preprocessing layer for AI systems. It converts docs sites, GitHub repositories, PDFs, videos, notebooks, local projects, and other sources into structured knowledge assets that can later be:

- used as AI skills
- exported to RAG pipelines
- packaged for platform-specific targets
- converted into IDE assistant context

The core mental model is:

1. create or scrape structured source data
2. optionally enhance the generated skill with AI
3. package or export for a target platform

## Common Commands

### Create

```powershell
skill-seekers create "https://docs.react.dev/"
skill-seekers create "facebook/react"
skill-seekers create "C:\path\to\local-project"
skill-seekers create "C:\path\to\manual.pdf"
skill-seekers create "C:\path\to\report.docx"
skill-seekers create "C:\path\to\notebook.ipynb"
skill-seekers create "C:\path\to\presentation.pptx"
```

### Video

```powershell
skill-seekers video --url "https://www.youtube.com/watch?v=..." --name "my-video-skill"
skill-seekers video --setup
```

### Enhance

```powershell
skill-seekers enhance ".\output\react"
```

Local agent examples from the upstream note:

```powershell
skill-seekers create "https://docs.django.com/" --agent kimi
skill-seekers create "https://docs.django.com/" --agent-cmd "my-custom-agent run"
```

### Package

```powershell
skill-seekers package ".\output\react" --target claude
skill-seekers package ".\output\react" --target gemini
skill-seekers package ".\output\react" --target openai
skill-seekers package ".\output\react" --target langchain
skill-seekers package ".\output\react" --target llama-index
skill-seekers package ".\output\react" --target markdown
```

## Supported Source Types

The source note indicates support for at least the following common inputs:

- docs websites
- GitHub repositories
- local projects
- PDF
- DOCX
- EPUB
- Jupyter notebooks
- OpenAPI files
- PowerPoint files
- AsciiDoc files
- local HTML
- RSS or Atom feeds
- man pages
- videos

## Typical Output Layout

The generated structure normally looks like this:

```text
output/
└── skill-name/
    ├── SKILL.md
    ├── references/
    ├── scripts/
    └── assets/
```

Raw source data may also appear in a sibling `*_data` directory.

## Enhancement and Target Notes

- Claude is the default local agent in the source note.
- API-based enhancement is available when the corresponding API keys are present.
- Packaging targets include Claude, Gemini, OpenAI, LangChain, LlamaIndex, Haystack, and generic Markdown outputs.
- Some IDE assistant workflows reuse Claude packaging outputs as portable context bundles.

## Windows-Specific Caveat

The upstream note contains shell-oriented examples. When operating on Windows:

- translate commands to PowerShell
- quote paths with spaces or non-ASCII characters
- prefer pinned working directories over relying on `--output`
- consult `windows-verified-workflows.md` before choosing a local enhancement route

## MCP Note

The source note also lists MCP server entry points. On Windows, shell scripts such as `setup_mcp.sh` should not be treated as directly runnable PowerShell commands. Prefer explicit Python module entry points instead.

## Use in This Skill

Read this file when you need:

- a quick backup of common Skill Seekers capabilities
- examples of supported source types
- packaging target reminders
- a fallback explanation of the upstream project without reopening the original Obsidian note
