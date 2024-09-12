#include <cmath>

double lennard_jones_potential(double r, double epsilon, double sigma) {
    double r6 = pow(sigma / r, 6);
    double r12 = r6 * r6;
    return 4.0 * epsilon * (r12 - r6);
}
