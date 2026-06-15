---
name: workflow-agent-url-formatting
description: Updated workflow_agent.py to display URLs plainly under each title in generated Markdown reports
metadata:
  type: reference
---

Modified workflow_agent.py _generate_report method to format each research result as:
### [Title]
*URL:* [Raw URL]
*Summary:* [Snippet/Content]
instead of hiding URLs in Markdown links.
Also updated STATUS.md to document this change under workflow_agent.py section.