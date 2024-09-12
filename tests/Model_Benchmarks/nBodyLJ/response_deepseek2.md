 To evaluate the energy and forces for an n-body system using the Lennard-Jones (LJ) plus Coulomb potential, we need to compute both the LJ potential and the Coulomb potential between each pair of particles. The LJ potential is given by:

\[ V_{LJ}(r) = 4E_0 \left( \left(\frac{R_0}{r}\right)^{12} - \left(\frac{R_0}{r}\right)^6 \right) \]

And the Coulomb potential (Coulomb's Law) is:

\[ V_{Coulomb}(r) = \frac{Q_i Q_j}{4\pi \epsilon_0 \epsilon_r r} \]

Here, \( R_0 \) is the equilibrium distance, \( E_0 \) is the energy at equilibrium distance, and \( Q_i \) and \( Q_j \) are the charges of particles i and j. The function should return the total energy and update the force array for each particle.

Let's implement this in C++:

```C++
#include <cmath>

struct Vec3d {
    double x, y, z;
};

double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const double* REQ) {
    double E = 0.0; // Total energy

    for (int i = 0; i < n; ++i) {
        fapos[i].x = fapos[i].y = fapos[i].z = 0.0; // Initialize forces to zero
    }

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = apos[i].x - apos[j].x;
            double dy = apos[i].y - apos[j].y;
            double dz = apos[i].z - apos[j].z;
            double r2 = dx * dx + dy * dy + dz * dz;
            double r = sqrt(r2);

            // Precalculate R0 and E0 for this pair of particles
            double R0ij = REQ[0] + REQ[0]; // Assuming symmetric, so R0ij = R0i + R0j
            double E0ij = REQ[1] * REQ[1]; // E0ij = E0i * E0j
            double Qij = REQ[2] * REQ[2]; // Qij = Qi * Qj

            if (r > 0) {
                double u = R0ij / r;
                double u6 = u * u * u * u * u * u;
                double u12 = u6 * u6;
                double LJ_potential = 4.0 * E0ij * (u12 - u6);
                double Coulomb_potential = Qij / r;

                // Update energy
                E += LJ_potential + Coulomb_potential;

                // Calculate forces
                double force_magnitude = -(24.0 * E0ij * (2.0 * u12 - u6) / (r2 * r)) + (-Qij / (r2 * r));
                fapos[i].x += force_magnitude * dx;
                fapos[i].y += force_magnitude * dy;
                fapos[i].z += force_magnitude * dz;

                fapos[j].x -= force_magnitude * dx;
                fapos[j].y -= force_magnitude * dy;
                fapos[j].z -= force_magnitude * dz;
            }
        }
    }

    return E;
}
```

### Explanation:
1. **Initialization**: We initialize the total energy `E` to zero and set all forces in `fapos` to zero.
2. **Nested Loops**: We use nested loops to iterate over each pair of particles (i, j) where \( i < j \) to avoid double counting pairs.
3. **Distance Calculation**: For each pair, we calculate the distance \( r \) between particles using the Euclidean distance formula.
4. **Precalculation**: We precalculate `R0ij`, `E0ij`, and `Qij` for efficiency.
5. **Potential Calculation**: We compute the LJ potential and Coulomb potential for the given distance \( r \).
6. **Energy Update**: We add the computed potentials to the total energy `E`.
7. **Force Calculation**: We calculate the force magnitude using derivatives of the LJ and Coulomb potentials and update the forces on each particle accordingly.
8. **Return Energy**: Finally, we return the total energy `E`.

This implementation ensures that the function is efficient and handles all edge cases by checking for non-zero distances to avoid division by zero errors.