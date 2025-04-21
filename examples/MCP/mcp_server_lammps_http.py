# Core MCP components are directly under the fastmcp package
from fastmcp import Context, FastMCP

# Other necessary standard library imports
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import os
import tempfile
from kill_servers import kill_mcp_servers
import sys  # ensure sys is available for exit
import glob  # for finding potential files

# Import LAMMPS (keep this section as is)
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
    context = AppContext()

    if LAMMPS_AVAILABLE:
        # Initialize LAMMPS with appropriate settings
        context.lmp = lammps()
        LMP_INSTANCE = context.lmp
        print("LAMMPS initialized successfully")

    try:
        yield context
    finally:
        # Cleanup on shutdown
        if context.lmp is not None:
            # Use the lmp instance from the context we created
            context.lmp.close()
            LMP_INSTANCE = None
            print("LAMMPS instance closed")

# === MODIFICATION START ===
# Create the MCP server instance.
# We DO NOT need to create or pass an HTTPTransport object.
# FastMCP likely uses an ASGI server like Uvicorn internally.
mcp_app = FastMCP("LAMMPS-MCP", lifespan=app_lifespan)
# === MODIFICATION END ===


# --- LAMMPS Resources and Tools ---
# (Your existing LAMMPS functions remain unchanged)

@mcp_app.resource("lammps://version")
def get_lammps_version() -> str:
    """Return the LAMMPS version"""
    if not LAMMPS_AVAILABLE:
        return "LAMMPS not available"
    if LMP_INSTANCE is None:
        return "LAMMPS not initialized"
    version = LMP_INSTANCE.version()
    return f"LAMMPS version: {version}"

@mcp_app.tool()
def run_lammps_simulation(ctx: Context, script_content: str) -> str:
    """Run a LAMMPS simulation with the provided script content"""
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"

    # Get the lammps instance from the lifespan context
    lmp = ctx.request_context.lifespan_context.lmp
    if lmp is None:
        return "Error: LAMMPS not initialized within context"

    # Create a temporary file for the LAMMPS script
    with tempfile.NamedTemporaryFile(suffix='.lmp', mode='w', delete=False) as temp:
        temp_filename = temp.name
        temp.write(script_content)

    try:
        # Reset LAMMPS instance for a new simulation
        lmp.command("clear")

        # Run the simulation script
        lmp.file(temp_filename)

        # Return some basic results
        natoms = lmp.get_natoms()
        if hasattr(lmp, 'has_error') and lmp.has_error():
            # Use get_last_error message method if available
            error_msg = ""
            if hasattr(lmp, 'get_last_error'):
                 line, file = lmp.get_last_error()
                 error_msg = f"(Line {line} in {file})" # Or however the error is formatted
            return f"Error occurred during simulation {error_msg}"
        else:
            return f"Simulation completed successfully. System contains {natoms} atoms."
    except Exception as e:
        return f"Error running LAMMPS simulation: {str(e)}"
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filename):
             os.unlink(temp_filename)


@mcp_app.tool()
def calculate_energy(ctx: Context, element: str, lattice_constant: float) -> str:
    """Calculate energy of a simple crystal structure"""
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"

    # Get the lammps instance from the lifespan context
    lmp = ctx.request_context.lifespan_context.lmp
    if lmp is None:
        return "Error: LAMMPS not initialized within context"

    # Reset LAMMPS instance
    lmp.command("clear")

    # Set up a simple simulation
    lmp.command("units metal")
    lmp.command("atom_style atomic")
    lmp.command(f"lattice fcc {lattice_constant}")
    lmp.command("region box block 0 1 0 1 0 1")
    lmp.command("create_box 1 box")
    lmp.command(f"create_atoms 1 box")
    lmp.command(f"mass 1 {get_atomic_mass(element)}") # Using helper function below

    # Determine and load a suitable EAM potential (case-insensitive match)
    potential_path = "/usr/share/lammps/potentials"
    patterns = [f"{element.lower()}*.eam*", f"{element.capitalize()}*.eam*"]
    matches = []
    for pat in patterns:
        matches = glob.glob(os.path.join(potential_path, pat))
        if matches:
            break
    if matches:
        potential_file = matches[0]
        lmp.command("pair_style eam")
        lmp.command(f"pair_coeff * * {potential_file}")
    else:
        # No EAM found; fallback to Lennard-Jones
        lmp.command("pair_style lj/cut 2.5")
        lmp.command("pair_coeff 1 1 1.0 1.0 2.5")
    # Configure thermo and perform energy minimization for accurate potential energy
    lmp.command("thermo_style custom pe")
    lmp.command("thermo 1")
    lmp.command("minimize 1e-8 1e-10 1000 1000")
    # Calculate energy
    lmp.command("run 0")
    energy = lmp.get_thermo("pe")

    if hasattr(lmp, 'has_error') and lmp.has_error():
        line, file = lmp.get_last_error()
        return f"Error during energy calculation (Line {line} in {file})"
    else:
        return f"Potential energy of {element} crystal (lattice constant {lattice_constant}): {energy} eV"

# Helper function to get atomic mass
def get_atomic_mass(element):
    # (Keep your existing get_atomic_mass function here)
    masses = {
        "H": 1.008, "He": 4.003, "Li": 6.941, "Be": 9.012,
        "B": 10.811, "C": 12.011, "N": 14.007, "O": 15.999,
        "F": 18.998, "Ne": 20.180, "Na": 22.990, "Mg": 24.305,
        "Al": 26.982, "Si": 28.086, "P": 30.974, "S": 32.065,
        "Cl": 35.453, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
        "Cu": 63.546, "Ni": 58.693, "Ag": 107.868, "Au": 196.967
    }
    return masses.get(element.capitalize(), 1.0)  # Use capitalize and default


def check_lammps():
    try:
        from lammps import lammps
        lmp = lammps()
        print("LAMMPS version:", lmp.version())
        return True
    except ImportError:
        print("LAMMPS not found. Please install lammps and its Python bindings.")
        return False

# Start the MCP server
if __name__ == "__main__":
    # --- Call the killing function first ---
    kill_mcp_servers()
    # --------------------------------------

    # We still need uvicorn installed for the 'sse' transport
    try:
        import uvicorn
        print("Uvicorn module imported successfully.")
    except ImportError:
        print("ERROR: uvicorn seems to be missing. Please ensure it's installed:")
        print("pip install \"uvicorn[standard]\"")
        sys.exit(1)

    host = "0.0.0.0"  # Listen on all interfaces
    #port = 8888       # Keep the different port (8888) to avoid conflicts immediately
    port = 8000
    print(f"\nAttempting to start HTTP (SSE) server for '{mcp_app.name}' using mcp_app.run()...")
    print(f"Will listen on: http://{host}:{port}")
    print("If successful, you should see Uvicorn INFO messages below.")
    print("Press CTRL+C to stop the server.")

    try:
        # === MODIFICATION START ===
        # Use the run method, specifying the transport as 'sse'
        # Pass host and port as arguments to the 'sse' transport configuration
        mcp_app.run(
            transport="sse",
            host=host,
            port=port,
            log_level="info" # Keep info level for standard Uvicorn messages
        )
        # === MODIFICATION END ===

        # This line is reached when the server is stopped (e.g., Ctrl+C)
        print("\nServer has shut down gracefully.")

    except Exception as e:
        # Catch and print any error during server startup
        print(f"\n!!! FAILED TO START HTTP (SSE) Server !!!")
        print("Error details:")
        import traceback
        traceback.print_exc()

    print("Server script finished.")