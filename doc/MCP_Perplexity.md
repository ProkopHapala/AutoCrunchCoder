# User Question 1

I would like to make MCP server binding (model context protocol) to my program for computational chemistry. I'm trying to figure out how to do that. For that pruprose I probably need to look how looks and works MCP bindings for other chemical tools like for LAMMPS, Gromas, Avogadro, Atomistic simulation environmenet (ASE), I I saw there are such. But I also don't undrstand exatly what it is and how it works. What part should be on the server side, what on the side of LLM API.

---

# Building MCP Server Bindings for Computational Chemistry Programs: A Practical Guide

Before diving into the code and implementation, I'll summarize the key points of this guide. The Model Context Protocol (MCP) is a standardized way for applications to expose data and functionality to Large Language Model (LLM) applications securely. For computational chemistry programs, MCP can enable LLMs to access molecular simulations, analyze structures, and run calculations through a consistent interface. This guide will walk you through installing the necessary components on Ubuntu 24 LTS and implementing a basic MCP server that binds to computational chemistry tools using Python.

## Understanding the Model Context Protocol (MCP)

The Model Context Protocol provides a standardized method for applications to offer context, data, and functionality to LLMs. It separates the concerns of providing context from the actual LLM interaction[3]. In the context of computational chemistry:

### Server vs Client Architecture

- **Server Side**: Your computational chemistry program exposes its functionality through an MCP server. This exposes data (resources) and actions (tools) that LLMs can access.
- **Client Side**: LLM applications like Claude Desktop or custom applications connect to your MCP server to access its functionality[2].

The separation allows your computational chemistry tools to run independently from the LLMs that use them, creating a more modular and maintainable system.

## Installing the MCP Python SDK

Let's begin by installing the Python MCP SDK on your Ubuntu 24 LTS system. Open a terminal and run the following commands:

```bash
# Create and activate a virtual environment (recommended)
python3 -m venv mcp-chem-env
source mcp-chem-env/bin/activate

# Install the MCP Python SDK with CLI tools
pip install "mcp[cli]"
```

You can verify the installation by running:

```bash
mcp --help
mcp version
```

This should display the version of the MCP SDK installed on your system[3].

## Creating a Basic MCP Server for Computational Chemistry

Let's create a minimal MCP server that demonstrates how to expose computational chemistry functionality. We'll start with a simple example and gradually add more features.

### Basic Server Structure

Create a new file named `chem_mcp_server.py`:

```python
from mcp.server.fastmcp import Context, FastMCP

# Create a named MCP server
mcp = FastMCP("ChemistryMCP")

# Define a simple resource that returns molecular information
@mcp.resource("molecules://info")
def get_molecule_info() -> str:
    """Return basic information about available molecules"""
    return "Available molecules: H2O, CH4, CO2, C6H6"

# Define a simple tool that performs a calculation
@mcp.tool()
def calculate_molecular_weight(formula: str) -> str:
    """Calculate the molecular weight of a given chemical formula"""
    # This is a simplified example
    weights = {"H": 1.008, "C": 12.011, "O": 15.999, "N": 14.007}
    
    # Very basic parser (would need a proper one for real use)
    total_weight = 0
    current_element = ""
    current_count = ""
    
    for char in formula + " ":  # Add space to process the last element
        if char.isalpha():
            if char.isupper():
                if current_element:
                    count = int(current_count) if current_count else 1
                    total_weight += weights.get(current_element, 0) * count
                    current_count = ""
                current_element = char
            else:
                current_element += char
        elif char.isdigit():
            current_count += char
        else:  # Space or other delimiter
            if current_element:
                count = int(current_count) if current_count else 1
                total_weight += weights.get(current_element, 0) * count
                current_element = ""
                current_count = ""
    
    return f"Molecular weight of {formula}: {total_weight:.3f} g/mol"

# Start the server
if __name__ == "__main__":
    mcp.run()
```

Save this file and run it with:

```bash
python chem_mcp_server.py &
```

This creates a basic MCP server that exposes information about molecules as a resource and provides a tool to calculate molecular weights[3].

## Integrating with LAMMPS for Molecular Dynamics

Now, let's create a more practical example by integrating with LAMMPS, a popular molecular dynamics software. First, ensure LAMMPS with Python bindings is installed:

```bash
# Install LAMMPS with Python bindings via conda (recommended approach)
sudo apt update
sudo apt install -y wget
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda
eval "$($HOME/miniconda/bin/conda shell.bash hook)"
conda init

# Create a new environment for LAMMPS
conda create --name lmp python=3.9
conda activate lmp
conda config --env --add channels conda-forge
conda install numpy matplotlib jupyter pandas
conda install lammps
```

