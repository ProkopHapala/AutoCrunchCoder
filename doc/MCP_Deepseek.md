# User Question 1

I would like to make MCP server binding (model context protocol) to my program for computational chemistry. I'm trying to figure out how to do that. For that pruprose I probably need to look how looks and works MCP bindings for other chemical tools like for LAMMPS, Gromas, Avogadro, Atomistic simulation environmenet (ASE), I I saw there are such. But I also don't undrstand exatly what it is and how it works. What part should be on the server side, what on the side of LLM API. 

Rather than going into deep theory, I would like some cookbook, or tutorial. Which explains think in clear python code examples, and explain also what to install on the server and on the client machine. (currently it is the same machine, localhost, but later this may change). I'm on linux (ubunti 24 LTS), so when I should install something, please give me example how to do it in terminal / bash.

---

# Building an MCP Server for Computational Chemistry: A Practical Guide

## Understanding MCP for Computational Chemistry

The Model Context Protocol (MCP) provides a standardized way to connect your computational chemistry tools with large language models (LLMs) like Claude or GPT. This allows you to create AI-powered workflows where the LLM can interact with your chemistry software, query data, and even trigger calculations - all through a unified interface .

For your use case, you'll want to:
1. Create an MCP server that exposes your computational chemistry tools/functions
2. Connect this server to an MCP client (like VS Code with Copilot or Claude Desktop)
3. Have the LLM use these tools when relevant to chemistry queries

## Prerequisites and Setup

First, let's set up your Ubuntu 24.04 environment:

```bash
# Install Python 3.11 (recommended for MCP compatibility)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Install uv (modern Python project manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # Restart shell to make uv available

# Create project directory
mkdir chem-mcp-server
cd chem-mcp-server

# Create virtual environment
uv venv
source .venv/bin/activate

# Install MCP SDK and chemistry dependencies
uv add "mcp[cli]" numpy pandas ase  # ASE = Atomic Simulation Environment
```

## Basic MCP Server Structure

Create a file named `chem_server.py` with this basic structure:

```python
from mcp.server.fastmcp import FastMCP
from ase import Atoms
from ase.calculators.emt import EMT
import numpy as np

# Initialize MCP server with a chemistry-specific name
mcp = FastMCP("Computational Chemistry Server")

# Add your chemistry tools here using @mcp.tool() decorator

if __name__ == "__main__":
    mcp.run(transport='stdio')
```

## Example Chemistry Tools to Expose

Here are some practical examples of computational chemistry tools you might expose:

### 1. Molecular Energy Calculation

```python
@mcp.tool()
def calculate_energy(chemical_formula: str) -> dict:
    """
    Calculate the energy of a molecule using EMT calculator.
    
    Args:
        chemical_formula: Chemical formula (e.g., 'H2O')
    
    Returns:
        Dictionary with energy and other properties
    """
    try:
        # Create molecule using ASE
        molecule = Atoms(chemical_formula)
        molecule.calc = EMT()
        energy = molecule.get_potential_energy()
        
        return {
            "energy": float(energy),
            "formula": chemical_formula,
            "calculator": "EMT",
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
```

### 2. Molecular Dynamics Simulation

```python
@mcp.tool()
def run_md_simulation(
    formula: str,
    temperature: float = 300.0,
    steps: int = 1000,
    timestep: float = 1.0
) -> dict:
    """
    Run simple molecular dynamics simulation.
    
    Args:
        formula: Chemical formula
        temperature: Temperature in Kelvin
        steps: Number of MD steps
        timestep: Time step in fs
    
    Returns:
        Dictionary with trajectory and energy data
    """
    from ase.md import VelocityVerlet
    from ase import units
    
    try:
        atoms = Atoms(formula)
        atoms.calc = EMT()
        
        # Set momenta corresponding to temperature
        atoms.set_momenta(np.random.randn(len(atoms), 3) * np.sqrt(units.kB * temperature))
        
        # Run MD
        dyn = VelocityVerlet(atoms, timestep=timestep * units.fs)
        energies = []
        for _ in range(steps):
            dyn.run(1)
            energies.append(atoms.get_potential_energy())
            
        return {
            "energies": [float(e) for e in energies],
            "temperature": temperature,
            "steps": steps,
            "timestep": timestep,
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
```

### 3. Chemical Property Prediction

```python
@mcp.tool()
def predict_properties(formula: str) -> dict:
    """
    Predict basic chemical properties (example implementation).
    
    Args:
        formula: Chemical formula
    
    Returns:
        Dictionary with predicted properties
    """
    try:
        # This is a placeholder - replace with your actual prediction code
        # Could connect to your existing models or quantum chemistry codes
        
        # Simple example using ASE for basic properties
        atoms = Atoms(formula)
        atoms.calc = EMT()
        
        return {
            "formula": formula,
            "energy": float(atoms.get_potential_energy()),
            "forces": atoms.get_forces().tolist(),
            "dipole_moment": np.linalg.norm(atoms.get_dipole_moment()),
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
```

