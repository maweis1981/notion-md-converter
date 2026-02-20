# notion-md-converter

Convert between Markdown and Notion-friendly content formats.
Current implementation focuses on Markdown -> Notion block conversion.

## Core Purpose

This project is a format conversion tool for Markdown and Notion content.

## Features

- Convert Markdown to Notion blocks
- Bold (`**text**`) using annotations
- Italic (`*text*`) support
- Tables converted to bullet lists
- Horizontal rules as dividers
- Code blocks with syntax highlighting
- Link detection
- Create pages or append to existing pages in Notion

## Installation

### Via ClawHub

```bash
clawhub install notion-md-converter
```

### Manual

```bash
pip install requests
```

## Usage

### Basic

```bash
# Create page from file
notion-md-converter create --file report.md --title "Weekly Report"

# Append to existing page
notion-md-converter append --file notes.md --page-id "abc123..."

# From stdin
cat file.md | notion-md-converter create --title "My Page"
```

### Options

```
--file, -f       Input Markdown file (default: stdin)
--title, -t      Page title (required for create)
--page-id, -p    Target page ID
--emoji, -e      Page emoji (default: 📄)
--list           List pages
```

Legacy command alias: `notion-sync` (kept for compatibility).

## Notion Block Mapping

| Markdown | Notion Block |
|----------|--------------|
| `# Title` | heading_1 |
| `## Title` | heading_2 |
| `**bold**` | bold annotation |
| `*italic*` | italic annotation |
| `---` | divider |
| ````python```` | code block |
| `- item` | bulleted list |
| `[link](url)` | link |

## Configuration

Set your Notion API key:

```bash
export NOTION_API_KEY="ntn_your_key_here"
```

Or create `~/.config/notion/api_key`

## Setup Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Create new integration
3. Copy API key
4. Share pages with the integration

## License

MIT
