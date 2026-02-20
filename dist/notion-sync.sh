#!/bin/bash
# notion-md-converter: Convert Markdown into Notion blocks

export NOTION_API_KEY="${NOTION_API_KEY:-$HOME/.config/notion/api_key}"
[ -f "$NOTION_API_KEY" ] && NOTION_API_KEY=$(cat "$NOTION_API_KEY")

if [ -z "$NOTION_API_KEY" ]; then
    echo "Error: NOTION_API_KEY not set"
    exit 1
fi

usage() {
    echo "Usage: $0 <command> [options]"
    echo "Commands:"
    echo "  create --title 'Page Title' < file.md"
    echo "  append --page-id <id> < file.md"
    echo "Note: primary command name is notion-md-converter (legacy alias: notion-sync)"
    exit 1
}

convert_md_to_json() {
    python3 << 'PYEOF'
import sys
import json
import re

def convert(content):
    blocks = []
    for line in content.strip().split('\n'):
        line = line.rstrip()
        if not line:
            continue
        
        if line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
            })
        elif line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
            })
        elif line.strip() == '---':
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        elif line.startswith('- ') or line.startswith('* '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })
    
    print(json.dumps(blocks[:100]))

convert(sys.stdin.read())
PYEOF
}

cmd="${1:-}"
shift

case "$cmd" in
    create)
        title=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --title|-t) title="$2"; shift 2 ;;
                --emoji|-e) emoji="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        
        if [ -z "$title" ]; then
            echo "Error: --title required"
            exit 1
        fi
        
        blocks=$(convert_md_to_json)
        
        curl -s -X POST "https://api.notion.com/v1/pages" \
            -H "Authorization: Bearer $NOTION_API_KEY" \
            -H "Notion-Version: 2025-09-03" \
            -H "Content-Type: application/json" \
            -d "{\"parent\": {\"page_id\": \"root\"}, \"icon\": {\"emoji\": \"📄\"}, \"properties\": {\"title\": {\"title\": [{\"type\": \"text\", \"text\": {\"content\": \"$title\"}}]}}, \"children\": $blocks}"
        ;;
    append)
        page_id=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --page-id|-p) page_id="$2"; shift 2 ;;
                *) shift ;;
            esac
        done
        
        if [ -z "$page_id" ]; then
            echo "Error: --page-id required"
            exit 1
        fi
        
        blocks=$(convert_md_to_json)
        
        curl -s -X PATCH "https://api.notion.com/v1/blocks/$page_id/children" \
            -H "Authorization: Bearer $NOTION_API_KEY" \
            -H "Notion-Version: 2025-09-03" \
            -H "Content-Type: application/json" \
            -d "{\"children\": $blocks}"
        ;;
    *)
        usage ;;
esac
