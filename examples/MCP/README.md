# examples/MCP

Model Context Protocol (MCP) server and client examples. These demonstrate how an LLM agent can call external tools — chemistry simulations, LAMMPS molecular dynamics, and Maxima symbolic math — through the MCP standard.

## Files

- `mcp_server_chem.py` — MCP server exposing chemistry-related tools (molecular properties, force calculations).
- `mcp_server_lammps_http.py` / `mcp_server_lammps_http_old.py` / `mcp_server_lammps_stdio.py` — MCP servers wrapping LAMMPS molecular dynamics simulator (HTTP and stdio transports).
- `mcp_server_maxima.py` / `mcp_server_maxima_stdio.py` — MCP servers exposing Maxima CAS commands (symbolic differentiation, integration).
- `mcp_client_chem.py` — Client demonstrating how an LLM consumes the chemistry MCP server.
- `mcp_client_lammps_http.py` / `mcp_client_lammps_stdio.py` — Clients for the LAMMPS MCP servers.
- `kill_servers.py` — Utility to clean up running MCP server processes.
