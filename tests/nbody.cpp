#include <math.h>
#include "Vec3.h"
#include "Vec4.h"

#include <cstdio>

//double nbody(int n, Vec3d *pos, Vec3d *forces ){}

#define COULOMB_CONST      14.3996448915  

Vec4d interact_coulomb( const Vec3d d, const Vec4d Pi, const Vec4d Pj ){
    const double  ir2 = d.norm2() + 1e-32;
    const double  ir  = sqrt(ir2);
    const double qq   = Pi.z*Pj.z;
    const double E    = COULOMB_CONST*qq*ir;
    //printf("interact_coulomb() r=%g qq=%g Ei=%g \n", d.norm(), qq, E );
    return Vec4d( d*(E*ir2), E );
}

template<typename Func>
double nbody( const int n, const Vec3d *pos, const Vec4d* params, Vec3d *forces, Func pair_interaction ){
    double E=0;
    for(int i=0; i<n; i++){
        const Vec3d pi   = pos[i];
        const Vec4d pari = params[i];
        Vec4d       fe   = Vec4dZero;
        for(int j=0; j<n; j++){
            if(i==j) continue;
            fe += pair_interaction( pos[j]-pi, pari, params[j] );
            //printf("nbody[%i,%i] Ei=%g \n", i, j, fe.e );
        }
        forces[i] = fe.f;
        E        += fe.e;
    }
    return E;
}

__attribute__((hot)) 
double nbody_coulomb( int n, const Vec3d *pos, const Vec4d* params, Vec3d *forces ){
    return nbody( n, pos, params, forces, interact_coulomb );
}

extern "C" {
    double nbody_coulomb_c( int n, double* pos, double* params, double *forces ){
        return nbody_coulomb( n, (Vec3d*)pos, (Vec4d*)params, (Vec3d*)forces );
    }
}