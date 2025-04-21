from fastmcp import Context, FastMCP  # use fastmcp package import to support run params

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
    # Launch SSE server on port 8000 with info logging
    print("Starting ChemistryMCP SSE server on http://0.0.0.0:8000/sse …")
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
