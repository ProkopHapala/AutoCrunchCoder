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