Or install lammps with ubuntu package manager like:

```bash
sudo apt install lammps lammps-doc lammps-examples lammps-data python3-lammps liblammps0 liblammps-dev
```

Check the intalled packages
```bash
> apt list --installed | grep lammps
> dpkg -l | grep lammps
```

Result should be like this:
```bash

$ apt list --installed | grep lammps

WARNING: apt does not have a stable CLI interface. Use with caution in scripts.

lammps-data/jammy,jammy,now 20220106.git7586adbb6a+ds1-2 all [installed,automatic]
lammps-doc/jammy,jammy,now 20220106.git7586adbb6a+ds1-2 all [installed,automatic]
lammps-examples/jammy,jammy,now 20220106.git7586adbb6a+ds1-2 all [installed,automatic]
lammps/jammy,now 20220106.git7586adbb6a+ds1-2 amd64 [installed]
liblammps-dev/jammy,now 20220106.git7586adbb6a+ds1-2 amd64 [installed]
liblammps0/jammy,now 20220106.git7586adbb6a+ds1-2 amd64 [installed,automatic]
python3-lammps/jammy,now 20220106.git7586adbb6a+ds1-2 amd64 [installed]
prokophapala@carbsisYoga:~/git/AutoCrunchCoder/examples/MCP$ 

$ dpkg -l | grep lammps
ii  lammps                                                      20220106.git7586adbb6a+ds1-2                      amd64        Molecular Dynamics Simulator
ii  lammps-data                                                 20220106.git7586adbb6a+ds1-2                      all          Molecular Dynamics Simulator. Data (potentials)
ii  lammps-doc                                                  20220106.git7586adbb6a+ds1-2                      all          Molecular Dynamics Simulator (documentation)
ii  lammps-examples                                             20220106.git7586adbb6a+ds1-2                      all          Molecular Dynamics Simulator (examples)
ii  liblammps-dev                                               20220106.git7586adbb6a+ds1-2                      amd64        Molecular Dynamics Simulator (dev files)
ii  liblammps0:amd64                                            20220106.git7586adbb6a+ds1-2                      amd64        Molecular Dynamics Simulator (shared library)
ii  python3-lammps                                              20220106.git7586adbb6a+ds1-2                      amd64        Molecular Dynamics Simulator
```



Now, let's create an MCP server `lammps_mcp_server.py` that exposes LAMMPS functionality:

```python
from mcp.server.fastmcp import Context, FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import os
import tempfile

# Import LAMMPS after it's properly installed
try:
    from lammps import lammps
    LAMMPS_AVAILABLE = True
except ImportError:
    print("WARNING: LAMMPS Python bindings not found. Some features will be disabled.")
    LAMMPS_AVAILABLE = False

# Create a context class to hold our LAMMPS instance
@dataclass
class AppContext:
    lmp: any = None

# Create a lifespan manager for the LAMMPS instance
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and clean up LAMMPS"""
    context = AppContext()
    
    if LAMMPS_AVAILABLE:
        # Initialize LAMMPS with appropriate settings
        context.lmp = lammps()
        print("LAMMPS initialized successfully")
    
    try:
        yield context
    finally:
        # Cleanup on shutdown
        if context.lmp is not None:
            context.lmp.close()
            print("LAMMPS instance closed")

# Create the MCP server with our lifespan manager
mcp = FastMCP("LAMMPS-MCP", lifespan=app_lifespan)

@mcp.resource("lammps://version")
def get_lammps_version(ctx: Context) -> str:
    """Return the LAMMPS version"""
    if not LAMMPS_AVAILABLE:
        return "LAMMPS not available"
    
    lmp = ctx.request_context.lifespan_context.lmp
    version = lmp.version()
    return f"LAMMPS version: {version}"

@mcp.tool()
def run_lammps_simulation(ctx: Context, script_content: str) -> str:
    """Run a LAMMPS simulation with the provided script content"""
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
    
    # Use a simple potential (EAM for metals)
    if element.lower() in ['cu', 'ni', 'al', 'ag', 'au']:
        lmp.command(f"pair_style eam")
        lmp.command(f"pair_coeff * * /usr/share/lammps/potentials/{element.lower()}_mm.eam")
    else:
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
    mcp.run()
```

Run this server with:

```bash
conda activate lmp  # Ensure LAMMPS environment is active
python lammps_mcp_server.py
```

This creates an MCP server that exposes LAMMPS functionality through resources and tools. The server initializes LAMMPS when it starts and cleans up when it shuts down[1][3].

## Connecting to the MCP Server from an LLM Client

