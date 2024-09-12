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
            Vec3d r = apos[i] - apos[j];
            double r2 = r.x * r.x + r.y * r.y + r.z * r.z;
            double R0ij = REQ[i].R0 + REQ[j].R0;
            double E0ij = REQ[i].E0 * REQ[j].E0;
            double Qij = REQ[i].Q * REQ[j].Q;
            double u = R0ij / r2;
            double f = 4.0 * u * u * u - 4.0 * u;
            E += (f + Qij / r2) / pow(r2, 3);
            Vec3d fij = r * f;
            fapos[i] += fij;
            fapos[j] -= fij;
        }
    }
    return E;
}
```