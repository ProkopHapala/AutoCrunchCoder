#!/usr/bin/env python3

"""
Example demonstrating the use of Maxima CAS integration for computing overlap integrals of Slater orbitals.
This example shows how to:
1. Set up Maxima expressions for Slater-type orbitals
2. Compute their overlap integrals in cylindrical coordinates
3. Handle symbolic integration with assumptions
"""

from pyCruncher2.scientific.cas.maxima import MaximaSession

def compute_slater_overlap(task_name: str, maxima_commands: str):
    """Run a Maxima computation for Slater orbital overlap integrals."""
    print(f"\n=== Computing {task_name} ===")
    
    # Initialize Maxima session with display2d disabled for cleaner output
    session = MaximaSession()
    session.execute("display2d: false$")
    
    # Run the integration task
    result = session.execute(maxima_commands)
    print(result)
    
    return result

def main():
    # Task 1: Cartesian coordinates integration
    task1 = """; 
    assume(a>0,b>0,x0>0);
    slater(x0, a):= exp(-a*((x-x0)^2 + y^2 + z^2))/((x-x0)^2 + y^2 + z^2);
    ss: slater(0.0,a)*slater(x0,b);
    ss: ratsimp(expand(ss));
    Syz: integrate(integrate(ss, y, -inf, inf), z, -inf, inf);
    S: integral_x: integrate(integral_yz, x, -inf, inf); 
    """
    compute_slater_overlap("Cartesian Integration", task1)

    # Task 2: Cylindrical coordinates with different exponents
    task2 = """; 
    assume(a>0,b>0,x0>0);
    ss: exp(-a*( x^2 + r^2))/( x^2 + r^2) * exp(-b*((x-x0)^2 + r^2))/((x-x0)^2 + r^2) * r;
    ss: ratsimp(expand(ss));
    Syz: integrate(ss, r, 0, inf)*2*%pi;
    S: integral_x: integrate(integral_yz, x, -inf, inf); 
    """
    compute_slater_overlap("Cylindrical Integration (Different Exponents)", task2)

    # Task 3: Cylindrical coordinates with same exponents
    task3 = """; 
    assume(a>0,b>0,x0>0);
    ss: exp(-a*( x^2 + r^2))/( x^2 + r^2) * exp(-a*((x-x0)^2 + r^2))/((x-x0)^2 + r^2) * r;
    ss: ratsimp(expand(ss));
    Syz: integrate(ss, r, 0, inf)*2*%pi;
    S: integral_x: integrate(integral_yz, x, -inf, inf); 
    """
    compute_slater_overlap("Cylindrical Integration (Same Exponent)", task3)

if __name__ == "__main__":
    main()
