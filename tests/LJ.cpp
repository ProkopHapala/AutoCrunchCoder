#include <cmath>
#include <vector>

double lennard_jones_potential(double r, double E0, double R0, double& dE_dr) {
    double inv_r = 1.0 / r;
    double u = E0 * inv_r;
    double u2 = inv_r * inv_r;
    double u6 = u2 * u2 * u2;
    double u12 = u6 * u6;
    double E = E0 *        ( u12 - 2* u6 );
    dE_dr    = E0 * 12.0 * ( u12 -    u6 ) * inv_r;
    return E;
}

template <double (*PotentialFunc)(double, double, double, double&)>
void evaluatePotentialAndForce(const double* points, double* potentials, double* forces, size_t n, double epsilon, double sigma) {
    for (size_t i = 0; i < n; ++i) {
        double r = points[i];
        double dE_dr;
        potentials[i] = PotentialFunc(r, epsilon, sigma, dE_dr);
        forces[i] = dE_dr;
    }
}

// Specialization for Lennard-Jones potential
void evaluateLJPotentialAndForce(const double* points, double* potentials, double* forces, size_t n, double epsilon, double sigma) {
    evaluatePotentialAndForce<lennard_jones_potential>(points, potentials, forces, n, epsilon, sigma);
}

// Coulomb potential function
double coulomb_potential(double r, double q1, double q2, double& dE_dr) {
    double k = 8.99e9; // Coulomb constant in N m^2 C^-2
    double E = k * q1 * q2 / r;
    dE_dr = -E / r;
    return E;
}

// Specialization for Coulomb potential
void evaluateCoulombPotentialAndForce(const double* points, double* potentials, double* forces, size_t n, double q1, double q2) {
    evaluatePotentialAndForce<coulomb_potential>(points, potentials, forces, n, q1, q2);
}