Now, let's create a simple client that connects to our MCP server to demonstrate how an LLM would interact with it. Create a file named `mcp_client.py`:

```python
import sys
import json
import requests

def main():
    print("Simple MCP Client")
    print("=================")
    
    # By default, the MCP server runs on stdio
    server_url = "http://localhost:8080/mcp"
    
    # Get server offerings (resources and tools)
    try:
        response = requests.post(
            server_url, 
            json={"type": "offerings/list"}
        )
        offerings = response.json()
        
        print("\nAvailable Resources:")
        for resource in offerings.get("resources", []):
            print(f"- {resource['name']}: {resource['description']}")
        
        print("\nAvailable Tools:")
        for tool in offerings.get("tools", []):
            print(f"- {tool['name']}: {tool['description']}")
            
        # Example: Call a resource
        print("\nCalling a resource:")
        resource_response = requests.post(
            server_url,
            json={
                "type": "resources/get",
                "uri": "lammps://version"
            }
        )
        print(f"Response: {resource_response.json()['content']}")
        
        # Example: Call a tool
        print("\nCalling a tool:")
        tool_response = requests.post(
            server_url,
            json={
                "type": "tools/run",
                "name": "calculate_energy",
                "inputs": {
                    "element": "Cu",
                    "lattice_constant": 3.615
                }
            }
        )
        print(f"Response: {tool_response.json()['content']}")
        
    except Exception as e:
        print(f"Error communicating with MCP server: {str(e)}")

if __name__ == "__main__":
    main()
```

However, the default MCP server in our example uses stdio for communication, not HTTP. To make it work with HTTP, you would need to modify the server to use a web transport. Let's create a modified version of our LAMMPS MCP server that works over HTTP:

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.transports.http import HTTPTransport
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import os
import tempfile

# Import LAMMPS after it's properly installed
try:
    from lammps import lammps
    LAMMPS_AVAILABLE = True
except ImportError:
    print("WARNING: LAMMPS Python bindings not found. Some features will be disabled.")
    LAMMPS_AVAILABLE = False

# Create a context class to hold our LAMMPS instance
@dataclass
class AppContext:
    lmp: any = None

# Create a lifespan manager for the LAMMPS instance
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and clean up LAMMPS"""
    context = AppContext()
    
    if LAMMPS_AVAILABLE:
        # Initialize LAMMPS with appropriate settings
        context.lmp = lammps()
        print("LAMMPS initialized successfully")
    
    try:
        yield context
    finally:
        # Cleanup on shutdown
        if context.lmp is not None:
            context.lmp.close()
            print("LAMMPS instance closed")

# Create the MCP server with HTTP transport and our lifespan manager
http_transport = HTTPTransport(host="0.0.0.0", port=8080)
mcp = FastMCP("LAMMPS-MCP", transport=http_transport, lifespan=app_lifespan)

# Define resources and tools (same as before)
@mcp.resource("lammps://version")
def get_lammps_version(ctx: Context) -> str:
    """Return the LAMMPS version"""
    if not LAMMPS_AVAILABLE:
        return "LAMMPS not available"
    
    lmp = ctx.request_context.lifespan_context.lmp
    version = lmp.version()
    return f"LAMMPS version: {version}"

@mcp.tool()
def run_lammps_simulation(ctx: Context, script_content: str) -> str:
    """Run a LAMMPS simulation with the provided script content"""
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
    
    # Use a simple potential (EAM for metals)
    if element.lower() in ['cu', 'ni', 'al', 'ag', 'au']:
        lmp.command(f"pair_style eam")
        lmp.command(f"pair_coeff * * /usr/share/lammps/potentials/{element.lower()}_mm.eam")
    else:
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
    print(f"Starting LAMMPS MCP server on http://0.0.0.0:8080/mcp")
    mcp.run()
```

Save this as `lammps_mcp_http_server.py` and run it:

```bash
conda activate lmp
python lammps_mcp_http_server.py
```

Now your MCP client should be able to connect to this HTTP server.

## Integrating with GROMACS

Similar to LAMMPS, we can create an MCP server for GROMACS. First, install GROMACS on Ubuntu:

```bash
sudo apt update
sudo apt install -y gromacs python3-pip
pip install gmxapi
```

Then create a GROMACS MCP server:

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.transports.http import HTTPTransport
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import subprocess
import tempfile
import os

# Create the MCP server with HTTP transport
http_transport = HTTPTransport(host="0.0.0.0", port=8081)
mcp = FastMCP("GROMACS-MCP", transport=http_transport)

@mcp.resource("gromacs://version")
def get_gromacs_version() -> str:
    """Return the GROMACS version"""
    try:
        result = subprocess.run(
            ["gmx", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error getting GROMACS version: {str(e)}"

@mcp.tool()
def run_gromacs_energy_minimization(pdb_file_content: str) -> str:
    """Run a simple GROMACS energy minimization on a PDB structure"""
    # Create temporary directory for GROMACS files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write PDB content to file
        pdb_path = os.path.join(temp_dir, "input.pdb")
        with open(pdb_path, "w") as f:
            f.write(pdb_file_content)
        
        try:
            # Convert PDB to GROMACS format
            subprocess.run(
                ["gmx", "pdb2gmx", "-f", pdb_path, "-o", os.path.join(temp_dir, "processed.gro"), 
                 "-water", "spce", "-ff", "oplsaa", "-ignh"],
                capture_output=True,
                check=True,
                cwd=temp_dir
            )
            
            # Define box
            subprocess.run(
                ["gmx", "editconf", "-f", os.path.join(temp_dir, "processed.gro"), 
                 "-o", os.path.join(temp_dir, "box.gro"), "-c", "-d", "1.0", "-bt", "cubic"],
                capture_output=True,
                check=True,
                cwd=temp_dir
            )
            
            # Create minimization MDP file
            mdp_content = """
