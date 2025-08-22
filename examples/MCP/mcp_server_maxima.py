from fastmcp import Context, FastMCP
from typing import List, Tuple

import os, sys
# DEBUG: ensure repository root is on sys.path so 'pyCruncher2' can be imported when run from any CWD
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
# DEBUG: also ensure this script directory is importable (for kill_servers.py)
sys.path.append(os.path.dirname(__file__))

# Reuse existing Maxima bindings
from pyCruncher2.scientific.cas.maxima import run_maxima, get_derivs, run_maxima_script

# Create a named MCP server
mcp = FastMCP("MaximaMCP")

# Simple resource to expose Maxima tutorial content (for quick inline help)
@mcp.resource("maxima://help")
def maxima_help() -> str:
    """Return brief info and path to detailed Maxima tutorial in this repo."""
    return (
        "Maxima MCP Server. Tools: maxima_eval, maxima_diff, maxima_run_script, maxima_integrate, maxima_simplify. "
        "See: doc/MCP_Maxima.md (Windsurf config: ~/.codeium/windsurf/mcp_config.json)."
    )

# Tools
@mcp.tool()
def maxima_eval(code: str) -> dict:
    """Evaluate raw Maxima code in batch mode (display2d: false). Returns plain text output.
    The code may contain multiple lines and must not include quit()."""
    out = run_maxima(code)
    if out is None:
        # run_maxima already printed stderr; fail loudly here to surface to client
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

@mcp.tool()
def maxima_diff(expr: str, vars: List[str]) -> List[str]:
    """Compute first derivatives of expr w.r.t. variables in 'vars'.
    Returns labeled output lines like ["E: ...", "dE_x: ...", ...]."""
    return get_derivs(expr, vars)

@mcp.tool()
def maxima_run_script(script: str, timeout: int = 10) -> dict:
    """Run a full Maxima script (multiple commands). Stops if idle beyond timeout (s)."""
    stdout, stderr = run_maxima_script(script, timeout=timeout)
    return {"stdout": stdout, "stderr": stderr}

@mcp.tool()
def maxima_integrate(expr: str, var: str) -> dict:
    """Symbolic integration: integrate(expr, var). Returns plain text output."""
    code = f"display2d:false$ integrate({expr}, {var});"
    out = run_maxima(code)
    if out is None:
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

@mcp.tool()
def maxima_simplify(expr: str, method: str = "ratsimp") -> dict:
    """Algebraic simplify. method in {ratsimp,factor,expand,trigsimp,trigreduce}."""
    m = (method or "").lower()
    fn = {"ratsimp": "ratsimp", "factor": "factor", "expand": "expand", "trigsimp": "trigsimp", "trigreduce": "trigreduce"}.get(m, "ratsimp")
    code = f"display2d:false$ {fn}({expr});"
    out = run_maxima(code)
    if out is None:
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

if __name__ == "__main__":
    # SSE transport for easy local testing next to existing servers
    # Attempt to kill any lingering MCP servers to avoid port conflicts (# DEBUG)
    try:
        from kill_servers import kill_mcp_servers
        kill_mcp_servers()
    except Exception as e:
        print(f"[MaximaMCP] WARN: kill_mcp_servers failed: {e}", file=sys.stderr)
    print("Starting MaximaMCP SSE server on http://0.0.0.0:8011/sse …")
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8011,
        log_level="info"
    )
