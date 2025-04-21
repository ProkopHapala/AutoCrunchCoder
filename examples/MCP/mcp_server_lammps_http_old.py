import os
# import signal
# import subprocess
# import time
import sys
import traceback
from kill_servers import kill_mcp_servers

# Core fastmcp imports
from fastmcp import FastMCP, Context

# Import the specific SSE Server Transport - this is the HTTP one
try:
    from fastmcp.server.server import SseServerTransport
except ImportError:
    print("FATAL ERROR: Could not import SseServerTransport from fastmcp.")
    print("Please ensure fastmcp is installed correctly and is a compatible version (e.g., 2.2.1).")
    print("Try: pip install --upgrade fastmcp")
    sys.exit(1)

# Standard library imports needed for the rest of the script
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import tempfile


# Import LAMMPS after it's properly installed
try:
    from lammps import lammps
    LAMMPS_AVAILABLE = True
except ImportError:
    print("WARNING: LAMMPS Python bindings not found. Some features will be disabled.")
    LAMMPS_AVAILABLE = False

LMP_INSTANCE = None  # Global LAMMPS instance for resource access

# Create a context class to hold our LAMMPS instance
@dataclass
class AppContext:
    lmp: any = None

# Create a lifespan manager for the LAMMPS instance
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and clean up LAMMPS"""
    global LMP_INSTANCE
    global LAMMPS_AVAILABLE # <--- Add this line
    context = AppContext()

    if LAMMPS_AVAILABLE:
        try:
            # Initialize LAMMPS
            context.lmp = lammps()
            LMP_INSTANCE = context.lmp
            print("LAMMPS initialized successfully")
        except Exception as e:
            print(f"WARNING: Failed to initialize LAMMPS: {e}")
            LAMMPS_AVAILABLE = False # Mark unavailable if init fails


    try:
        yield context # This is where the server runs, using the context
    finally:
        # Cleanup on shutdown
        if context.lmp is not None:
            print("Cleaning up LAMMPS instance...")
            try:
                 context.lmp.close()
                 LMP_INSTANCE = None
                 print("LAMMPS instance closed.")
            except Exception as e:
                 print(f"Error closing LAMMPS instance: {e}")
        else:
            print("No LAMMPS instance to clean up.")


# Create the FastMCP application instance
# Use app_lifespan to manage the LAMMPS instance
mcp_app = FastMCP("LAMMPS-MCP", lifespan=app_lifespan)
print(f"Created FastMCP application object: {mcp_app.name}")


# --- LAMMPS Resources and Tools (keep these sections as they were) ---
# You can copy the get_lammps_version, run_lammps_simulation,
# calculate_energy, and get_atomic_mass functions from your previous script.

@mcp_app.resource("lammps://version")
def get_lammps_version() -> str:
    """Return the LAMMPS version"""
    if not LAMMPS_AVAILABLE:
        return "LAMMPS not available"
    if LMP_INSTANCE is None:
        return "LAMMPS not initialized"
    # Ensure the context object and lmp attribute exist before calling version()
    # Access lmp from global LMP_INSTANCE as resources don't get ctx directly
    if LMP_INSTANCE is not None and hasattr(LMP_INSTANCE, 'version'):
         version = LMP_INSTANCE.version()
         return f"LAMMPS version: {version}"
    else:
        return "LAMMPS instance not fully available for version check."


@mcp_app.tool()
def run_lammps_simulation(ctx: Context, script_content: str) -> str:
    """Run a LAMMPS simulation with the provided script content"""
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"

    # Get the lammps instance from the lifespan context provided in the tool ctx
    lmp = ctx.request_context.lifespan_context.lmp
    if lmp is None:
        return "Error: LAMMPS not initialized within context"

    temp_filename = None # Initialize outside try for finally block
    try:
        with tempfile.NamedTemporaryFile(suffix='.lmp', mode='w', delete=False) as temp:
            temp_filename = temp.name
            temp.write(script_content)
        print(f"Running LAMMPS script from temporary file: {temp_filename}")

        lmp.command("clear")
        lmp.file(temp_filename)
        natoms = lmp.get_natoms()

        if lmp.has_error():
            error_msg = ""
            if hasattr(lmp, 'get_last_error'):
                 try: line, file = lmp.get_last_error(); error_msg = f"(Line {line} in {file})"
                 except: pass # Handle potential errors in get_last_error itself
            return f"Error occurred during simulation {error_msg}"
        else:
            return f"Simulation completed successfully. System contains {natoms} atoms."
    except Exception as e:
        return f"Error running LAMMPS simulation: {str(e)}"
    finally:
        if temp_filename and os.path.exists(temp_filename):
             try:
                os.unlink(temp_filename)
                # print(f"Cleaned up temporary file: {temp_filename}") # Uncomment for more detail
             except Exception as e:
                print(f"Warning: Could not clean up temporary file {temp_filename}: {e}")


@mcp_app.tool()
def calculate_energy(ctx: Context, element: str, lattice_constant: float) -> str:
    """Calculate energy of a simple crystal structure"""
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"

    lmp = ctx.request_context.lifespan_context.lmp
    if lmp is None:
        return "Error: LAMMPS not initialized within context"

    try: # Wrap calculation in try block
        lmp.command("clear")

        lmp.command("units metal")
        lmp.command("atom_style atomic")
        lmp.command(f"lattice fcc {lattice_constant}")
        lmp.command("region box block 0 1 0 1 0 1")
        lmp.command("create_box 1 box")
        lmp.command(f"create_atoms 1 box")
        lmp.command(f"mass 1 {get_atomic_mass(element)}")

        potential_path = "/usr/share/lammps/potentials"
        if element.lower() in ['cu', 'ni', 'al', 'ag', 'au']:
            potential_file = os.path.join(potential_path, f"{element.lower()}_mm.eam")
            if os.path.exists(potential_file):
                lmp.command(f"pair_style eam")
                lmp.command(f"pair_coeff * * {potential_file}")
            else:
                 return f"Error: Potential file not found: {potential_file}. Please check if LAMMPS potentials are installed correctly."
        else:
            # Using Lennard-Jones as a fallback for other elements
            lmp.command("pair_style lj/cut 2.5")
            lmp.command("pair_coeff 1 1 1.0 1.0 2.5")
            print(f"Using Lennard-Jones potential for element: {element}") # Indicate fallback

        lmp.command("run 0")
        energy = lmp.get_thermo("pe")

        if lmp.has_error():
            try: line, file = lmp.get_last_error(); error_msg = f"(Line {line} in {file})"
            except: error_msg = ""
            return f"Error during energy calculation {error_msg}"
        else:
            return f"Potential energy of {element} crystal (lattice constant {lattice_constant}): {energy} eV"
    except Exception as e:
        return f"An error occurred during energy calculation setup: {str(e)}"


def get_atomic_mass(element):
    masses = {
        "H": 1.008, "He": 4.003, "Li": 6.941, "Be": 9.012,
        "B": 10.811, "C": 12.011, "N": 14.007, "O": 15.999,
        "F": 18.998, "Ne": 20.180, "Na": 22.990, "Mg": 24.305,
        "Al": 26.982, "Si": 28.086, "P": 30.974, "S": 32.065,
        "Cl": 35.453, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
        "Cu": 63.546, "Ni": 58.693, "Ag": 107.868, "Au": 196.967
    }
    return masses.get(element.capitalize(), 1.0) # Use capitalize and default





# ... (after the mcp_app = FastMCP(...) line) ...

print(f"Created FastMCP application object: {mcp_app.name}")

# --- Attempt to Inspect Routes ---
print("\nAttempting to inspect server routes...")
try:
    # FastMCP might have a direct attribute for the underlying ASGI app (often Starlette)
    # Common names are 'app', 'asgi_app', '_app', '_asgi_app', etc.
    # Let's check a few common possibilities
    potential_app_attrs = ['app', 'asgi_app', '_app', '_asgi_app']
    asgi_app_instance = None
    for attr_name in potential_app_attrs:
        if hasattr(mcp_app, attr_name):
            asgi_app_instance = getattr(mcp_app, attr_name)
            print(f"Found potential ASGI app instance via attribute: '{attr_name}'")
            break

    if asgi_app_instance and hasattr(asgi_app_instance, 'routes'):
        print("Available Routes:")
        for route in asgi_app_instance.routes:
            # Starlette routes have 'path' and 'endpoint' (the function/class handling it)
            # Some routes might have a 'name' as well
            route_info = f"  Path: {getattr(route, 'path', 'N/A')}"
            if hasattr(route, 'endpoint'):
                 route_info += f", Endpoint: {getattr(route.endpoint, '__name__', route.endpoint)}"
            if hasattr(route, 'name'):
                route_info += f", Name: {route.name}"
            print(route_info)
    elif hasattr(mcp_app, 'router') and hasattr(mcp_app.router, 'routes'):
         # Sometimes the router is exposed directly
         print("Available Routes (via mcp_app.router):")
         for route in mcp_app.router.routes:
             route_info = f"  Path: {getattr(route, 'path', 'N/A')}"
             if hasattr(route, 'endpoint'):
                 route_info += f", Endpoint: {getattr(route.endpoint, '__name__', route.endpoint)}"
             if hasattr(route, 'name'):
                 route_info += f", Name: {route.name}"
             print(route_info)
    else:
        print("Could not automatically find and print routes.")
        print("The SSE endpoint is likely hardcoded or configured internally by mcp_app.run(transport='sse').")
        # Common MCP SSE endpoint might be '/sse' or '/mcp'. Trying '/sse' next.

except Exception as e:
    print(f"An error occurred while trying to inspect routes: {e}")
# --- End Route Inspection ---


# --- START THE SERVER ---
if __name__ == "__main__":
    # ... (keep the kill_mcp_servers() call and the rest of the startup block
    #      using mcp_app.run(transport="sse", log_level="info") as in the previous step) ...
    # --- Call the killing function first ---
    kill_mcp_servers()
    # --------------------------------------

    # We need uvicorn installed as it's used by the 'sse' transport internally
    try:
        import uvicorn
        print("Uvicorn module imported successfully.")
    except ImportError:
        print("\nFATAL ERROR: uvicorn is not installed. Please ensure it's installed:")
        print("pip install \"uvicorn[standard]\"")
        sys.exit(1)

    # SseServerTransport does not need to be explicitly imported or instantiated here

    print(f"\nAttempting to start HTTP (SSE) server for '{mcp_app.name}' using mcp_app.run(transport='sse')...")
    print("Server might default to listening on localhost:8000.")
    print("If successful, you should see Uvicorn INFO messages below.")
    print("Press CTRL+C to stop the server.")

    try:
        # Call run() specifying ONLY transport="sse" and log_level.
        # Do NOT pass host or port here. Let's see if it uses defaults.
        mcp_app.run(
            transport="sse",
            log_level="info"
        )

        # This line is reached when the server is stopped (e.g., Ctrl+C)
        print("\nServer has shut down gracefully.")

    except Exception as e:
        print(f"\n!!! FAILED TO START HTTP (SSE) Server !!!")
        print("Error details:")
        traceback.print_exc()

    print("Server script finished.")



'''

if __name__ == "__main__":
    # --- Call the killing function first ---
    kill_mcp_servers()
    # --------------------------------------

    # We need uvicorn installed as it's used by the 'sse' transport internally
    try:
        import uvicorn
        print("Uvicorn module imported successfully.")
    except ImportError:
        print("\nFATAL ERROR: uvicorn is not installed. Please ensure it's installed:")
        print("pip install \"uvicorn[standard]\"")
        sys.exit(1)

    # SseServerTransport does not need to be explicitly imported or instantiated here

    print(f"\nAttempting to start HTTP (SSE) server for '{mcp_app.name}' using mcp_app.run(transport='sse')...")
    print("Server might default to listening on localhost:8000.")
    print("If successful, you should see Uvicorn INFO messages below.")
    print("Press CTRL+C to stop the server.")

    try:
        # === MODIFICATION START ===
        # Call run() specifying ONLY transport="sse" and log_level.
        # Do NOT pass host or port here. Let's see if it uses defaults.
        mcp_app.run(
            transport="sse",
            log_level="info"
        )
        # === MODIFICATION END ===

        # This line is reached when the server is stopped (e.g., Ctrl+C)
        print("\nServer has shut down gracefully.")

    except Exception as e:
        print(f"\n!!! FAILED TO START HTTP (SSE) Server !!!")
        print("Error details:")
        traceback.print_exc()

    print("Server script finished.")

'''