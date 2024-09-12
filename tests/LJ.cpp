#include <cmath>
#include <vector>


#define COULOMB_CONST      14.3996448915  // [eV A]

inline double getLJ(double r, double& dE_dr, double E0, double R0 ){
    double inv_r = 1.0 / r;
    double u = E0 * inv_r;
    double u2 = inv_r * inv_r;
    double u6 = u2 * u2 * u2;
    double u12 = u6 * u6;
    double E = E0 *        ( u12 - 2* u6 );
    dE_dr    = E0 * 12.0 * ( u12 -    u6 ) * inv_r;
    return E;
}

// Coulomb potential function
inline double getCoulomb(double r, double& dE_dr, double qq ){
    double inv_r = 1.0 / r;
    double E = COULOMB_CONST * qq * inv_r;
    dE_dr = -E / r;
    return E;
}

// Combined Lennard-Jones and Coulomb potential function
inline double getLJQ(double r, double& dE_dr, double E0, double R0, double qq) {
    double inv_r = 1.0 / r;
    double u = E0 * inv_r;
    double u2 = inv_r * inv_r;
    double u6 = u2 * u2 * u2;
    double u12 = u6 * u6;
    double E_lj = E0 * (u12 - 2 * u6);
    double dE_dr_lj = E0 * 12.0 * (u12 - u6) * inv_r;

    double E_coul = COULOMB_CONST * qq * inv_r;
    double dE_dr_coul = -E_coul * inv_r;

    dE_dr = dE_dr_lj + dE_dr_coul;
    return E_lj + E_coul;
}

template<typename Func>
void evalRadialPotential( int npar, int n, const double* rs, double* Es, double* Fs, double* params, Func func ) {
    for (int i = 0; i < n; ++i) {
        const double r   = rs[i];
        const double par = params + i*npar;
        double dE_dr;
        Es[i] = func(r, dE_dr, par );
        Fs[i] = dE_dr;
    }
}

// Specialization for Lennard-Jones potential
void evaluateLJ( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=2; // 2 parameters: E0 and R0
    evalRadialPotential( npar, n, rs, Es, Fs, params, [&](double r, double& dE_dr, double* pars ){ return getLJ( r, dE_dr, pars[0], pars[1] ); } );
}

// Specialization for Coulomb potential
void evaluateCoulombPotentialAndForce( int n, const double* rs, double* Es, double* Fs, double* params ){
    int npar=1; // 1 parameter: qq
    evalRadialPotential( npar, n, rs, Es, Fs, params, [&](double r, double& dE_dr, double* pars ){ return getCoulomb( r, dE_dr, pars[0] ); } );
}

// Specialization for combined Lennard-Jones and Coulomb potential
void evaluateLJQ( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=3; // 3 parameters: E0, R0, and qq
    evalRadialPotential( npar, n, rs, Es, Fs, params, [&](double r, double& dE_dr, double* pars ){ return getLJQ( r, dE_dr, pars[0], pars[1], pars[2] ); } );
}
