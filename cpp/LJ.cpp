#include <vector>
#include <cmath>

// Constants from tests/response_simplify.md
const double e0 = 1.0; // Example value, adjust as needed
const double r0 = 1.0; // Example value, adjust as needed
const double Kcoul = 1.0; // Example value, adjust as needed
const double qq = 1.0; // Example value, adjust as needed

// Function to evaluate Lenard-Jones potential for a single distance r
double getLJ(double r) {
    double e0r012 = e0 * std::pow(r0, 12);
    double inv_r = 1.0 / r;
    double inv_r6 = std::pow(inv_r, 6);
    double inv_r12 = std::pow(inv_r, 12);
    double E = e0r012 * (inv_r12 - 2 * inv_r6) + (Kcoul * qq) * inv_r;
    return E;
}

// Function to calculate Lennard-Jones force between two particles
double getLJForce(double r) {
    double e0r06 = e0 * std::pow(r0, 6);
    double inv_r = 1.0 / r;
    double inv_r7 = std::pow(inv_r, 7);
    double inv_r13 = std::pow(inv_r, 13);
    double F = 12 * e0r06 * (inv_r7 - inv_r13);
    return F;
}

// Function to calculate Lennard-Jones potential and its derivative
double LJ(double r, double R0, double E0, double& dE_dr) {
    double inv_r = 1.0 / r;
    double inv_r6 = std::pow(inv_r, 6);
    double inv_r12 = std::pow(inv_r, 12);
    double E = E0 * (std::pow(R0 / r, 12) - 2 * std::pow(R0 / r, 6));
    dE_dr = -12 * E0 * (std::pow(R0 / r, 12) / r - std::pow(R0 / r, 6) / r);
    return E;
}

// Template function to evaluate any potential and force for an array of points
template <double (*PotentialFunc)(double)>
void evaluatePotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    for (size_t i = 0; i < points.size(); ++i) {
        double r = points[i];
        potentials[i] = PotentialFunc(r);
        forces[i] = getLJForce(r) + ((Kcoul * qq) / (r * r));
    }
}

// Specialize the template function with getLJ as the template parameter
extern "C" void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    evaluatePotentialAndForce<getLJ>(points, potentials, forces);
}

extern "C" void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    evaluatePotentialAndForce<getLJ>(points, potentials, forces);
}
#include <vector>
#include <cmath>

// Constants from tests/response_simplify.md
const double e0 = 1.0; // Example value, adjust as needed
const double r0 = 1.0; // Example value, adjust as needed
const double Kcoul = 1.0; // Example value, adjust as needed
const double qq = 1.0; // Example value, adjust as needed

// Function to evaluate Lenard-Jones potential for a single distance r
double getLJ(double r) {
    double e0r012 = e0 * std::pow(r0, 12);
    double inv_r = 1.0 / r;
    double inv_r6 = std::pow(inv_r, 6);
    double inv_r12 = std::pow(inv_r, 12);
    double E = e0r012 * (inv_r12 - 2 * inv_r6) + (Kcoul * qq) * inv_r;
    return E;
}

// Template function to evaluate any potential and force for an array of points
template <double (*PotentialFunc)(double)>
void evaluatePotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    for (size_t i = 0; i < points.size(); ++i) {
        double r = points[i];
        potentials[i] = PotentialFunc(r);
        forces[i] = -((12 * e0 * std::pow(r0, 6) * std::pow(1.0 / r, 7)) - (12 * e0r012 * std::pow(1.0 / r, 13))) + ((Kcoul * qq) / (r * r));
    }
}

// Specialize the template function with getLJ as the template parameter
extern "C" void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    evaluatePotentialAndForce<getLJ>(points, potentials, forces);
}
#include <vector>
#include <cmath>

// Constants from tests/response_simplify.md
const double e0 = 1.0; // Example value, adjust as needed
const double r0 = 1.0; // Example value, adjust as needed
const double Kcoul = 1.0; // Example value, adjust as needed
const double qq = 1.0; // Example value, adjust as needed

// Function to evaluate Lenard-Jones potential for a single distance r
double getLJ(double r) {
    double e0r012 = e0 * std::pow(r0, 12);
    double inv_r = 1.0 / r;
    double inv_r6 = std::pow(inv_r, 6);
    double inv_r12 = std::pow(inv_r, 12);
    double E = e0r012 * (inv_r12 - 2 * inv_r6) + (Kcoul * qq) * inv_r;
    return E;
}

// Template function to evaluate any potential and force for an array of points
template <double (*PotentialFunc)(double)>
void evaluatePotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    for (size_t i = 0; i < points.size(); ++i) {
        double r = points[i];
        potentials[i] = PotentialFunc(r);
        forces[i] = -((12 * e0 * std::pow(r0, 6) * std::pow(1.0 / r, 7)) - (12 * e0r012 * std::pow(1.0 / r, 13))) + ((Kcoul * qq) / (r * r));
    }
}

// Specialize the template function with getLJ as the template parameter
extern "C" void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    evaluatePotentialAndForce<getLJ>(points, potentials, forces);
}
#include <vector>
#include <cmath>

// Constants from tests/response_simplify.md
const double e0 = 1.0; // Example value, adjust as needed
const double r0 = 1.0; // Example value, adjust as needed
const double Kcoul = 1.0; // Example value, adjust as needed
const double qq = 1.0; // Example value, adjust as needed

// Function to evaluate Lenard-Jones potential for a single distance r
double getLJ(double r) {
    double e0r012 = e0 * std::pow(r0, 12);
    double inv_r = 1.0 / r;
    double inv_r6 = std::pow(inv_r, 6);
    double inv_r12 = std::pow(inv_r, 12);
    double E = e0r012 * (inv_r12 - 2 * inv_r6) + (Kcoul * qq) * inv_r;
    return E;
}

// Template function to evaluate any potential and force for an array of points
template <double (*PotentialFunc)(double)>
void evaluatePotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    for (size_t i = 0; i < points.size(); ++i) {
        double r = points[i];
        potentials[i] = PotentialFunc(r);
        forces[i] = -((12 * e0 * std::pow(r0, 6) * std::pow(1.0 / r, 7)) - (12 * e0r012 * std::pow(1.0 / r, 13))) + ((Kcoul * qq) / (r * r));
    }
}

// Specialize the template function with getLJ as the template parameter
extern "C" void evaluateLJPotentialAndForce(const std::vector<double>& points, std::vector<double>& potentials, std::vector<double>& forces) {
    evaluatePotentialAndForce<getLJ>(points, potentials, forces);
}
