```C++
#include <cmath>
#include <vector>

struct Vec3d {
    double x, y, z;
};

double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const Vec3d* REQ) {
    double E = 0.0;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = apos[i].x - apos[j].x;
            double dy = apos[i].y - apos[j].y;
            double dz = apos[i].z - apos[j].z;
            double r2 = dx * dx + dy * dy + dz * dz;
            if (r2 < 1e-6) continue; // avoid division by zero and singularity in potential

            double R0ij = REQ[i].x + REQ[j].x;
            double E0ij = REQ[i].y * REQ[j].y;
            double Qij = REQ[i].z * REQ[j].z;

            double u2 = R0ij * R0ij / r2;
            double u6 = u2 * u2 * u2;
            double u12 = u6 * u6;

            E += 4.0 * E0ij * (u12 - u6) + Qij / std::sqrt(r2);

            double force_factor = 4.0 * E0ij * (-12.0 * u12 + 6.0 * u6) / r2 + Qij / (r2 * std::sqrt(r2));
            fapos[i].x += force_factor * dx;
            fapos[i].y += force_factor * dy;
            fapos[i].z += force_factor * dz;
            fapos[j].x -= force_factor * dx;
            fapos[j].y -= force_factor * dy;
            fapos[j].z -= force_factor * dz;
        }
    }
    return E;
}
```