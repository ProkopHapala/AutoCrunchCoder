#include <cmath>
#include <vector>
#include "Vec3.h"

#define COULOMB_CONST      14.3996448915  // [eV A]

// -------- Coulomb potential 

// Coulomb potential - evaluation of force-field 
inline double getCoulomb(double r, double& dE_r, double qq ){
    double inv_r = 1.0 / r;
    double E = COULOMB_CONST * qq * inv_r;
    dE_r = -E / r;
    return E;
}

// Coulomb potential - derivatives according to perameters (for fitting parameters)
inline double varCoulomb(double r, double& dE_qq, double qq ){
    double inv_r = 1.0 / r;
    dE_qq = COULOMB_CONST * inv_r;
    return dE_qq * qq;
}

// -------- Lennard-Jones potential

// Lennard-Jones potential  - evaluation of force-field 
inline double getLJ(double r, double& dE_r, double E0, double R0 ){
    double inv_r = 1.0 / r;
    double u   = E0 * inv_r;
    double u2  = inv_r * inv_r;
    double u6  = u2 * u2 * u2;
    double u12 = u6 * u6;
    double E   = E0 *        ( u12 - 2* u6 );
    dE_r       = E0 * 12.0 * ( u12 -    u6 ) * inv_r;
    return E;
}

// Lennard-Jones potential  - derivatives according to parameters (for fitting parameters)
inline double varLJ(double r, double R0, double E0,  double& dE_E0, double& dE_R0 ){                                                                                                                                                                                                                                                                                                                                                         
    double inv_r = 1.0 / r;                                                                                                                                                                                                                                                                                                                                                                                                                   
    double u     = E0 * inv_r;                                                                                                                                                                                                                                                                                                                                                                                                                    
    double u2    = inv_r * inv_r;                                                                                                                                                                                                                                                                                                                                                                                                                
    double u6    = u2 * u2 * u2;                                                                                                                                                                                                                                                                                                                                                                                                                 
    double u12   = u6 * u6;                                                                                                                                                                                                                                                                                                                                                                                                                     
    dE_E0        =      ( u12 - 2* u6 );   
    double E     = E0 * dE_E0;                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
    dE_R0        = 12.0 * E0 * (u12 - u6) / R0;                                                                                                                                                                                                                                                                                                                                                                                    
    return E;                                                                                                                                                                                                                                                                                                                                                                                                                                 
}        

// -------- LennardJones+Coulomb potential

// Energy and Force for LennardJones+Coulomb potential 
inline double getLJQ(double r, double& dE_r, double R0, double E0, double qq ){
    double inv_r = 1.0 / r;
    double u     = E0 * inv_r;
    double u2    = inv_r * inv_r;
    double u6    = u2 * u2 * u2;
    double u12   = u6 * u6;
    double E_lj  = E0 * (u12 - 2 * u6);
    double dE_r_lj = E0 * 12.0 * (u12 - u6) * inv_r;

    double E_coul    = COULOMB_CONST * qq * inv_r;
    double dE_r_coul = -E_coul * inv_r;

    dE_r = dE_r_lj + dE_r_coul;
    return E_lj + E_coul;
}

// Variational derivatives for LonearJones+Coulomb potential
inline double varLJQ(double r, double R0, double E0,  double qq, double& dE_R0, double& dE_E0, double& dE_qq ){
    double inv_r = 1.0 / r;
    double u     = E0 * inv_r;
    double u2    = inv_r * inv_r;
    double u6    = u2 * u2 * u2;
    double u12   = u6 * u6;
    double E_lj  = E0 * (u12 - 2 * u6);
    double dE_dr_lj = E0 * 12.0 * (u12 - u6) * inv_r;

    double E_coul = COULOMB_CONST * qq * inv_r;
    double dE_dr_coul = -E_coul * inv_r;

    dE_E0 = (u12 - 2 * u6);
    dE_R0 = 12.0 * E0 * (u12 - u6) / R0;
    dE_qq = COULOMB_CONST * inv_r;
    return E_lj + E_coul;
}

inline double _varLJQ(double r, const double* par,  double* dpar ){  return varLJQ( r,       par[0], par[1], par[2],  dpar[0], dpar[1], dpar[2]  ); };
inline double _getLJQ(double r,       double& dE_r, double*  par ){  return getLJQ( r, dE_r, par[0], par[1], par[2]  ); };

