# Maxima MCP Server (AutoCrunchCoder)

This guide explains how to run and use the Maxima MCP server in Windsurf/Cascade, including setup, configuration, testing, and troubleshooting.

- Repo servers:
  - SSE/HTTP: `examples/MCP/mcp_server_maxima.py` (SSE on port 8011)
  - STDIO: `examples/MCP/mcp_server_maxima_stdio.py` (recommended for Windsurf)
- Tools exposed:
  - `maxima_eval(code: str) -> { output: str }`
  - `maxima_diff(expr: str, vars: List[str]) -> List[str]`
  - `maxima_run_script(script: str, timeout: int=10) -> { stdout: str, stderr: str }`
  - `maxima_integrate(expr: str, var: str) -> { output: str }`
  - `maxima_simplify(expr: str, method: str = "ratsimp") -> { output: str }`

Both servers auto-kill lingering MCP server processes at startup via `examples/MCP/kill_servers.py` to avoid port/process conflicts.

## Prerequisites

- System: Maxima installed and available in PATH (`maxima -q` works)
- Python: `pip install fastmcp`
- Repo: Ensure you run the servers from this repo (imports rely on repository root added to `sys.path` internally)

## Option A: Run SSE server (manual)

1) Start the server:
```
python /home/<you>/git/AutoCrunchCoder/examples/MCP/mcp_server_maxima.py
```
- It will serve SSE at `http://0.0.0.0:8011/sse` (logs via Uvicorn)

2) Optional remote config for Windsurf (if supported): add to `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "maxima-remote": {
      "serverUrl": "http://127.0.0.1:8011/sse",
      "headers": { "Content-Type": "application/json" }
    }
  }
}
```

## Option B: Run STDIO server from Windsurf (recommended)

1) Configure Windsurf MCP at `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "maxima": {
      "command": "python3",
      "args": [
        "/home/<you>/git/AutoCrunchCoder/examples/MCP/mcp_server_maxima_stdio.py"
      ],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```
Replace `/home/<you>` with your path.

2) Reload Windsurf (Developer: Reload Window). You should see the server start in the tool logs with lines like:
```
[MaximaMCP] Starting stdio MCP server
```

## Quick validation in Windsurf

Ask Cascade to call the tools:

- maxima_eval
  - code: `factor((x^2 - 1));`
  - Expect: `(x-1)*(x+1)`

- maxima_diff
  - expr: `x^3 + x*y + sin(z)`, vars: `["x","y","z"]`
  - Expect labels: `E`, `dE_x`, `dE_y`, `dE_z`

- maxima_run_script
  - script: `display2d:false$ f:x^3 + y^2$ diff(f,x); diff(f,y);`
  - Expect stdout lines containing derivatives (we use `subprocess.run` internally)

- maxima_integrate
  - expr: `sin(x)`, var: `x`
  - Expect: `-cos(x)` (up to constant)

- maxima_simplify
  - expr: `(x^2 - 1)/(x-1)`, method: `ratsimp`
  - Expect: `x+1`

## Tool reference

- maxima_eval(code)
  - Runs code in batch mode with `display2d:false` and auto-`quit()` wrapper.
  - Accepts multi-line Maxima code (without explicit `quit()`).

- maxima_diff(expr, vars)
  - Computes first derivatives of `expr` w.r.t. each variable in `vars`.
  - Returns labeled lines: `E: ...`, `dE_x: ...`, etc.

- maxima_run_script(script, timeout)
  - Sends the script to `maxima -q` via stdin using `subprocess.run(..., input=..., timeout=...)`.
  - For batch runs, you typically don’t need `quit()`.
  - If `timeout` elapses, returns `(None, "Maxima process timed out")`.

- maxima_integrate(expr, var)
  - Computes an antiderivative: `integrate(expr, var)` in Maxima.
  - Example: `integrate(sin(x), x)` → `-cos(x)`.

- maxima_simplify(expr, method="ratsimp")
  - Applies an algebraic transformation. Supported methods: `ratsimp`, `factor`, `expand`, `trigsimp`, `trigreduce`.
  - Examples:
    - `ratsimp((x^2-1)/(x-1))` → `x+1`
    - `factor(x^2 - y^2)` → `(x-y)*(x+y)`
    - `expand((x+y)^3)` → `x^3+3*x^2*y+3*x*y^2+y^3`

## Logs and auto-kill behavior

- On startup, both servers try to kill lingering servers via `examples/MCP/kill_servers.py` using `pgrep -f` and `SIGKILL`.
- STDIO server prints debug entries to stderr, e.g. `"[MaximaMCP] maxima_eval called"`.
- SSE server logs via Uvicorn. Ctrl+C may show `asyncio.exceptions.CancelledError`—this is benign.

## Troubleshooting

- "ModuleNotFoundError: pyCruncher2":
  - We prepend the repo root to `sys.path` in server scripts. Ensure you run the file from repo or via absolute path.
- "maxima: not found": install Maxima and ensure it’s on PATH.
- No output from `maxima_run_script`: ensure you restarted the server (Windsurf must reload to pick up code changes). We use `subprocess.run` now.
- Port in use (SSE): the server auto-kills on startup; if still blocked, manually kill or change port in `mcp_server_maxima.py`.
- Windsurf can’t see the server: check `~/.codeium/windsurf/mcp_config.json` and reload window.

## Examples

- Evaluate and then substitute:
```
code = "display2d:false$ f:x^2 + y^2$ subst(y=2,f);"
```
- Derivatives for mechanics energy E:
```
expr = "(k/2)*(x^2 + y^2) + a*x*y"; vars = ["x","y"]
```
- Batch script (no quit needed):
```
script = "display2d:false$ f:sin(x)^2 + cos(x)^2$ expand(f); trigreduce(f);"
```

- Integrals and simplification:
```
# Indefinite integral
expr = "sin(x)"; var = "x"

# Simplify with different methods
expr1 = "(x^2 - 1)/(x - 1)"; method1 = "ratsimp"
expr2 = "x^2 - y^2"; method2 = "factor"
```

## Roadmap: advanced tools

Planned additions:
- `maxima_subst(expr: str, rules: dict)` – substitutions `subst`
- `maxima_solve(exprs: List[str], vars: List[str])` – solve equations/systems
- `maxima_gradient(expr: str, vars: List[str])` – vector of partial derivatives
- `maxima_hessian(expr: str, vars: List[str])` – second derivatives
- `maxima_integrate_definite(expr: str, var: str, a: str, b: str)` – definite integrals
- `maxima_matrix_eval(cmd: str)` – linear algebra snippets (optional)
