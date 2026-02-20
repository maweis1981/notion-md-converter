#!/usr/bin/env python3
"""
notion-sync: Sync Markdown content to Notion

Usage:
    notion-sync create --file <file> --title <title> [--emoji <emoji>] [--parent-id <id>]
    notion-sync append --file <file> --page-id <id>
    notion-sync list --parent-id <id>
    
Options:
    -f, --file       Input Markdown file (default: stdin)
    -t, --title      Page title (required for create)
    -p, --page-id    Target page ID
    --parent-id       Parent page ID for nesting
    -e, --emoji      Page emoji icon (default: 📄)
    -h, --help       Show this help
"""

import os
import sys
import json
import requests
import argparse
from pathlib import Path

VERSION = "1.0.0"

class NotionSync:
    """Sync Markdown to Notion"""
    
    BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2025-09-03"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not set. Run: export NOTION_API_KEY='your_key'")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
    
    def _load_api_key(self):
        """Load API key from environment or file"""
        return os.environ.get("NOTION_API_KEY") or \
               Path("~/.config/notion/api_key").expanduser().read_text().strip() if Path("~/.config/notion/api_key").expanduser().exists() else None
    
    def markdown_to_blocks(self, content):
        """Convert Markdown to Notion blocks"""
        blocks = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Heading 1
            if line.startswith('# '):
                blocks.append(self._heading_block(line[2:], 'heading_1'))
                i += 1
                continue
            
            # Heading 2
            if line.startswith('## '):
                blocks.append(self._heading_block(line[3:], 'heading_2'))
                i += 1
                continue
            
            # Heading 3
            if line.startswith('### '):
                blocks.append(self._heading_block(line[4:], 'heading_3'))
                i += 1
                continue
            
            # Horizontal rule
            if line.strip() in ['---', '***', '___']:
                blocks.append({"object": "block", "type": "divider", "divider": {}})
                i += 1
                continue
            
            # Blockquote
            if line.startswith('> '):
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
                })
                i += 1
                continue
            
            # Code block
            if line.startswith('```'):
                lang = line[3:].strip() if len(line) > 3 else ''
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": lang if lang else "plain text",
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}]
                    }
                })
                i += 1
                continue
            
            # Bulleted list item
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                text = line.strip()[2:]
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [self._parse_rich_text(text)]}
                })
                i += 1
                continue
            
            # Numbered list item
            import re
            if re.match(r'^\d+\. ', line):
                text = re.sub(r'^\d+\. ', '', line)
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": [self._parse_rich_text(text)]}
                })
                i += 1
                continue
            
            # Table row - convert to paragraph
            if '|' in line and not line.strip().startswith('|'):
                # Table content - convert to readable format
                cells = [c.strip() for c in line.split('|')[1:-1]]
                text = ' | '.join(cells)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [self._parse_rich_text(text)]}
                })
                i += 1
                continue
            
            # Regular paragraph
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [self._parse_rich_text(line)]}
            })
            i += 1
        
        return blocks[:100]  # Notion limit
    
    def _heading_block(self, text, heading_type):
        """Create heading block"""
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {"rich_text": [self._parse_rich_text(text)]}
        }
    
    def _parse_rich_text(self, text):
        """Parse text with bold, italic, links"""
        result = []
        i = 0
        current = ""
        
        while i < len(text):
            # Handle bold
            if text[i:i+2] == '**':
                if current:
                    result.append({"type": "text", "text": {"content": current}})
                    current = ""
                j = text.find('**', i+2)
                if j == -1:
                    j = len(text)
                result.append({
                    "type": "text",
                    "text": {"content": text[i+2:j]},
                    "annotations": {"bold": True}
                })
                i = j + 2
                continue
            
            # Handle italic
            if text[i] == '*' and (i == 0 or text[i-1] != '*'):
                if current:
                    result.append({"type": "text", "text": {"content": current}})
                    current = ""
                j = text.find('*', i+1)
                if j == -1:
                    j = len(text)
                result.append({
                    "type": "text",
                    "text": {"content": text[i+1:j]},
                    "annotations": {"italic": True}
                })
                i = j + 1
                continue
            
            # Handle link
            if text[i:i+1] == '[':
                if current:
                    result.append({"type": "text", "text": {"content": current}})
                    current = ""
                j = text.find(']', i)
                if j != -1 and text[j+1:j+2] == '(':
                    link_text = text[i+1:j]
                    k = text.find(')', j+1)
                    if k != -1:
                        url = text[j+2:k]
                        result.append({
                            "type": "text",
                            "text": {"content": link_text, "link": {"url": url}}
                        })
                        i = k + 1
                        continue
            
            current += text[i]
            i += 1
        
        if current:
            result.append({"type": "text", "text": {"content": current}})
        
        return result[0] if result else {"type": "text", "text": {"content": ""}}
    
    def create_page(self, title, content, emoji="📄", parent_id=None):
        """Create a new page with content"""
        blocks = self.markdown_to_blocks(content)
        
        payload = {
            "parent": {"page_id": parent_id} if parent_id else {"page_id": self._get_user_page_id()},
            "icon": {"emoji": emoji},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
            "children": blocks
        }
        
        resp = requests.post(f"{self.BASE_URL}/pages", headers=self.headers, json=payload)
        return self._handle_response(resp)
    
    def append_to_page(self, page_id, content):
        """Add content to existing page"""
        blocks = self.markdown_to_blocks(content)
        
        payload = {"children": blocks}
        resp = requests.patch(
            f"{self.BASE_URL}/blocks/{page_id}/children",
            headers=self.headers,
            json=payload
        )
        return self._handle_response(resp)
    
    def _get_user_page_id(self):
        """Get user's private pages (creates root page)"""
        resp = requests.post(
            f"{self.BASE_URL}/search",
            headers=self.headers,
            json={"filter": {"property": "object", "value": "page"}, "page_size": 1}
        )
        data = self._handle_response(resp)
        if data.get("results"):
            return data["results"][0]["id"]
        # Create root page if none exists
        resp = requests.post(
            f"{self.BASE_URL}/pages",
            headers=self.headers,
            json={
                "parent": {"page_id": "root"},
                "properties": {"title": {"title": [{"text": {"content": "OpenClaw Notes"}}]}
            }
        )
        return self._handle_response(resp)["id"]
    
    def _handle_response(self, resp):
        """Handle API response"""
        if resp.status_code not in [200, 201]:
            raise Exception(f"API Error {resp.status_code}: {resp.text[:200]}")
        return resp.json()
    
    def list_pages(self, parent_id=None):
        """List pages"""
        payload = {
            "filter": {"property": "object", "value": "page"},
            "page_size": 50
        }
        if parent_id:
            payload["parent"] = {"page_id": parent_id}
        
        resp = requests.post(
            f"{self.BASE_URL}/search",
            headers=self.headers,
            json=payload
        )
        return self._handle_response(resp)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Markdown to Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--file', '-f', help='Input Markdown file (default: stdin)')
    parser.add_argument('--title', '-t', help='Page title')
    parser.add_argument('--page-id', '-p', help='Target page ID')
    parser.add_argument('--parent-id', help='Parent page ID')
    parser.add_argument('--emoji', '-e', default='📄', help='Page emoji')
    parser.add_argument('--list', action='store_true', help='List pages')
    
    args = parser.parse_args()
    
    # Get content
    if args.file:
        content = Path(args.file).read_text()
    else:
        content = sys.stdin.read()
    
    if not content.strip():
        print("Error: No content provided")
        sys.exit(1)
    
    # Initialize
    sync = NotionSync()
    
    # List pages
    if args.list:
        result = sync.list_pages(args.parent_id)
        for page in result.get("results", []):
            props = page.get("properties", {})
            title = props.get("title", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
            page_id = page["id"]
            print(f"📄 {title}")
            print(f"   ID: {page_id}")
            print()
        return
    
    # Create page
    if args.title:
        if not args.page_id:
            result = sync.create_page(args.title, content, args.emoji, args.parent_id)
            page_id = result["id"]
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"✅ Created: {args.title}")
            print(f"🔗 {page_url}")
        else:
            result = sync.append_to_page(args.page_id, content)
            print(f"✅ Appended to page: {args.page_id}")
        return
    
    # Append to page
    if args.page_id:
        result = sync.append_to_page(args.page_id, content)
        print(f"✅ Appended to: {args.page_id}")
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()
