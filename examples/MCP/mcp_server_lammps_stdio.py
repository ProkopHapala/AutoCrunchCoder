from mcp.server.fastmcp import Context, FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import os
import tempfile
import sys  # Add stderr logging



'''
FastMCP uses the MCP “stdio” transport, which means:

It spawns the server as a subprocess and marries your client and server over the child’s STDIN/STDOUT pipes.
Internally it frames MCP requests/responses (JSON + length prefixes) over those pipes.
Advantages vs HTTP/SSE

Lower overhead & latency (no HTTP headers, no event‑stream framing).
No external web server – just one process talking to its child.
You don’t need Uvicorn, TLS, CORS, ports, etc.
Disadvantages

Only works locally on the same machine/process hierarchy.
No network transparency (you can’t easily connect from another host).
You lose all the tooling around HTTP (proxies, logging middleware, load‑balancers).
Harder to secure/encrypt, no standard observability.
More verbose logging
I’ve instrumented the LAMMPS stdio server to print to stderr on:
Startup ("[SERVER] Starting stdio MCP server")
Lifespan init/teardown ("LAMMPS initialized successfully", "LAMMPS instance closed")
Every handler entry (get_lammps_version, run_lammps_simulation, calculate_energy).
'''

# Import LAMMPS after it's properly installed
try:
    from lammps import lammps
    LAMMPS_AVAILABLE = True
except ImportError:
    print("WARNING: LAMMPS Python bindings not found. Some features will be disabled.", file=sys.stderr)
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
        print("LAMMPS initialized successfully", file=sys.stderr)
    
    try:
        yield context
    finally:
        # Cleanup on shutdown
        if context.lmp is not None:
            context.lmp.close()
            LMP_INSTANCE = None
            print("LAMMPS instance closed", file=sys.stderr)

# Create the MCP server with our lifespan manager
mcp = FastMCP("LAMMPS-MCP", lifespan=app_lifespan)

@mcp.resource("lammps://version")
def get_lammps_version() -> str:
    """Return the LAMMPS version"""
    print("[SERVER] get_lammps_version called", file=sys.stderr)
    if not LAMMPS_AVAILABLE:
        return "LAMMPS not available"
    if LMP_INSTANCE is None:
        return "LAMMPS not initialized"
    version = LMP_INSTANCE.version()
    return f"LAMMPS version: {version}"

@mcp.tool()
def run_lammps_simulation(ctx: Context, script_content: str) -> str:
    """Run a LAMMPS simulation with the provided script content"""
    print(f"[SERVER] run_lammps_simulation called, script size={len(script_content)}", file=sys.stderr)
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"
    
    lmp = ctx.request_context.lifespan_context.lmp
    
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
        if lmp.has_error():
            return f"Error occurred during simulation: {lmp.get_last_error()}"
        else:
            return f"Simulation completed successfully. System contains {natoms} atoms."
    except Exception as e:
        return f"Error running LAMMPS simulation: {str(e)}"
    finally:
        # Clean up temporary file
        os.unlink(temp_filename)

@mcp.tool()
def calculate_energy(ctx: Context, element: str, lattice_constant: float) -> str:
    """Calculate energy of a simple crystal structure"""
    print(f"[SERVER] calculate_energy called, element={element}, lattice_constant={lattice_constant}", file=sys.stderr)
    if not LAMMPS_AVAILABLE:
        return "Error: LAMMPS not available"
    
    lmp = ctx.request_context.lifespan_context.lmp
    
    # Reset LAMMPS instance
    lmp.command("clear")
    
    # Set up a simple simulation
    lmp.command("units metal")
    lmp.command("atom_style atomic")
    lmp.command(f"lattice fcc {lattice_constant}")
    lmp.command("region box block 0 1 0 1 0 1")
    lmp.command("create_box 1 box")
    lmp.command(f"create_atoms 1 box")
    lmp.command(f"mass 1 {get_atomic_mass(element)}")
    
    # Use Lennard-Jones potential (avoid missing EAM files causing MPI abort)
    lmp.command("pair_style lj/cut 2.5")
    lmp.command("pair_coeff 1 1 1.0 1.0 2.5")
    
    # Calculate energy
    lmp.command("run 0")
    energy = lmp.get_thermo("pe")
    
    return f"Potential energy of {element} crystal (lattice constant {lattice_constant}): {energy} eV"

# Helper function to get atomic mass
def get_atomic_mass(element):
    masses = {
        "H": 1.008, "He": 4.003, "Li": 6.941, "Be": 9.012,
        "B": 10.811, "C": 12.011, "N": 14.007, "O": 15.999,
        "F": 18.998, "Ne": 20.180, "Na": 22.990, "Mg": 24.305,
        "Al": 26.982, "Si": 28.086, "P": 30.974, "S": 32.065,
        "Cl": 35.453, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
        "Cu": 63.546, "Ni": 58.693, "Ag": 107.868, "Au": 196.967
    }
    return masses.get(element, 1.0)  # Default to 1.0 if element not found

# Start the MCP server
if __name__ == "__main__":
    print("[SERVER] Starting stdio MCP server", file=sys.stderr)
    mcp.run(transport="stdio")
