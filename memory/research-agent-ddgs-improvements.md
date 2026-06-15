---
name: research-agent-ddgs-improvements
description: Improved DDGS search logic in research_agent.py to prevent missing URLs and snippets
metadata:
  type: reference
---

Updated research_agent.py to:
1. Use DDGS().text(query, max_results=max_results, backend="lite") explicitly (already present)
2. Replace URL extraction with: url = r.get('href') or r.get('link') or r.get('url') or '#'
3. Replace snippet extraction with: snippet = r.get('body') or r.get('snippet') or r.get('text') or 'No snippet available'
Applied to both execute_task and handle_query methods.
This ensures robust parsing of DDGS results and eliminates "No snippet" and missing URLs.