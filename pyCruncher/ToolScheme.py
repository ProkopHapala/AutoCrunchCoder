import inspect
from typing import Callable, Dict, Any, Optional
import re

type_mapping = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list
}

def parse_docstring(docstring: Optional[str]) -> Dict[str, str]:
    """
    Parse the docstring to extract the descriptions for the parameters and the overall function.
    Returns a dictionary with function description and parameter descriptions.
    """
    if not docstring:
        return {"description": "", "params": {}}
    
    lines = docstring.strip().splitlines()
    description_lines = []
    param_descs = {}
    
    # Regex to match docstring param lines like: `param_name: description`
    param_pattern = re.compile(r"(\w+)\s*:\s*(.*)")
    
    for line in lines:
        line = line.strip()
        param_match = param_pattern.match(line)
        
        if param_match:
            # Capture param description
            param_name, param_desc = param_match.groups()
            param_descs[param_name] = param_desc
        else:
            # Otherwise, add to the general function description
            description_lines.append(line)
    
    return {
        "description": " ".join(description_lines),  # Join description lines into one
        "params": param_descs
    }

def schema(function: Callable, bOnlyRequired: bool = False) -> Dict[str, Any]:  
    """
    Generate a function schema from a Python function signature, using the docstring
    to fill in descriptions for the function and its parameters.
    """
    sig = inspect.signature(function)
    
    # Parse the docstring
    doc = parse_docstring(function.__doc__)
    
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    for param_name, param in sig.parameters.items():
        bRequired = param.default == inspect.Parameter.empty

        if bOnlyRequired and not bRequired:
            continue

        # Assume types based on function defaults or hints
        param_type = "string"  # Default to string if no hint
        if param.annotation == int:
            param_type = "integer"
        elif param.annotation == float:
            param_type = "number"
        elif param.annotation == bool:
            param_type = "boolean"
        elif param.annotation == dict:
            param_type = "object"
        elif param.annotation == list:
            param_type = "array"

        # Use the docstring description for the parameter, if available
        param_description = doc["params"].get(param_name, f"{param_name} argument")

        parameters["properties"][param_name] = {
            "type": param_type,
            "description": param_description
        }
        
        if bRequired:
            parameters["required"].append(param_name)
        parameters["additionalProperties"] =  False
    fname = function.__name__
    tool = {
        "name": fname,
        "strict": True,
        "description": doc["description"] or f"Function {fname}",
        "parameters": parameters
    }
    return tool

def validate_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]):
    """
    Validate the arguments provided by the model against the function schema.
    """
    required_args = schema['parameters'].get('required',   [])
    properties    = schema['parameters'].get('properties', {})

    # Check if all required arguments are provided
    for required_arg in required_args:
        if required_arg not in arguments:
            raise ValueError(f"Missing required argument: {required_arg}")

    # Check types of provided arguments
    for arg_name, arg_value in arguments.items():
        expected_type = properties.get(arg_name, {}).get('type', 'string')
        if not check_type(arg_value, expected_type):
            raise TypeError(f"Argument {arg_name} expected to be of type {expected_type}, but got {type(arg_value).__name__}")

def check_type(value: Any, expected_type: str) -> bool:
    """
    Check if a value matches the expected type.
    """
    return isinstance(value, type_mapping.get(expected_type, str))
