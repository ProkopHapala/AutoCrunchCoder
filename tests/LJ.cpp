#include <cmath>
#include <vector>

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

template <double (*PotentialFunc)(double, double, double, double&)>
void evaluatePotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces, double epsilon, double sigma) {
    for (size_t i = 0; i < points.size(); ++i) {
        double r = points[i];
        double dE_dr;
        potentials[i] = PotentialFunc(r, epsilon, sigma, dE_dr);
        forces[i] = dE_dr;
    }
}

// Specialization for Lennard-Jones potential
void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces, double epsilon, double sigma) {
    evaluatePotentialAndForce<lennard_jones_potential>(points, potentials, forces, epsilon, sigma);
}
