import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from command_classifier import suggest_corrected_command

app = Server("runbook-remediation-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="suggest_correction",
            description="Suggests a corrected command for a failed shell or SQL operation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "step_type": {"type": "string"},
                    "error_output": {"type": "string"}
                },
                "required": ["command", "step_type", "error_output"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "suggest_correction":
        import re

        command = arguments.get("command", "")
        step_type = arguments.get("step_type", "SHELL")
        error_output = arguments.get("error_output", "")
        
        # Get the raw correction text from our classifier
        correction = suggest_corrected_command(command, step_type, error_output)
        
        clean_command = _extract_clean_command(correction, step_type, command)
        
        return [TextContent(type="text", text=json.dumps({
            "corrected_command": clean_command,
            "raw_correction": correction
        }))]
    
    raise ValueError(f"Unknown tool: {name}")


def _extract_clean_command(correction: str, step_type: str, original_command: str) -> str:
    """
    Robustly extracts a valid corrected command from the Ollama/rule-based correction text.
    Handles:
      - Backtick-wrapped: `SQL: SELECT * FROM RUNBOOK;`
      - Raw SQL block without backticks: SELECT * FROM RUNBOOK;
      - Malformed/single-word outputs (e.g. "sql") — falls back to safe default
    """
    import re

    correction = correction.strip()

    # ── 1. Try backtick extraction first ────────────────────────────────────
    backtick_match = re.search(r'`([^`]+)`', correction)
    if backtick_match:
        candidate = backtick_match.group(1).strip()
        # Validate: must be more than a single word
        if len(candidate.split()) > 1:
            return candidate

    # ── 2. For DB_QUERY: scan all lines for SQL keywords ────────────────────
    if step_type == "DB_QUERY":
        sql_keywords = re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH)\b', re.IGNORECASE)
        lines = correction.split('\n')
        # Collect consecutive lines that look like SQL
        sql_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and (sql_keywords.search(stripped) or sql_lines):
                # Stop collecting at "Explanation:" line
                if stripped.lower().startswith('explanation'):
                    break
                sql_lines.append(stripped)

        if sql_lines:
            raw_sql = ' '.join(sql_lines).rstrip(';') + ';'
            # Remove any accidental "SQL:" prefix already in it
            raw_sql = re.sub(r'^SQL:\s*', '', raw_sql, flags=re.IGNORECASE).strip()
            return f"SQL: {raw_sql}"

        # DB_QUERY hard fallback — run SELECT * FROM RUNBOOK (default table)
        return "SQL: SELECT * FROM RUNBOOK;"

    # ── 3. For REST_API / SHELL: first non-empty line ────────────────────────
    lines = [l.strip() for l in correction.split('\n') if l.strip()]
    if lines:
        candidate = lines[0]
        # Skip lines that are just explanatory text
        if not candidate.lower().startswith('explanation') and len(candidate.split()) > 1:
            return candidate

    # ── 4. Absolute fallback: return original command unchanged ──────────────
    return original_command

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
