from fastmcp import Context, FastMCP
import os, sys
from typing import List

# DEBUG: ensure repository root is on sys.path so 'pyCruncher2' can be imported when run from any CWD
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
# DEBUG: also ensure this script directory is importable (for kill_servers.py)
sys.path.append(os.path.dirname(__file__))
from pyCruncher2.scientific.cas.maxima import run_maxima, get_derivs, run_maxima_script

# Create a named MCP server
mcp = FastMCP("MaximaMCP-STDIO")

@mcp.resource("maxima://help")
def maxima_help() -> str:
    return (
        "Maxima MCP (stdio). Tools: maxima_eval, maxima_diff, maxima_run_script, maxima_integrate, maxima_simplify. "
        "See: doc/MCP_Maxima.md (Windsurf config: ~/.codeium/windsurf/mcp_config.json)."
    )

@mcp.tool()
def maxima_eval(code: str) -> dict:
    print("[MaximaMCP] maxima_eval called", file=sys.stderr)
    out = run_maxima(code)
    if out is None:
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

@mcp.tool()
def maxima_diff(expr: str, vars: List[str]) -> List[str]:
    print(f"[MaximaMCP] maxima_diff called expr={expr} vars={vars}", file=sys.stderr)
    return get_derivs(expr, vars)

@mcp.tool()
def maxima_run_script(script: str, timeout: int = 10) -> dict:
    print(f"[MaximaMCP] maxima_run_script called len={len(script)} timeout={timeout}", file=sys.stderr)
    stdout, stderr = run_maxima_script(script, timeout=timeout)
    return {"stdout": stdout, "stderr": stderr}

@mcp.tool()
def maxima_integrate(expr: str, var: str) -> dict:
    print(f"[MaximaMCP] maxima_integrate called expr={expr} var={var}", file=sys.stderr)
    code = f"display2d:false$ integrate({expr}, {var});"
    out = run_maxima(code)
    if out is None:
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

@mcp.tool()
def maxima_simplify(expr: str, method: str = "ratsimp") -> dict:
    print(f"[MaximaMCP] maxima_simplify called expr={expr} method={method}", file=sys.stderr)
    m = (method or "").lower()
    fn = {"ratsimp": "ratsimp", "factor": "factor", "expand": "expand", "trigsimp": "trigsimp", "trigreduce": "trigreduce"}.get(m, "ratsimp")
    code = f"display2d:false$ {fn}({expr});"
    out = run_maxima(code)
    if out is None:
        raise RuntimeError("Maxima returned an error; see server stderr logs")
    return {"output": out}

if __name__ == "__main__":
    # Attempt to kill any lingering MCP servers to avoid duplicates/port conflicts (# DEBUG)
    try:
        from kill_servers import kill_mcp_servers
        kill_mcp_servers()
    except Exception as e:
        print(f"[MaximaMCP] WARN: kill_mcp_servers failed: {e}", file=sys.stderr)
    print("[MaximaMCP] Starting stdio MCP server", file=sys.stderr)
    mcp.run(transport="stdio")
