#include <cmath>

double lennard_jones_potential(double r, double epsilon, double sigma, double& dE_dr) {
    double inv_r = sigma / r;
    double inv_r2 = inv_r * inv_r;
    double inv_r6 = inv_r2 * inv_r2 * inv_r2;
    double inv_r12 = inv_r6 * inv_r6;
    double E = 4.0 * epsilon * (inv_r12 - inv_r6);
    
    // Compute the force (dE/dr)
    dE_dr = 4.0 * epsilon * (12.0 * inv_r12 * inv_r - 6.0 * inv_r6 * inv_r) / r;
    
    return E;
}
