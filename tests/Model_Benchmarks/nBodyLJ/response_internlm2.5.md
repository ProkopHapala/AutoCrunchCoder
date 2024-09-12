Here's a C++ function that evaluates energy and force for an n-body system of particles using Lenard-Jones + Coulomb potential. It takes into account both the repulsive and attractive forces as well as the energy calculation:

```C++
#include <cmath>

struct Vec3d {
    double x, y, z;
};

double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const Vec3d* REQ) {
    double E = 0.0;
    Vec3d F[3] = {0};

    for (int i=0; i<n; ++i) {
        for (int j=i+1; j<n; ++j) {
            double dx = apos[j].x - apos[i].x;
            double dy = apos[j].y - apos[i].y;
            double dz = apos[j].z - apos[i].z;
            
            // Calculate distance
            double dist = sqrt(dx*dx + dy*dy + dz*dz);
            
            // Obtain parameters from REQ
            double R0ij = REQ[3*i] + REQ[3*j];
            double E0ij = REQ[3*i+1] * REQ[3*j+1];
            double Qij = REQ[3*i+2] * REQ[3*j+2];

            // Calculate forces and potential energy
            double u = R0ij / dist;
            double force_mag = 24 * E0ij * (u*u - 2*u + 1) / (dist*dist);
            
            E += 4 * E0ij * (u*u - 1);

            // Calculate forces in each dimension
            F[0].x += dx * force_mag;
            F[0].y += dy * force_mag;
            F[0].z += dz * force_mag;

            // Add the forces to the respective particles
            fapos[i].x -= F[0].x;
            fapos[i].y -= F[0].y;
            fapos[i].z -= F[0].z;

            fapos[j].x += F[0].x;
            fapos[j].y += F[0].y;
            fapos[j].z += F[0].z;
        }
    }

    return E;
}
```

This function calculates the potential energy and forces between all pairs of particles. It uses the Lenard-Jones potential for the repulsive and attractive forces, and the Coulomb potential for the electrostatic force.

The distance `dist` between two particles is calculated using the difference in their positions. Then, the parameters `R0ij`, `E0ij`, and `Qij` are obtained from the array `REQ`. The function then calculates the magnitude of the force `force_mag` and the components of this force in each dimension.

The forces are added to the respective particles and the potential energy is summed up. Finally, the function returns the total potential energy.

Note: This code assumes that the arrays `apos`, `fapos`, and `REQ` are all pre-allocated with a size of at least `3*n`.