## Running and Testing Your Server

### Local Testing with MCP Inspector

```bash
# In your activated virtual environment
mcp dev chem_server.py
```

This will start a web-based inspector at `http://localhost:8000` where you can:
1. See all available tools
2. Test them with different parameters
3. View responses 

### Integrating with VS Code

1. Create a `.vscode/mcp.json` file in your workspace:

```json
{
  "servers": {
    "ChemistryServer": {
      "type": "stdio",
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/chem_server.py"],
      "description": "Computational Chemistry Tools"
    }
  }
}
```

2. In VS Code:
   - Open the Command Palette (Ctrl+Shift+P)
   - Run "MCP: List Servers"
   - Start your server 

### Integrating with Claude Desktop

Edit the Claude Desktop config file:

```bash
# On Linux
code ~/.config/claude/claude_desktop_config.json
```

Add your server configuration:

```json
{
  "mcpServers": {
    "ChemistryServer": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/chem_server.py"],
      "description": "Computational Chemistry Tools"
    }
  }
}
```

Restart Claude Desktop to see your tools available 

## Advanced Topics

### 1. Connecting to Existing Chemistry Software

You can modify the tools to interface with your existing chemistry codes:

```python
@mcp.tool()
def run_lammps_simulation(input_script: str) -> str:
    """
    Run LAMMPS simulation with provided input script.
    
    Args:
        input_script: LAMMPS input script content
    
    Returns:
        Simulation output
    """
    import subprocess
    
    try:
        # Write input file
        with open("in.lammps", "w") as f:
            f.write(input_script)
            
        # Run LAMMPS
        result = subprocess.run(
            ["lammps", "-in", "in.lammps"],
            capture_output=True,
            text=True
        )
        
        return result.stdout
    except Exception as e:
        return f"Error running LAMMPS: {str(e)}"
```

### 2. Handling Large Outputs

For large simulation outputs, consider:

```python
@mcp.tool()
def get_simulation_results(simulation_id: str) -> dict:
    """
    Retrieve results from a previously run simulation.
    
    Args:
        simulation_id: ID of the simulation
    
    Returns:
        Dictionary with results or status
    """
    # Implement your result caching/retrieval system here
    # Could return file paths or summaries rather than full data
    pass
```

### 3. Security Considerations

When exposing tools that run simulations:
- Validate all inputs
- Set reasonable timeouts
- Consider resource limits
- Use proper error handling 

## Deployment Considerations

When moving beyond localhost:

1. For remote servers, use SSE (Server-Sent Events) transport:

```python
if __name__ == "__main__":
    mcp.run(transport='sse', host='0.0.0.0', port=8000)
```

2. Configure firewall rules to allow access to your MCP port
3. Consider authentication if exposing sensitive chemistry tools 

## Example Workflow

Here's how your tools might be used by an LLM:

1. User asks: "What's the energy of a water molecule?"
2. LLM detects this requires your `calculate_energy` tool
3. LLM calls the tool with `formula="H2O"`
4. Your server runs the calculation and returns results
5. LLM formats the response: "The energy of H2O is X eV according to EMT calculator" 

## Troubleshooting

Common issues and solutions:

1. **Server not starting**:
   - Check Python version (`python3.11 --version`)
   - Ensure virtual environment is activated
   - Check for missing dependencies (`uv pip list`)

2. **Tools not showing in client**:
   - Verify server is running
   - Check client configuration
   - Look at server logs for errors 

3. **Performance issues**:
   - Add logging to identify slow operations
   - Consider async tools for long-running calculations
   - Implement caching where appropriate

## Next Steps

To extend this basic setup:

1. Add more chemistry-specific tools
2. Implement connection to your existing codes
3. Add resource endpoints for common chemistry data
4. Create prompt templates for common chemistry workflows 

This practical guide should give you a solid foundation for integrating your computational chemistry work with LLMs through MCP. The protocol's flexibility allows you to start simple and expand functionality as needed.


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

# Comprehensive Guide to Model Context Protocol (MCP) for Computational Chemistry Integration

## 1. LLM Client Interaction with MCP Server

### Discovery Mechanism
The MCP protocol enables automatic discovery of server capabilities through a structured JSON-RPC 2.0 based communication system. When an LLM client connects to an MCP server, the server advertises its available tools, resources, and prompt templates in a standardized format . This discovery process occurs through:

1. **Capability Advertisement**: The server sends a `server/info` message containing:
   - Tool descriptions with parameter schemas (name, type, description)
   - Resource endpoints with access methods
   - Available prompt templates for common workflows 

2. **Dynamic Tool Registration**: Unlike static API documentation, MCP servers can update their advertised capabilities at runtime, allowing for adaptive integration .

### Request Formatting
The LLM client formats requests using JSON-RPC messages with these components:
- **Method**: Namespaced action (e.g., `tools/calculate_energy`)
- **Params**: Structured input matching the server's schema
- **ID**: Unique identifier for tracking responses 

