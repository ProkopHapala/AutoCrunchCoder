#!/usr/bin/env python3

"""
Example demonstrating automatic derivative computation using Maxima CAS.
This example shows how to:
1. Define molecular interaction potentials
2. Compute their derivatives with respect to coordinates and parameters
3. Handle different potential forms (Lennard-Jones, Coulomb)
"""

from pyCruncher2.scientific.cas.maxima import get_derivs

def compute_potential_derivatives(name: str, formula: str, dofs: list[str], params: list[str]):
    """Compute derivatives of a potential energy formula."""
    print(f"\n=== Computing derivatives for {name} potential ===")
    print(f"Formula: {formula}")
    print(f"DOFs: {dofs}")
    print(f"Parameters: {params}")
    
    derivatives = get_derivs(formula, dofs + params)
    print("\nDerivatives:")
    print(derivatives)
    
    return derivatives

def main():
    # Example 1: Basic Lennard-Jones + Coulomb potential
    formula1 = "A/r^12 - B/r^6 + Q/r"
    dofs1 = ["r"]
    params1 = ["A", "B", "Q"]
    compute_potential_derivatives("Basic L-J + Coulomb", formula1, dofs1, params1)
    
    # Example 2: Standard Lennard-Jones form with Coulomb
    formula2 = "E0*((R0/r)^12 - 2*(R0/r)^6) + Q/r"
    dofs2 = ["r"]
    params2 = ["E0", "R0", "Q"]
    compute_potential_derivatives("Standard L-J + Coulomb", formula2, dofs2, params2)

if __name__ == "__main__":
    main()