inline void mix_LJQ( const double* pi, const double* pj, double* pij ){
    pij[0] = pi[0] + pj[0];
    pij[1] = pi[1] * pj[1];
    pij[2] = pi[2] * pj[2];
}

inline void dmix_LJQ( const double* pi, const double* pj, const double* dpij, double* dpi ){
    dpi[0] = dpij[0];
    dpi[1] = dpij[1] * pj[1];
    dpi[2] = dpij[2] * pj[2];
}

// -------- Morse potential

inline double getMorse(double r, double& dE_r, double R0, double E0, double k ){
    double e = std::exp(-k * (r - R0));
    double E = E0 * ( e*e - 2*e );
    dE_r  = 2 * E0 * k * ( e*e - e );
    return E;
}


inline double varMorse(double r, double R0, double E0, double k,  double& dE_R0, double& dE_E0, double& dE_k ){
    double e = std::exp(-k * (r - R0));
    dE_E0 = (e*e - 2*e);
    dE_k  = 2*E0 * (e*e - e) * (r - R0);
    return E0*dE_E0;
}

// -------- Morse+Coulomb potential

// Energy and Force for Morse+Coulomb potential
inline double getMorseQ(double r, double& dE_r, double R0, double E0, double qq, double k ){
    double e = std::exp(-k * (r - R0));
    double e2 = e*e;
    double E_morse     =    E0 *     (e2 - 2*e);
    double dE_r_morse = 2 * E0 * k * (e2 -   e);

    double inv_r = 1.0 / r;
    double E_coul = COULOMB_CONST * qq * inv_r;
    double dE_r_coul = -E_coul * inv_r;

    dE_r = dE_r_morse + dE_r_coul;
    return E_morse + E_coul;
}

// Variational derivatives for Morse+Coulomb potential
inline double varMorseQ(double r, double R0, double E0, double qq, double k,  double& dE_R0,  double& dE_E0, double& dE_qq, double& dE_k ) {
    double e = std::exp(-k * (r - R0));
    double e2 = e*e;
    double inv_r = 1.0 / r;
    dE_E0 = (e*e - 2*e);
    dE_R0 = -2 * E0 * k * (e2 - e);
    dE_k  =  2 * E0 *     (e2 - e) * (r - R0);
    dE_qq = COULOMB_CONST * inv_r;
    return E0*dE_E0 + qq*dE_qq;
}

inline double _varMorseQ(double r, const double* par,  double* dpar ){  return varMorseQ( r,         par[0], par[1], par[2], par[3],  dpar[0], dpar[1], dpar[2], dpar[3] ); };
inline double _getMorseQ(double r,       double& dE_r, double*  par ){  return getMorseQ( r, dE_r,   par[0], par[1], par[3], par[3]  ); };

inline void mix_varMorseQ( const double* pi, const double* pj, double* pij ){
    pij[0] = pi[0] + pj[0];
    pij[1] = pi[1] * pj[1];
    pij[2] = pi[2] * pj[2];
    pij[3] = (pi[3] + pj[3])*0.5;
}

inline void dmix_varMorseQ( const double* pi, const double* pj, const double* dpij, double* dpi ){
    dpi[0] = dpij[0];
    dpi[1] = dpij[1] * pj[1];
    dpi[2] = dpij[2] * pj[2];
    dpi[3] = dpij[3] * 0.5;
}



// =========== Template functions for calculation of variational derivatives of energy with respect to parameters ==========

template<
    typename FuncFF, 
    void(*mixPar )(const double*,const double*,double*),
    void(*dmixPar)(const double*,const double*,const double*,double*)
>
double getVarDerivs( int npar, int na1, const Vec3d* apos1, const double* pars1, int na2, const Vec3d* apos2, const double* pars2, double* dE_par1, FuncFF ff ){   //  , FuncMix mixPar, dFuncMix dmixPar ) {
    double  parij[na1*npar];
    double dparij[na1*npar];
    double E=0;
    for (int ia=0; ia<na1; ia++){
        const double* pari = pars1   + ia*npar;
        double*      dpari = dE_par1 + ia*npar;
        for (int ja=0; ja<na2; ja++){
            Vec3d d = apos1[ia] - apos2[ja];
            double r = d.norm();
            const double* parj = pars2   + ja*npar;
            mixPar( pari, parj, parij );
            E += ff(r, parij, dpari );
            dmixPar( pari, parj, dparij, dpari );
        }
    }
    return E;
}

