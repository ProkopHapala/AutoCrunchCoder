import sys
import json
import asyncio
import traceback # Import traceback for better error printing

# Import the SSETransport for connecting to an HTTP (SSE) server
try:
    from fastmcp.client import Client
    from fastmcp.client.transports import SSETransport
except ImportError:
    print("FATAL ERROR: Could not import Client or SSETransport from fastmcp.")
    print("Please ensure fastmcp is installed correctly (e.g., pip install fastmcp).")
    sys.exit(1)

async def main():
    print("Simple MCP Client (Connecting via SSE)")
    print("=====================================")

    # Correct Server URL based on server output and successful connection
    server_url = "http://localhost:8000/sse" # <-- Use port 8000 and /sse path

    print(f"Attempting to connect to server at: {server_url}")

    try:
        # Initialize the SSETransport with the server URL
        transport = SSETransport(server_url)

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
         print(f"\n!!! Connection Error: Failed to connect to {server_url}. Is the server running? !!!")
         print(f"Details: {e}")
         # traceback.print_exc() # Uncomment for full connection traceback if needed

    except Exception as e:
        print(f"\n!!! An unexpected error occurred during client execution: !!!")
        traceback.print_exc() # Print detailed error information for other errors


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())