```C++
#include <cmath>
#include <vector>

double evalLJ(int n, const Vec3d* apos, Vec3d* fapos, const Vec3d* REQ ) {
    double E = 0;
    for (int i = 0; i < n; i++) {
        for (int j = i+1; j < n; j++) {
            double r = apos[i].norm() + apos[j].norm();
            double R0ij = REQ[i].R0 + REQ[j].R0;
            double E0ij = REQ[i].E0 * REQ[j].E0;
            double Qij = REQ[i].Q * REQ[j].Q;
            double u = (R0ij / r);
            double f = 1.0 / (4.0 * M_PI * pow(u, 3.0));
            E += f * (E0ij - Qij*pow(u, 2.0) - Qij*pow(u, 4.0));
        }
    }
    return E;
}
```