// =========== Fitting Derivatives ==========

// Specialization for Lennard-Jones potential
double getVarDerivsLJQ( int na1, const Vec3d* apos1, const double* pars1, int na2, const Vec3d* apos2, const double* pars2, double* dE_par1 ){
    int npar=2; // 2 parameters: R0 E0
    //auto ff = [&](double r, const double* par, double* dpar ){  return varLJQ( r, par[0], par[1], par[2],  dpar[0], dpar[1], dpar[2]  ); };
    //return getVarDerivs< decltype(ff), mix_LJQ, dmix_LJQ >( npar, na1, apos1, pars1, na2, apos2, pars2, dE_par1, ff );
    return getVarDerivs< decltype(_varLJQ), mix_LJQ, dmix_LJQ >( npar, na1, apos1, pars1, na2, apos2, pars2, dE_par1, _varLJQ );
};

// Specialization for Lennard-Jones potential
double getVarDerivsMorseQ( int na1, const Vec3d* apos1, const double* pars1, int na2, const Vec3d* apos2, const double* pars2, double* dE_par1 ){
    int npar=2; // 2 parameters: R0 E0
    //auto ff = [&](double r, const double* par, double* dpar ){  return varMorseQ( r, par[0], par[1], par[2],par[3],  dpar[0], dpar[1], dpar[2], dpar[3]  ); };
    //return getVarDerivs< decltype(ff), mix_LJQ, dmix_LJQ >( npar, na1, apos1, pars1, na2, apos2, pars2, dE_par1, ff );
    return getVarDerivs< decltype(_varMorseQ), mix_LJQ, dmix_LJQ >( npar, na1, apos1, pars1, na2, apos2, pars2, dE_par1, _varMorseQ );
};


// =========== Template functions for evaluation of potentials at points ==========

template<typename Func>
void evalRadialPotential( int npar, int n, const double* rs, double* Es, double* Fs, const double* params, Func func ) {
    for (int i = 0; i < n; ++i) {
        const double r   = rs[i];
        const double* par = params + i*npar;
        double dE_dr;
        Es[i] = func(r, dE_dr, par );
        Fs[i] = dE_dr;
    }
}

// ========== Evaluation of potentials at points 

// Specialization for Lennard-Jones potential
void evaluateLJ( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=2; // 2 parameters: R0 E0
    evalRadialPotential( npar, n, rs, Es, Fs, params, 
        [&](double r, double& dE_dr, const double* pars ){ 
            return getLJ( r, dE_dr, pars[0], pars[1] ); 
        } 
    );
}

// Specialization for Coulomb potential
void evaluateCoulomb( int n, const double* rs, double* Es, double* Fs, double* params ){
    int npar=1; // 1 parameter: qq
    evalRadialPotential( npar, n, rs, Es, Fs, params, 
        [&](double r, double& dE_dr, const double* pars ){ 
            return getCoulomb( r, dE_dr, pars[0] ); 
        } 
    );
}

// Specialization for combined Lennard-Jones and Coulomb potential
void evaluateLJQ( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=3; // 3 parameters: E0, R0, qq
    evalRadialPotential( npar, n, rs, Es, Fs, params, 
    [&](double r, double& dE_dr, const double* pars ){ 
        return getLJQ( r, dE_dr, pars[0], pars[1], pars[2] ); 
    });
}

void evaluateMorse( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=3; // 3 parameters: R0, E0, k
    evalRadialPotential( npar, n, rs, Es, Fs, params, 
        [&](double r, double& dE_dr, const double* pars ){ 
            return getMorse( r, dE_dr, pars[0], pars[1], pars[2] ); 
        }
    );
}

void evaluateMorseQ( int n, const double* rs, double* Es, double* Fs, double* params ) {
    int npar=4; // 4 parameters: R0, E0, qq, k
    evalRadialPotential( npar, n, rs, Es, Fs, params, 
        [&](double r, double& dE_dr, const double* pars ){ 
            return getMorseQ( r, dE_dr, pars[0], pars[1], pars[2], pars[3] ); 
        }
    );
}




