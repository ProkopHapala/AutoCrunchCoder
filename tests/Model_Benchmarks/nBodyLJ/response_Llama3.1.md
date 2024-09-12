Here's an optimized implementation in C++ for evaluating energy and force for n-body system of particles using Lenard-Jones + Coulomb potential.

```cpp
#include <cmath>
#include <iostream>

// Structure to represent 3D vector
struct Vec3d {
    double x, y, z;
};

// Function to calculate distance between two points
double dist(const Vec3d& a, const Vec3d& b) {
    return std::sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y) + (a.z - b.z) * (a.z - b.z));
}

// Function to calculate energy and force for n-body system of particles using Lenard-Jones + Coulomb potential
double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const double* REQ) {
    double E = 0.0;
    double R0ij, E0ij, Qij;

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            // Calculate equilibrium distance and energy at equilibrium distance
            R0ij = REQ[i * 3] + REQ[j * 3];
            E0ij = REQ[i * 3 + 1] * REQ[j * 3 + 1];

            // Calculate product of charges
            Qij = REQ[i * 3 + 2] * REQ[j * 3 + 2];

            // Calculate distance between particles i and j
            double r = dist(apos[i], apos[j]);

            // Check for zero distance to avoid division by zero
            if (r == 0.0) {
                continue;
            }

            // Calculate u=(R0/r)
            double u = R0ij / r;

            // Pre-calculate powers of u efficiently
            double u2 = u * u, u3 = u2 * u, u6 = u2 * u2 * u2, u12 = u6 * u6;

            // Calculate Lenard-Jones potential and force
            double LJ_potential = E0ij * (u12 - 2.0 * u6);
            double LJ_force = -E0ij * (12.0 * u10 - 6.0 * u8) / r;

            // Calculate Coulomb potential and force
            double Coulomb_potential = Qij / r;
            double Coulomb_force = Qij / r2;

            // Update total energy and forces
            E += LJ_potential + Coulomb_potential;
            fapos[i].x -= (Coulomb_force * (apos[j].x - apos[i].x) + LJ_force * (apos[j].x - apos[i].x)) / r;
            fapos[i].y -= (Coulomb_force * (apos[j].y - apos[i].y) + LJ_force * (apos[j].y - apos[i].y)) / r;
            fapos[i].z -= (Coulomb_force * (apos[j].z - apos[i].z) + LJ_force * (apos[j].z - apos[i].z)) / r;

            // Update forces for particle j
            fapos[j].x += Coulomb_force * (apos[i].x - apos[j].x) + LJ_force * (apos[i].x - apos[j].x);
            fapos[j].y += Coulomb_force * (apos[i].y - apos[j].y) + LJ_force * (apos[i].y - apos[j].y);
            fapos[j].z += Coulomb_force * (apos[i].z - apos[j].z) + LJ_force * (apos[i].z - apos[j].z);
        }
    }

    return E;
}

int main() {
    int n = 10; // Number of particles
    Vec3d apos[n]; // Positions of particles
    Vec3d fapos[n]; // Forces on particles
    double REQ[30]; // Parameters

    // Initialize positions, forces and parameters
    for (int i = 0; i < n; ++i) {
        apos[i].x = rand() / static_cast<double>(RAND_MAX);
        apos[i].y = rand() / static_cast<double>(RAND_MAX);
        apos[i].z = rand() / static_cast<double>(RAND_MAX);

        fapos[i].x = 0.0;
        fapos[i].y = 0.0;
        fapos[i].z = 0.0;

        REQ[i * 3] = rand() / static_cast<double>(RAND_MAX);
        REQ[i * 3 + 1] = rand() / static_cast<double>(RAND_MAX);
        REQ[i * 3 + 2] = rand() / static_cast<double>(RAND_MAX);
    }

    double E = evalLJ(n, apos, fapos, REQ);

    std::cout << "Total energy: " << E << std::endl;

    return 0;
}
```

This code calculates the total energy and forces for an n-body system of particles using Lenard-Jones + Coulomb potential. It uses pre-calculation of powers to efficiently evaluate the Lenard-Jones potential and force.

Note that this is a simplified example, in real-world applications you would need to consider more complex interactions between particles, such as angular momentum conservation, and also optimize the code for performance on large systems.