For computational chemistry, a request might look like:
```json
{
  "jsonrpc": "2.0",
  "method": "chemistry/calculate_energy",
  "params": {
    "molecule": "H2O",
    "method": "DFT",
    "basis_set": "6-31G*"
  },
  "id": "req_123"
}
```

### Documentation Handling
MCP servers embed documentation directly in their capability descriptions:
- **Tool Descriptions**: Included in the discovery payload
- **Parameter Metadata**: Type hints and validation rules
- **Example Values**: Common usage patterns 

This eliminates the need for external documentation while ensuring the LLM always has current information. The protocol supports markdown-formatted descriptions for rich documentation .

## 2. MCP Advantages Over Standard Tool-Use

### Key Differentiators
1. **Stateful Sessions**: MCP maintains context across interactions, allowing multi-step workflows where traditional function calling treats each request as isolated .

2. **Bidirectional Communication**: Servers can initiate requests to the LLM (sampling), enabling collaborative workflows impossible with one-way function calling .

3. **Standardized Discovery**: Automatic capability detection replaces manual API specification handling required in standard tool-use .

4. **Resource Abstraction**: MCP treats data sources as first-class citizens (via `resources/` endpoints) rather than just functions .

### Chemistry-Specific Benefits
For computational chemistry integration:
- **Complex Workflows**: Chain quantum calculations with visualization tools
- **Data Awareness**: Direct access to molecular databases
- **Prompt Templates**: Pre-defined chemistry question patterns 

Example advantage: An MCP-enabled chemistry server could maintain calculation state across multiple refinement steps, while standard function calling would require re-specifying all parameters.

## 3. Implementing MCP with Standard LLM APIs

### Core Implementation Strategy
To minimize dependencies, implement these components:

1. **Transport Layer**:
```python
# Using WebSockets for bidirectional communication
import websockets

async def handle_mcp_connection(websocket):
    while True:
        message = await websocket.recv()
        response = await process_mcp_message(json.loads(message))
        await websocket.send(json.dumps(response))
```

2. **Message Processing**:
```python
async def process_mcp_message(message):
    if message["method"] == "server/info":
        return get_capabilities()
    elif message["method"].startswith("tools/"):
        return await call_tool(message)
```

3. **OpenAI Integration**:
```python
def prepare_openai_prompt(mcp_capabilities):
    tools = [{
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["parameters"]
    } for tool in mcp_capabilities["tools"]]
    
    return {
        "messages": [...],
        "tools": tools,
        "tool_choice": "auto"
    }
```

### Key Implementation Patterns
1. **Capability Registry**: Maintain a dynamic list of available tools/resources
2. **JSON-RPC Router**: Direct messages to appropriate handlers
3. **Schema Validation**: Ensure parameter compliance before execution

## 4. Low-Level MCP Server Implementation

### Resource Definition
Without decorators, define resources explicitly:

```python
class ChemistryResources:
    def __init__(self):
        self.molecules = {}  # In-memory storage
        self.calculations = {}

    async def handle_resource_request(self, method, params):
        if method == "resources/molecules/create":
            molecule_id = generate_id()
            self.molecules[molecule_id] = params["structure"]
            return {"id": molecule_id}
        elif method == "resources/molecules/get":
            return {"structure": self.molecules[params["id"]]}
```

### Tool Implementation
Raw tool handling involves:

1. **Schema Definition**:
```python
calculate_energy_schema = {
    "name": "calculate_energy",
    "description": "Perform quantum energy calculation",
    "parameters": {
        "molecule": {"type": "string", "description": "Chemical formula"},
        "method": {"type": "string", "enum": ["DFT", "MP2", "CCSD"]},
        "basis_set": {"type": "string"}
    }
}
```

2. **Execution Handler**:
```python
async def execute_calculation(params):
    # Validate against schema
    if not validate_params(params, calculate_energy_schema["parameters"]):
        raise InvalidParamsError
    
    # Call computational backend
    result = run_quantum_calculation(
        params["molecule"],
        params["method"],
        params["basis_set"]
    )
    
    return {"energy": result.energy, "forces": result.forces}
```

### Protocol-Level Components
1. **Message Structure**:
```python
{
    "jsonrpc": "2.0",
    "method": "chemistry/calculate_energy",
    "params": {...},
    "id": "unique_id"
}
```

2. **Error Handling**:
```python
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32602,
        "message": "Invalid parameters",
        "data": {"param": "basis_set", "issue": "Unsupported basis set"}
    },
    "id": "req_123"
}
```

### State Management
Maintain session state for computational chemistry workflows:
```python
class CalculationSession:
    def __init__(self):
        self.current_molecule = None
        self.calculation_history = []

    async def handle_tool_call(self, method, params):
        if method == "chemistry/optimize_geometry":
            if not self.current_molecule:
                raise NoMoleculeError
            result = await optimize_geometry(self.current_molecule)
            self.calculation_history.append(result)
            return result
```

This low-level approach provides maximum flexibility while adhering to MCP standards, suitable for integrating with diverse computational chemistry backends.