from mcp.server.fastmcp import FastMCP
import sqlite3
import argparse
import sys
import os

# Initialize the MCP Server
mcp = FastMCP("ResearchDB")

# We need a way to pass the db path to the server. FastMCP runs as a standalone script usually.
# We'll use an environment variable or default.
DB_PATH = os.environ.get("RESEARCH_DB_PATH", "papers.db")

def get_db():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def search_by_math_solver(solver_name: str) -> str:
    """Finds computational papers that use a specific mathematical solver or algorithm."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.title, p.essence, p.summary_path
        FROM papers p
        JOIN article_tags act ON p.stem = act.article_id
        JOIN tags t ON act.tag_id = t.id
        WHERE t.name LIKE ? AND t.category = 'solver'
        LIMIT 10
    ''', (f"%{solver_name}%",))
    
    results = cursor.fetchall()
    if not results:
        return f"No papers found using solver matching '{solver_name}'."
        
    response = f"Found the following papers for solver '{solver_name}':\n\n"
    for r in results:
        response += f"- {r['title']}: {r['essence']}\n  (Summary: {r['summary_path']})\n\n"
    
    return response

@mcp.tool()
def search_by_topic(topic_name: str) -> str:
    """Finds computational papers related to a specific scientific domain or topic."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.title, p.essence, p.summary_path
        FROM papers p
        JOIN article_tags act ON p.stem = act.article_id
        JOIN tags t ON act.tag_id = t.id
        WHERE t.name LIKE ? AND t.category = 'domain'
        LIMIT 10
    ''', (f"%{topic_name}%",))
    
    results = cursor.fetchall()
    if not results:
        return f"No papers found for topic matching '{topic_name}'."
        
    response = f"Found the following papers for topic '{topic_name}':\n\n"
    for r in results:
        response += f"- {r['title']}: {r['essence']}\n  (Summary: {r['summary_path']})\n\n"
    
    return response

@mcp.tool()
def get_equations(summary_path: str) -> str:
    """Reads the Markdown summary file and extracts ONLY the Key Equations section."""
    try:
        if not os.path.exists(summary_path):
            return f"Summary file not found: {summary_path}"
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            start = content.find("## Key Equations")
            if start == -1:
                return "Could not isolate equations section."
            end = content.find("## Algorithms", start)
            if end == -1:
                end = content.find("## Methods & Abbreviations", start)
            if end == -1:
                end = len(content)
            return content[start:end].strip()
    except Exception as e:
        return f"Error reading file: {e}"

@mcp.tool()
def get_algorithms(summary_path: str) -> str:
    """Reads the Markdown summary file and extracts ONLY the Algorithms section."""
    try:
        if not os.path.exists(summary_path):
            return f"Summary file not found: {summary_path}"
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            start = content.find("## Algorithms")
            if start == -1:
                return "Could not isolate algorithms section."
            end = content.find("## Methods & Abbreviations", start)
            if end == -1:
                end = len(content)
            return content[start:end].strip()
    except Exception as e:
        return f"Error reading file: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith('.db'):
        DB_PATH = sys.argv[1]
        sys.argv.pop(1)
    mcp.run()
