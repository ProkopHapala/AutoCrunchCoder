import sys
import json
import asyncio
import traceback # Import traceback for better error printing

'''
the “stdio” transport is not a network protocol. It simply wires your client and server together over a child process’s STDIN/STDOUT, which means:

You can only talk to the server if your client spawns it (so it controls the pipes).
You can’t point a separately launched process at those pipes—there’s no cross‑terminal STDIO multiplexing.
If you need two independently running programs (even on the same box) to talk MCP, you must use a network‐based transport, e.g.:

transport="sse" (HTTP + Server‑Sent Events)
transport="ws" (WebSockets)
'''

# Import the SSETransport for connecting to an HTTP (SSE) server
try:
    from fastmcp.client import Client
    from fastmcp.client.transports import PythonStdioTransport  # stdio-based transport
    import os
except ImportError:
    print("FATAL ERROR: Could not import Client or PythonStdioTransport from fastmcp.")
    print("Please ensure fastmcp is installed correctly (e.g., pip install fastmcp).")
    sys.exit(1)

async def main():
    print("Simple MCP Client (Connecting via stdio transport)")
    print("=====================================")

    print("Simple MCP Client (Connecting via stdio transport)")

    try:
        # Launch and connect to MCP server via stdio transport
        script    = os.path.join(os.path.dirname(__file__), "mcp_server_lammps_stdio.py")
        transport = PythonStdioTransport(script_path=script, cwd=os.path.dirname(script))

        # Use the Client with the SSETransport within an async context
        async with Client(transport) as client:
            print("Client connected successfully.")

            print("\nGetting Available Offerings...")
            # Retrieve resources and tools
            resources = await client.list_resources()
            tools_list = await client.list_tools()

            print("\nAvailable Resources:")
            for resource in resources:
                 print(f"- {getattr(resource, 'name', 'N/A')}: {getattr(resource, 'description', 'N/A')}")

            print("\nAvailable Tools:")
            for tool in tools_list:
                 print(f"- {tool.name}: {tool.description}")

            # Example: Call a resource (lammps://version)
            resource_contents = await client.read_resource("lammps://version")
            for content in resource_contents:
                 print(f"Response Content: {getattr(content, 'text', content)}")

            # Example: Call a tool (calculate_energy)
            tool_result = await client.call_tool("calculate_energy", {"element": "Cu", "lattice_constant": 3.615})
            for content in tool_result:
                 print(f"Response Content: {getattr(content, 'text', content)}")


    except ConnectionError as e:
         print(f"\n!!! Connection Error: Failed to connect via stdio transport. !!!")
         print(f"Details: {e}")
         # traceback.print_exc() # Uncomment for full connection traceback if needed

    except Exception as e:
        print(f"\n!!! An unexpected error occurred during client execution: !!!")
        traceback.print_exc() # Print detailed error information for other errors


if __name__ == "__main__":
    # Run the async main function, then exit immediately to avoid event-loop cleanup errors
    import os
    asyncio.run(main())
    os._exit(0)