; minim.mdp - used as input into grompp to generate em.tpr
integrator  = steep         ; Algorithm (steep = steepest descent minimization)
emtol       = 1000.0        ; Stop minimization when the maximum force < 1000.0 kJ/mol/nm
emstep      = 0.01          ; Minimization step size
nsteps      = 50000         ; Maximum number of (minimization) steps to perform

; Parameters describing how to find the neighbors of each atom
nstlist         = 1         ; Frequency to update the neighbor list
cutoff-scheme   = Verlet    ; Neighbor search method
ns_type         = grid      ; Method to determine neighbor list
coulombtype     = PME       ; Treatment of long range electrostatic interactions
rcoulomb        = 1.0       ; Short-range electrostatic cut-off
rvdw            = 1.0       ; Short-range Van der Waals cut-off
pbc             = xyz       ; Periodic Boundary Conditions in all directions
"""
            mdp_path = os.path.join(temp_dir, "minim.mdp")
            with open(mdp_path, "w") as f:
                f.write(mdp_content)
            
            # Prepare for minimization
            subprocess.run(
                ["gmx", "grompp", "-f", mdp_path, "-c", os.path.join(temp_dir, "box.gro"), 
                 "-p", os.path.join(temp_dir, "topol.top"), "-o", os.path.join(temp_dir, "em.tpr")],
                capture_output=True,
                check=True,
                cwd=temp_dir
            )
            
            # Run minimization
            result = subprocess.run(
                ["gmx", "mdrun", "-v", "-deffnm", os.path.join(temp_dir, "em")],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            # Extract and return results
            return f"Energy minimization completed:\n{result.stdout}"
            
        except subprocess.CalledProcessError as e:
            return f"Error running GROMACS: {e.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

# Start the MCP server
if __name__ == "__main__":
    print(f"Starting GROMACS MCP server on http://0.0.0.0:8081/mcp")
    mcp.run()
```

Save this as `gromacs_mcp_server.py` and run it:

```bash
python gromacs_mcp_server.py
```

## Connecting a Custom MCP Server to LLM Clients

To connect your MCP servers to LLM clients like Claude Desktop or other applications that support MCP, you typically need to:

1. Run your MCP server with the appropriate transport (HTTP, stdio, or SSE)
2. Configure the LLM client to connect to your MCP server

For Claude Desktop, follow these steps:

1. Open Claude Desktop
2. Go to Settings
3. Navigate to the MCP section
4. Click "Add MCP Server"
5. For HTTP servers:
   - Enter the URL (e.g., `http://localhost:8080/mcp` for the LAMMPS server)
   - Enter a name for the server (e.g., "LAMMPS Chemistry Tools")
6. Click "Save"

Now Claude should be able to use your computational chemistry tools through the MCP server[2][5].

## Troubleshooting Common Issues

### MCP Server Not Found

If you see an error like the one in search result[5]:

```
Error in MCP: A system error occurred (spawn /home/user/.nvm/versions/node/v22.14.0/bin/npx ENOENT)
```

This is typically because the required executable is not in the path. For Python-based MCP servers, ensure that:

1. The virtual environment is activated
2. All dependencies are installed
3. The server is running before attempting to connect

For example, if using SSH to connect to a remote server:

```bash
# On the remote server
python3 -m venv mcp-env
source mcp-env/bin/activate
pip install "mcp[cli]"
python lammps_mcp_http_server.py
```

### LAMMPS Integration Issues

If you encounter issues with LAMMPS integration:

1. Verify LAMMPS installation:
   ```bash
   conda activate lmp
   python -c "import lammps; print(lammps.__version__)"
   ```

2. Ensure all paths are correctly set:
   ```bash
   # Check LAMMPS executable path
   which lmp_serial
   ```

3. Ensure potential files are available:
   ```bash
   # Check if potential files exist
   ls -la /usr/share/lammps/potentials/
   ```

## Conclusion

In this guide, we've covered how to create MCP server bindings for computational chemistry programs, specifically focusing on LAMMPS and GROMACS. The key components include:

1. Installing the MCP Python SDK on Ubuntu 24 LTS
2. Creating basic MCP servers that expose computational chemistry functionality
3. Integrating with specific tools like LAMMPS and GROMACS
4. Configuring client applications to connect to the MCP servers

This approach allows you to expose your computational chemistry tools to LLMs in a standardized way, enabling more sophisticated interactions and analyses. As you develop your MCP servers further, you can add more resources and tools to expose additional functionality from your computational chemistry programs.

For more advanced usage, consider exploring the full capabilities of the MCP protocol, including more complex data structures, batch operations, and authentication mechanisms[3].

## Source:
taken from: https://www.perplexity.ai/search/i-would-like-to-make-mcp-serve-eq3TNFvCTr6JOOF9iiScCg

## Citations:
[1] https://gsalvatovallverdu.gitlab.io/python/2022-18-07-lammps-compute-with-python/
[2] https://www.classcentral.com/course/youtube-build-your-own-mcp-server-in-under-15-minutes-spring-ai-tutorial-439441
[3] https://github.com/modelcontextprotocol/python-sdk
[4] https://manual.gromacs.org/documentation/2024.0/manual-2024.pdf
[5] https://forum.cursor.com/t/mcp-failed-in-ssh-remote-server/56058
[6] https://utkstair.org/clausius/docs/mse614/pdf/intramolecular_intro_v02.pdf
[7] https://mcp.so/server/pubchem-mcp-server/PhelanShao
[8] https://www.youtube.com/watch?v=CiArUs_2jm4
[9] https://docs.lammps.org/Python_module.html
[10] https://www.youtube.com/watch?v=lbyPJqCI-tw&vl=en
[11] https://www.cavs.msstate.edu/icme/code/lammps/tutorials/lammps/vacancy.php
[12] https://xiangyu-yin.com/content/post_mp_mcp.html
[13] https://emberden.github.io/mcp.html
[14] https://www.lammps.org/workshops/Aug17/pdf/berger.pdf
[15] https://github.com/cnosuke/mcp-wolfram-alpha
[16] https://www.youtube.com/watch?v=qb95jXnCOdc
[17] https://docs.lammps.org/Howto_python.html
[18] https://ai.pydantic.dev/mcp/
[19] https://manuals.plus/m/512b2fce4658b95cbbfb5d478a01b75c472d69466893e7ff571cdef381916b52_pdf
[20] https://askubuntu.com/questions/1378643/installing-avogadro-1-2-0-from-source-ubuntu-20-04
[21] https://www.youtube.com/watch?v=jLM6n4mdRuA
[22] https://modelcontextprotocol.io/docs/concepts/tools
[23] https://sc20.supercomputing.org/app/uploads/2020/09/GROMACS_webinar_tutorial.pdf
[24] https://stackoverflow.com/questions/68998893/sybase-ase-client-tools-for-windows-and-linux
[25] https://www.youtube.com/watch?v=EyYJI8TPIj8
[26] https://docs.anthropic.com/en/docs/agents-and-tools/mcp
[27] http://www.mdtutorials.com/gmx/umbrella/index.html
[28] https://avogadro.cc/install/debianubuntupackages/
[29] https://www.cavs.msstate.edu/icme/code/lammps/
[30] https://www.sciencedirect.com/science/article/pii/S0010465521002836
[31] https://docs.lammps.org/pair_reaxff.html
[32] https://docs.lammps.org/fix_gcmc.html
[33] https://utkstair.org/clausius/docs/mse614/pdf/atb_moltemplate_example_v02.pdf
[34] https://matsci.org/t/pressure-calculation-in-lammps-with-frozen-electrodes/49882
[35] https://dev.to/pavanbelagatti/model-context-protocol-mcp-8-mcp-servers-every-developer-should-try-5hm2
[36] https://news.ycombinator.com/item?id=43348942
[37] https://pubs.acs.org/doi/abs/10.1021/acs.jpcb.3c08419
[38] https://mcp.so/server/ChemRxiv-MCP-Server
[39] https://www.youtube.com/watch?v=lbyPJqCI-tw&vl=en
[40] https://glama.ai/mcp/servers/@dougdotcon/QuantMCP

---

# User Question 2

Explain in detail the following aspects of using the Model Context Protocol (MCP) for integrating a computational chemistry program with an LLM API: (1) How an LLM client understands and interacts with an MCP server, including the discovery of functionalities and the formatting of requests, and whether external documentation is necessary. (2) The key differences and advantages of MCP compared to standard tool-use or function calling mechanisms in LLMs. (3) How to implement MCP using the general OpenAI API or similar standard LLM interfaces, minimizing reliance on specialized packages like `fastmcp` or Anthropic's SDK. (4) Provide a more low-level explanation of MCP server implementation, detailing the underlying mechanisms for defining resources and tools without relying on decorators.

(1) Research how MCP enables an LLM client to discover the capabilities (tools, resources, prompts) offered by an MCP server.
(2) Investigate the mechanisms within the MCP protocol that allow a server to describe its functionalities to a client in a standardized format.
(3) Find information on how an LLM client uses this discovered information to construct requests to the MCP server, including the expected format for tool calls and resource requests.
(4) Explore whether the MCP protocol itself includes standardized ways for a server to provide documentation or specifications for its functionalities to the client.
(5) Compare and contrast the Model Context Protocol (MCP) with the standard tool-use or function calling features commonly found in LLM APIs (like OpenAI's function calling). Identify the specific advantages that MCP offers beyond simply grouping functions.
(6) Investigate if MCP provides any inherent mechanisms for ensuring the LLM uses tools and resources in the correct format and with consistent parameters.
(7) Research how to implement an MCP client and server using the general OpenAI API or other widely supported LLM interfaces, focusing on minimizing dependencies on specific MCP SDKs like `fastmcp` or Anthropic's. Look for examples or conceptual approaches.
(8) Find resources that explain the core concepts of defining MCP resources and tools at a lower level, without the use of decorators. This might involve looking at the underlying message structures (like JSON-RPC) and how they are handled by MCP implementations. Focus on the server-side implementation.


---

# Integrating Computational Chemistry Programs with LLMs via MCP: Technical Deep Dive

## 1. LLM Client Interaction with MCP Servers

### Capability Discovery Mechanism
MCP servers expose functionalities through a structured JSON-RPC 2.0 interface. During the **initialization phase**:
```python
# Client discovery request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "offerings/list"
}

# Server response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "calculate_energy",
        "description": "Calculates molecular energy using DFT",
        "parameters": {
          "type": "object",
          "properties": {
            "molecule": {"type": "string"},
            "basis_set": {"type": "string"}
          }
        }
      }
    ],
    "resources": [
      {
        "uri": "molecules://active_site",
        "description": "Active site coordinates from MD simulation"
      }
    ]
  }
}
```
This dynamic discovery eliminates the need for preconfigured function definitions in the LLM[1][2].

### Request Formatting
LLM clients construct requests using the discovered schema:
```python
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "calculate_energy",
    "arguments": {
      "molecule": "H2O",
      "basis_set": "6-31G*"
    }
  }
}
```
Parameters are validated against the server's schema before execution[3][5].

### Documentation Handling
MCP embeds documentation through:
1. **Structured descriptions** in capability listings
2. **Type annotations** for parameters
3. **Error code standardization** (e.g., -32602 for invalid params)
External documentation becomes optional as servers expose machine-readable specs[2][4].

## 2. MCP vs Traditional Function Calling

| Feature               | MCP                                  | Standard Function Calling         |
|-----------------------|--------------------------------------|------------------------------------|
| Discovery             | Dynamic runtime negotiation         | Static preconfiguration           |
| Protocol              | JSON-RPC 2.0 with stateful sessions  | Ad-hoc JSON structures            |
| Tool Composition      | Native multi-step workflows         | Manual chaining required          |
| Security              | Built-in capability negotiation     | Custom implementation needed      |
| Context Management    | Session-aware with history tracking | Stateless per-call interactions   |
| Error Handling        | Standardized error codes            | Vendor-specific implementations   |

**Key Advantages**:
- **Dynamic tooling**: Add/remove capabilities without client updates[5]
- **Stateful sessions**: Maintain computational chemistry context across requests[4]
- **Standardized security**: Fine-grained access control through capability negotiation[1]

## 3. MCP Implementation with Standard LLM APIs

### Server Implementation (Python)
```python
from jsonrpcserver import method, serve

@method
def calculate_energy(molecule: str, basis_set: str) -> dict:
    # DFT calculation logic
    return {"energy": -76.423, "units": "Hartree"}

@method
def list_capabilities() -> dict:
    return {
        "tools": [{
            "name": "calculate_energy",
            "description": "DFT energy calculation",
            "parameters": {
                "molecule": {"type": "string"},
                "basis_set": {"type": "string"}
            }
        }]
    }

if __name__ == "__main__":
    serve(port=8080)
```

### Client Implementation (OpenAI)
```python
import openai
import requests

# Discover capabilities
capabilities = requests.post(
    "http://localhost:8080",
    json={"jsonrpc": "2.0", "id": 1, "method": "list_capabilities"}
).json()

# Generate LLM prompt with tool definitions
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{
        "role": "user", 
        "content": "Calculate H2O energy with 6-31G* basis set"
    }],
    functions=capabilities["result"]["tools"]
)

# Execute tool call
tool_call = response.choices[0].message.function_call
result = requests.post(
    "http://localhost:8080",
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_call.name,
            "arguments": json.loads(tool_call.arguments)
        }
    }
)
```
This approach uses standard JSON-RPC libraries instead of MCP-specific SDKs[3][5].

## 4. Low-Level MCP Server Implementation

### Core Components
1. **Transport Layer**
```bash
# Start simple HTTP server
python -m http.server 8080
```

2. **Request Router**
```python
import json
from http.server import BaseHTTPRequestHandler

class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(content_length))
        
        if data["method"] == "calculate_energy":
            result = calculate_energy(**data["params"])
        elif data["method"] == "list_capabilities":
            result = list_capabilities()
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
```

3. **Tool Registry**
```python
tools = {
    "calculate_energy": {
        "handler": lambda params: run_dft(params["molecule"]),
        "schema": {
            "type": "object",
            "properties": {
                "molecule": {"type": "string"},
                "basis_set": {"type": "string"}
            }
        }
    }
}
```

4. **Validation Layer**
```python
from jsonschema import validate

def validate_request(request):
    schema = tools[request["method"]]["schema"]
    validate(instance=request["params"], schema=schema)
```

### Session Management
```python
sessions = {}

def handle_request(request):
    session_id = request.get("session_id", uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {
            "created_at": datetime.now(),
            "context": {}
        }
    
    # Store computational chemistry context
    sessions[session_id]["context"].update(request.get("context", {}))
    
    return {
        "result": process_request(request),
        "session_id": session_id
    }
```
This architecture enables state preservation across multiple quantum chemistry calculations[1][4].

## Implementation Checklist

1. **Server Setup**
```bash
# Install required dependencies
sudo apt install python3-jsonschema python3-jsonrpcserver
pip install openai requests
```

2. **Protocol Compliance Testing**
```bash
# Validate JSON-RPC responses
curl -X POST http://localhost:8080 -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "list_capabilities"
}'
```

3. **Security Hardening**
```bash
# Add TLS encryption
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

This approach provides a foundation for building MCP-compliant computational chemistry servers while maintaining compatibility with standard LLM APIs[2][5].

Citations:
[1] https://www.linkedin.com/pulse/model-context-protocol-inside-mcp-architecture-martin-treiber-nj1qf
[2] https://apidog.com/blog/mcp-servers-explained/
[3] https://dev.to/fotiecodes/function-calling-vs-model-context-protocol-mcp-what-you-need-to-know-4nbo
[4] https://www.ucssolutions.com/blog/mcp-ai-integration/amp/
[5] https://www.linkedin.com/posts/eng-ajay_mcp-vs-function-calling-the-model-context-activity-7308905953481920513-ZbEG
[6] https://github.com/marchampson/mcp-openai-server
[7] https://dev.to/busycaesar/mcp-model-context-protocol-4o1l
[8] https://www.youtube.com/watch?v=Y_Rk6QgWUbE&vl=id
[9] https://smithery.ai/server/@melvincarvalho/mcpjs
[10] https://www.linkedin.com/pulse/model-context-protocol-mcp-comprehensive-guide-muhammad-usman-khan-ejcpf
[11] https://dev.to/composiodev/what-is-model-context-protocol-mcp-explained-in-detail-5f53
[12] https://dev.to/e77/what-is-model-context-protocol-3b3f
[13] https://www.geeky-gadgets.com/model-context-protocol-mcp-explained/
[14] https://apidog.com/blog/mcp-servers-openai-agents/
[15] https://gist.github.com/onigetoc/2f572fa0878e9dd6a14bf7441b3e9c0b
[16] https://spec.modelcontextprotocol.io/specification/draft/basic/messages/
[17] https://blog.treblle.com/model-context-protocol-guide/
[18] https://dev.to/lynn_mikami_e94e5b9ad7daf/what-is-mcp-server-clearly-explained-210l
[19] https://securityboulevard.com/2025/03/what-is-the-model-context-protocol-mcp-and-how-it-works/
[20] https://github.com/S1M0N38/mcp-openai
[21] https://dev.to/shrsv/unpacking-the-mcp-base-protocol-3f3n
[22] https://dev.to/prajwalnayak/model-context-protocol-mcp-a-new-standard-for-ai-tool-interoperability-1e6d
[23] https://www.linkedin.com/pulse/diving-model-context-protocol-mcp-victor-karabedyants-qyjpf
[24] https://www.byteplus.com/en/blog/what-is-model-context-protocol
[25] https://www.youtube.com/watch?v=2GywjEOzZIY
[26] https://medium.com/@sal_12830/mcp-servers-what-they-are-and-what-do-they-do-036e9cac18b6
[27] https://daily.dev/blog/what-is-mcp-model-context-protocol
[28] https://ubos.tech/mcp/api-docs-mcp-server/
[29] https://www.runloop.ai/blog/function-calling-vs-model-context-protocol-mcp
[30] https://community.openai.com/t/a-surprising-discovery-me-about-mcp-and-function-calling/1223345
[31] https://www.linkedin.com/posts/cloudyamit_mcp-functioncalling-activity-7318890636311441408-VU0x
[32] https://www.gentoro.com/blog/function-calling-vs-model-context-protocol-mcp
[33] https://www.youtube.com/watch?v=fACswFtqCes
[34] https://blog.cubed.run/from-openai-api-compatibility-apis-to-mcp-compatible-agents-an-evolution-in-ai-integration-d18d26c39c1e?gi=7f75b42707c0
[35] https://community.openai.com/t/preparing-for-mcp-in-responses/1152972
[36] https://dev.to/composiodev/how-to-build-mcp-servers-and-clients-from-scratch-4o2f
[37] https://github.com/melvincarvalho/mcpjs
[38] https://hexdocs.pm/hermes_mcp/0.2.0/message_handling.html
[39] https://glama.ai/mcp/servers/cn5q63wd5r/blob/main/docs/03-building-mcp-servers-python.md
[40] https://www.linkedin.com/pulse/model-context-protocol-inside-mcp-architecture-martin-treiber-nj1qf
[41] https://www.linkedin.com/posts/kumarbandaru_%F0%9D%97%A0%F0%9D%97%96%F0%9D%97%A3-%F0%9D%97%97%F0%9D%97%B2%F0%9D%97%B2%F0%9D%97%BD-%F0%9D%97%97%F0%9D%97%B6%F0%9D%98%83%F0%9D%97%B2-%F0%9D%97%A7%F0%9D%97%BC%F0%9D%97%BC%F0%9D%97%B9%F0%9D%98%80-%F0%9D%97%A5%F0%9D%97%B2%F0%9D%98%80%F0%9D%97%BC%F0%9D%98%82%F0%9D%97%BF%F0%9D%97%B0%F0%9D%97%B2%F0%9D%98%80-activity-7314289780404473856-wjo4
[42] https://www.npmjs.com/package/@meldscience/mcp-tool-processor
[43] https://github.com/alekspetrov/mcp-docs-service/blob/main/docs/guides/mcp-integration.md
[44] https://neo4j.com/blog/developer/model-context-protocol/
[45] https://fossunited.org/c/bennett-university/linuxfest/cfp/j6st8frkk2
[46] https://towardsdatascience.com/clear-intro-to-mcp/
[47] https://dev.to/anguske/frontend-mcp-tool-development-tutorial-1pb4
[48] https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/
[49] https://www.innoq.com/en/articles/2025/03/model-context-protocol/
[50] https://github.com/SubaashNair/documentation-mcp-server
[51] https://ibis.org/interconnect_wip/Sigrity_MCP_Specification.pdf
[52] https://www.dremio.com/blog/what-is-the-model-context-protocol-mcp-and-why-it-matters-for-ai-applications/
[53] https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/
[54] https://apidog.com/blog/fastmcp/
[55] https://github.com/zcaceres/easy-mcp
[56] https://github.com/jlowin/fastmcp
[57] https://mcp.programnotes.cn/specification
[58] https://github.com/zcaceres/easy-mcp/blob/main/README.md

---
Answer from Perplexity: https://www.perplexity.ai/search/i-would-like-to-make-mcp-serve-eq3TNFvCTr6JOOF9iiScCg?utm_source=copy_output