/*

// ============= For automatic generation of interfaces

int nnode
int natom
int nvec = nnode+natom

//------- Dynamical

_RW float4*  apos      [ nSys* nvec ]
_RW float4*  aforce    [ nSys* nvec ]     
_RW float4*  avel      [ nSys* nvec ]    
_RW float4*  fneigh    [ nSys* nnode*2*4 ]

//------- parameters

_R  int4*    neighs    [ nSys* natom ]    
_R  int4*    bkNeighs  [ nSys* natom ]    
_R  int4*    neighCell [ nSys* natom ]    
_R  float4*  REQs     [ nSys* natom ]
_R  float4*  apars,    [ nSys* nnode ] 
_R  float4*  bLs,      [ nSys* nnode ] 
_R  float4*  bKs,      [ nSys* nnode ] 
_R  float4*  Ksp,      [ nSys* nnode ]
_R  float4*  Kpp,      [ nSys* nnode ]
_R  cl_Mat3* lvecs,    [ nSys ]
_R  cl_Mat3* ilvecs    [ nSys ]

_R float4*  apos_surf   [ natom_surf ]
_R float4*  aforce_surf [ natom_surf ]  

_R float4*  ps,         [ ndipol ]    
_R float4*  dipols,     [ ndipol ]

_RW image3d_t  FE_Paul[ ng.x, ng.y, ng.z ]
_RW image3d_t  FE_Lond[ ng.x, ng.y, ng.z ]
_RW image3d_t  FE_Coul[ ng.x, ng.y, ng.z ]

const float4   MDpars
const int4     nGrid
const cl_Mat3  dGrid
const float4   grid_p0 

*/


#define iGdbg 0
#define iSdbg 0

#pragma OPENCL EXTENSION cl_khr_fp64 : disable
//#pragma OPENCL FP_CONTRACT ON

// ======================================================================
// ======================================================================
//                           FUNCTIONS
// ======================================================================
// ======================================================================

//#pragma OPENCL EXTENSION cl_khr_3d_image_writes : enable

typedef struct __attribute__ ((packed)){
    float4 a;
    float4 b;
    float4 c;
} cl_Mat3;

#define  float4Zero  (float4){0.f,0.f,0.f,0.f}
#define  float3Zero  (float3){0.f,0.f,0.f}
#define  float2Zero  (float3){0.f,0.f,0.f}

#define R2SAFE          1e-4f
#define COULOMB_CONST   14.3996448915f       // [ eV*Ang/e^2 ]
#define const_kB        8.617333262145e-5f   // [ eV/K ]



inline float2 udiv_cmplx( float2 a, float2 b ){ return (float2){  a.x*b.x + a.y*b.y,  a.y*b.x - a.x*b.y }; }     // divison of unitary complex numbers (i.e. rotation backwards)
//inline void     udiv_cmplx(               const VEC& b ){                            T x_ =    x*b.x +   y*b.y;         y =    y*b.x -   x*b.y;       x=x_;  }

inline float3 rotMat ( float3 v, float3 a, float3 b, float3 c ){ return (float3)(dot(v,a),dot(v,b),dot(v,c)); }  // rotate vector v by matrix (a,b,c)
inline float3 rotMatT( float3 v, float3 a, float3 b, float3 c ){ return a*v.x + b*v.y + c*v.z; }                 // rotate vector v by matrix (a,b,c) transposed

//<<<file Forces.cl

// evaluate angular force and energy using cos(angle) formulation,    - faster, but not good for angles > 90 deg
inline float evalAngCos( const float4 hr1, const float4 hr2, float K, float c0, __private float3* f1, __private float3* f2 ){
    float  c = dot(hr1.xyz,hr2.xyz);
    float3 hf1,hf2;
    hf1 = hr2.xyz - hr1.xyz*c;
    hf2 = hr1.xyz - hr2.xyz*c;
    float c_   = c-c0;
    float E    = K*c_*c_;
    float fang = -K*c_*2;
    hf1 *= fang*hr1.w;
    hf2 *= fang*hr2.w;
    *f1=hf1;
    *f2=hf2;
    return E;
}

// evaluate angular force and energy using cos(angle/2) formulation - a bit slower, but not good for angles > 90 deg
inline float evalAngleCosHalf( const float4 hr1, const float4 hr2, const float2 cs0, float k, __private float3* f1, __private float3* f2 ){
    // This is much better angular function than evalAngleCos() with just a little higher computational cost ( 2x sqrt )
    // the main advantage is that it is quasi-harmonic beyond angles > 90 deg
    float3 h  = hr1.xyz + hr2.xyz;  // h = a+b
    float  c2 = dot(h,h)*0.25f;     // cos(a/2) = |ha+hb|  (after normalization)
    float  s2 = 1.f-c2 + 1e-7f;      // sin(a/2) = sqrt(1-cos(a/2)^2) ;  s^2 must be positive (otherwise we get NaNs)
    float2 cso = (float2){ sqrt(c2), sqrt(s2) }; // cso = cos(a/2) + i*sin(a/2)
    float2 cs = udiv_cmplx( cs0, cso );          // rotate back by equilibrium angle
    float  E         =  k*( 1 - cs.x );          // E = k*( 1 - cos(a/2) )  ; Do we need Energy? Just for debugging ?
    float  fr        = -k*(     cs.y );          // fr = k*( sin(a/2) )     ; force magnitude
    c2 *= -2.f;
    fr /=  4.f*cso.x*cso.y;   //    |h - 2*c2*a| =  1/(2*s*c) = 1/sin(a) 
    float  fr1    = fr*hr1.w; // magnitude of force on atom a
    float  fr2    = fr*hr2.w; // magnitude of force on atom b
    *f1 =  h*fr1  + hr1.xyz*(fr1*c2);  //fa = (h - 2*c2*a)*fr / ( la* |h - 2*c2*a| ); force on atom a
    *f2 =  h*fr2  + hr2.xyz*(fr2*c2);  //fb = (h - 2*c2*b)*fr / ( lb* |h - 2*c2*b| ); force on atom b
    return E;
}

// evaluate angular force and energy for pi-pi alignment interaction
inline float evalPiAling( const float3 h1, const float3 h2,  float K, __private float3* f1, __private float3* f2 ){  // interaction between two pi-bonds
    float  c = dot(h1,h2); // cos(a) (assumes that h1 and h2 are normalized)
    float3 hf1,hf2;        // working forces or direction vectors
    hf1 = h2 - h1*c;       // component of h2 perpendicular to h1
    hf2 = h1 - h2*c;       // component of h1 perpendicular to h2
    bool sign = c<0; if(sign) c=-c; // if angle is > 90 deg we need to flip the sign of force
    float E    = -K*c;     // energy is -K*cos(a)
    float fang =  K;       // force magnitude
    if(sign)fang=-fang;    // flip the sign of force if angle is > 90 deg
    hf1 *= fang;           // force on atom a
    hf2 *= fang;           // force on atom b
    *f1=hf1;
    *f2=hf2;
    return E;
}

// evaluate bond force and energy for harmonic bond stretching
inline float evalBond( float3 h, float dl, float k, __private float3* f ){
    float fr = dl*k;   // force magnitude
    *f = h * fr;       // force on atom a
    return fr*dl*0.5f;  // energy
}

// evaluate non-covalent interaction force and energy for Lennard-Jones (Q) and Coulomb interactions of charges (Q) and hydrogen bond correction (pseudo-charges H), damping R2damp is used to avoid singularity at r=0
inline float4 invR2( float3 dp ){
    const float ir2 = 1.f/(dot(dp,dp));
    const float E   = ir2;
    return  (float4){ dp*ir2*ir2, E };
}

inline float4 R2gauss( float3 dp ){
    const float r2 = dot(dp,dp);
    if(r2>1.0){ return (float4){0.f,0.f,0.f,0.f}; }
    float p = 1 - r2;
    return  (float4){ dp*p, p*p }; // dp*r2 = |dp|
}


// evaluate non-covalent interaction force and energy for Lennard-Jones (Q) and Coulomb interactions of charges (Q) and hydrogen bond correction (pseudo-charges H), damping R2damp is used to avoid singularity at r=0
inline float4 exp_r( float3 dp, float b ){
    const float r = length(dp);
    const float E = exp(-b*r);
    return  (float4){ dp*(E*b/r), E };
}

inline float4 exp_r_lin4( float3 dp, float b ){
    const float r2   = dot(dp,dp);
    const float Rc   = 5.f/b;
    if(r2>(Rc*Rc)){ return (float4){0.f,0.f,0.f,0.f}; }
    const float r    = sqrt(r2);
    const float y    = 1.f-(b*r/5.f);
    const float dy   = b;
    const float y2   = y*y;
    const float y4   = y2*y2;
    return  (float4){ dp*(y4*dy/r), y4*y  };
}

inline float4 exp_r_lin8( float3 dp, float b ){
    const float r2   = dot(dp,dp);
    const float Rc   = 9.f/b;
    if(r2>(Rc*Rc)){ return (float4){0.f,0.f,0.f,0.f}; }
    const float r    = sqrt(r2);
    const float y    = 1.f-(b*r/9.f);
    const float dy   = b;
    const float y2   = y*y;
    const float y4   = y2*y2;
    const float y8   = y4*y4;
    return  (float4){ dp*(y8*dy/r), y8*y  };
}

inline float4 exp_r_lin16( float3 dp, float b ){
    const float r2   = dot(dp,dp);
    const float Rc   = 17.f/b;
    if(r2>(Rc*Rc)){ return (float4){0.f,0.f,0.f,0.f}; }
    const float r    = sqrt(r2);
    const float y    = 1.f-(b*r/17.f);
    const float dy   = b;
    const float y2   = y*y;
    const float y4   = y2*y2;
    const float y8   = y4*y4;
    const float y16  = y8*y8;
    return  (float4){ dp*(y16*dy/r), y16*y  };
}

inline float4 exp_r_cub4( float3 dp, float4 cpoly, float Rc ){
    const float r2   = dot(dp,dp);
    if(r2>(Rc*Rc)){ return (float4){0.f,0.f,0.f,0.f}; }
    const float r    = sqrt(r2);
    const float y    = cpoly.x + r*( cpoly.y + r*(    cpoly.z + r*    cpoly.w)) ;
    const float dy   =               cpoly.y + r*(2.f*cpoly.z + r*3.f*cpoly.w)  ;
    const float y2   = y*y;
    const float y4   = y2*y2;
    return  (float4){ dp*(y4*-5.f*dy/r), y4*y  };
}

inline float4 getMorse( float3 dp,  float R0, float E0, float b ){
    float r = length( dp );
    float e = exp ( -b*(r-R0));
    float E = E0*        e*(e - 2.f); // Energy
    float F = E0*  2.f*b*e*(e - 1.f); // Force
    return  (float4){ dp*(F/r), E };
}

/**
 * @brief Morse potential using a linear approximation of the exponential term (n=5).
 * @param dp float3 distance vector between particles.
 * @param R0 float  Equilibrium distance for the potential minimum.
 * @param E0 float  Potential well depth (magnitude of energy at the minimum).
 * @param b  float  Exponential decay constant, controls the width of the well.
 * @return float4   Force vector in xyz, Energy in w.
 */
inline float4 getMorse_lin5( float3 dp, float R0, float E0, float b ){
    const float n = 5.f;
    const float r2 = dot(dp,dp);
    const float Rc = R0 + n/b;
    if (r2 > Rc*Rc) { return (float4)(0.f); }

    const float r_inv = rsqrt(r2);
    const float r     = r2 * r_inv;
    
    // Base of the power approximation
    const float y = 1.f - (b/n)*(r - R0);
    // The cutoff above handles r > Rc, where y would be negative.

    // p = y^5
    const float y2 = y*y;
    const float y4 = y2*y2;
    const float p  = y4*y;

    // Energy: E = E0 * (p^2 - 2p)
    const float E = E0 * p * (p - 2.f);

    // Force: F = -dE/dr * (dp/r)
    // dp/dr = -b * y^4
    const float dpdr = -b * y4;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;

    return (float4)(dp * f_over_r, E);
}

/**
 * @brief Morse potential using a linear approximation of the exponential term (n=9).
 */
inline float4 getMorse_lin9( float3 dp, float R0, float E0, float b ){
    const float n = 9.f;
    const float r2 = dot(dp,dp);
    const float Rc = R0 + n/b;
    if (r2 > Rc*Rc) { return (float4)(0.f); }

    const float r_inv = rsqrt(r2);
    const float r     = r2 * r_inv;
    
    const float y = 1.f - (b/n)*(r - R0);

    // p = y^9
    const float y2 = y*y;
    const float y4 = y2*y2;
    const float y8 = y4*y4;
    const float p  = y8*y;

    const float E = E0 * p * (p - 2.f);

    const float dpdr = -b * y8;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;

    return (float4)(dp * f_over_r, E);
}

/**
 * @brief Morse potential using a linear approximation of the exponential term (n=17).
 */
inline float4 getMorse_lin17( float3 dp, float R0, float E0, float b ){
    const float n = 17.f;
    const float r2 = dot(dp,dp);
    const float Rc = R0 + n/b;
    if (r2 > Rc*Rc) { return (float4)(0.f); }

    const float r_inv = rsqrt(r2);
    const float r     = r2 * r_inv;
    
    const float y = 1.f - (b/n)*(r - R0);

    // p = y^17
    const float y2  = y*y;
    const float y4  = y2*y2;
    const float y8  = y4*y4;
    const float y16 = y8*y8;
    const float p   = y16*y;

    const float E = E0 * p * (p - 2.f);

    const float dpdr = -b * y16;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;

    return (float4)(dp * f_over_r, E);
}

/**
 * @brief Morse potential using a cubic polynomial approximation of the exponential term (n=5).
 * @param dp    float3 distance vector between particles.
 * @param R0    float  Equilibrium distance for the potential minimum.
 * @param E0    float  Potential well depth.
 * @param cpoly float4 Coefficients (c0, c1, c2, c3) of the polynomial in (r-R0).
 * @param Rc    float  Cutoff radius for the interaction.
 * @return float4   Force vector in xyz, Energy in w.
 */
inline float4 getMorse_cub5( float3 dp, float R0, float E0, float4 cpoly, float Rc ){
    const float r2 = dot(dp,dp);
    if (r2 > Rc*Rc) { return (float4)(0.f); }
    //const float r_inv = rsqrt(r2);
    //const float r     = r2 * r_inv;
    const float r     = sqrt(r2);
    const float r_inv = 1/r;
    const float x     = r - R0;
    // Polynomial y = P(x) and its derivative dy/dx, where x = r-R0
    const float y    = cpoly.x + x*( cpoly.y + x*(    cpoly.z + x*    cpoly.w ));
    const float dydr =               cpoly.y + x*(2.f*cpoly.z + x*3.f*cpoly.w);
    // p = y^5
    const float y2 = y*y;
    const float y4 = y2*y2;
    const float p  = y4*y;
    // Energy: E = E0 * (p^2 - 2p)
    const float E = E0 * p * (p - 2.f);
    // Force: F = -dE/dr * (dp/r)
    // dp/dr = 5 * y^4 * dy/dr
    const float dpdr     =  5.f * y4 * dydr;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;
    return (float4)(dp * f_over_r, E);
}

/**
 * @brief Morse potential using a cubic polynomial approximation (n=9).
 */
inline float4 getMorse_cub9( float3 dp, float R0, float E0, float4 cpoly, float Rc ){
    const float r2 = dot(dp,dp);
    if (r2 > Rc*Rc) { return (float4)(0.f); }

    const float r_inv = rsqrt(r2);
    const float r     = r2 * r_inv;
    const float x     = r - R0;

    const float y    = cpoly.x + x*( cpoly.y + x*( cpoly.z + x*cpoly.w ));
    const float dydr =             cpoly.y + x*(2.f*cpoly.z + x*3.f*cpoly.w);

    // p = y^9
    const float y2 = y*y;
    const float y4 = y2*y2;
    const float y8 = y4*y4;
    const float p  = y8*y;
    
    const float E = E0 * p * (p - 2.f);

    // dp/dr = 9 * y^8 * dy/dr
    const float dpdr = 9.f * y8 * dydr;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;

    return (float4)(dp * f_over_r, E);
}

/**
 * @brief Morse potential using a cubic polynomial approximation (n=17).
 */
inline float4 getMorse_cub17( float3 dp, float R0, float E0, float4 cpoly, float Rc ){
    const float r2 = dot(dp,dp);
    if (r2 > Rc*Rc) { return (float4)(0.f); }

    const float r_inv = rsqrt(r2);
    const float r     = r2 * r_inv;
    const float x     = r - R0;

    const float y    = cpoly.x + x*( cpoly.y + x*( cpoly.z + x*cpoly.w ));
    const float dydr =             cpoly.y + x*(2.f*cpoly.z + x*3.f*cpoly.w);

    // p = y^17
    const float y2 = y*y;
    const float y4 = y2*y2;
    const float y8 = y4*y4;
    const float y16= y8*y8;
    const float p  = y16*y;
    
    const float E = E0 * p * (p - 2.f);

    // dp/dr = 17 * y^16 * dy/dr
    const float dpdr = 17.f * y16 * dydr;
    const float f_scalar = -2.f * E0 * (p - 1.f) * dpdr;
    const float f_over_r = f_scalar * r_inv;

    return (float4)(dp * f_over_r, E);
}




// evaluate non-covalent interaction force and energy for Lennard-Jones (Q) and Coulomb interactions of charges (Q) and hydrogen bond correction (pseudo-charges H), damping R2damp is used to avoid singularity at r=0
inline float4 getLJQH( float3 dp, float4 REQ, float R2damp ){
    // ---- Electrostatic (damped Coulomb potential)
    float   r2    = dot(dp,dp);
    float   ir2_  = 1.f/(  r2 +  R2damp);              // inverse distance squared and damped
    float   Ec    =  COULOMB_CONST*REQ.z*sqrt( ir2_ ); // Ec = Q1*Q2/sqrt(r^2+R2damp)
    // --- Lennard-Jones and Hydrogen bond correction
    float  ir2 = 1.f/r2;          // inverse distance squared
    float  u2  = REQ.x*REQ.x*ir2; // u2 = (R0/r)^2
    float  u6  = u2*u2*u2;        // u6 = (R0/r)^6
    float vdW  = u6*REQ.y;        // vdW = E0*(R0/r)^6
    float E    =       (u6-2.f)*vdW     + Ec  ;     // E = E0*(R0/r)^6 - E0*(R0/r)^12 + Q1*Q2/sqrt(r^2+R2damp)
    float fr   = -12.f*(u6-1.f)*vdW*ir2 - Ec*ir2_;  // fr = -12*E0*( (R0/r)^8/r + 12*E0*(R0/r)^14) - Q1*Q2/(r^2+R2damp)^1.5
    return  (float4){ dp*fr, E };
}

inline float4 getMorseQH( float3 dp,  float4 REQH, float K, float R2damp ){
    float r2    = dot(dp,dp);
    float ir2_  = 1/(r2+R2damp);
    float r     = sqrt( r2   );
    float ir_   = sqrt( ir2_ );     // ToDo: we can save some cost if we approximate r^2 = r^2 + R2damp;
    float e     = exp ( K*(r-REQH.x));
    //double e2    = e*e;
    //double fMors =  E0*  2*K*( e2 -   e ); // Morse
    //double EMors =  E0*      ( e2 - 2*e );
    float   Ae  = REQH.y*e;
    float fMors = Ae*  2*K*(e - 1); // Morse
    float EMors = Ae*      (e - 2);
    float Eel   = COULOMB_CONST*REQH.z*ir_;
    float fr    = fMors/r - Eel*ir2_ ;
    return  (float4){ dp*fr, EMors+Eel };
}

// evaluate damped Coulomb potential and force 
inline float4 getCoulomb( float3 dp, float R2damp ){
    // ---- Electrostatic
    float   r2    = dot(dp,dp);
    float   ir2_  = 1.f/(  r2 + R2damp);
    float   E    = COULOMB_CONST*sqrt( ir2_ );
    return  (float4){ dp*-E*ir2_, E };
}

// limit force magnitude to fmax
float3 limnitForce( float3 f, float fmax ){
    float fr2 = dot(f,f);                         // force magnitude squared
    if( fr2>(fmax*fmax) ){ f*=(fmax/sqrt(fr2)); } // if force magnitude is larger than fmax we scale it down to fmax
    return f;
}

float4 getR4repulsion( float3 d, float R, float Rcut, float A ){
    // we use R4blob(r) = A * (1-r^2)^2
    // such that at distance r=R we have force f = fmax
    // f = -dR4blob/dr = 4*A*r*(1-r^2) = fmax
    // A = fmax/(4*R*(1-R^2))
    float R2    = R*R;
    float R2cut = Rcut*Rcut;
    float r2 = dot(d,d);
    if( r2>R2cut ){ 
        return (float4){0.0f,0.0f,0.0f,0.0f};
    }else if( r2>R2 ){ 
        float mr2 = R2cut-r2;
        float fr = A*mr2;
        return (float4){ d*(-4*fr), fr*mr2 };
    }else{
        float mr2 = R2cut-R2;
        float fr  = A*mr2;
        float r    = sqrt(r2);
        float fmax = 4*R*fr;
        return (float4){ d* (-fmax/r), fmax*(R-r) + fr*mr2 };
    }
}


// ======================================================================
// ======================================================================
//                           MMFF kernells
// ======================================================================
// ======================================================================

__kernel void scanNonBond(
    const    int     n,       // 1  number of points
    const    float4  REQH,    // 2  non-bonded parameters (RvdW,EvdW,QvdW,Hbond)
    __global float4* pos,   // 3  [n]positions of points
    __global float4* force, // 4  [n]forces on points
    const    float8  ffpar    // 5  parameters specific to the potential function used
){
    for(int i=0; i<n; i++){
        float4 fij;
        const float3 dp = pos[i].xyz;
        //fij=getForce(dp,REQH,ffpar.x);
        //<<<GET_FORCE_NONBOND   // this line will be replaced python pre-processor
        force[i] = fij;
    }
}

#define WG_scanNonBond2 32
__kernel void scanNonBond2(
    const int         n,     // 1  number of points
    const float4      REQH0, // 2  non-bonded parameters of test atom (RvdW,EvdW,QvdW,Hbond)
    __global float4*  pos,   // 3  [n] positions of points
    __global float4*  force, // 4  [n] forces on points
    const int         na,    // 5  number of atoms
    __global float4*  apos,  // 6  [na] postions of atoms
    __global float4*  REQs,  // 7  [na] non-bonded parameters of atoms (RvdW,EvdW,QvdW,Hbond)
    const float8      ffpar  // 8  parameters specific to the potential function used
){
    __local float4 lPos[WG_scanNonBond2];          // cached atom positions
    __local float4 lPar[WG_scanNonBond2];          // cached atom parameters
    const int    lid = get_local_id(0);  // 0 … WG-1
    const int    gid = get_global_id(0); // 0 … n-1
    const float3 p   = pos[gid].xyz;     // position of the test point
    float4       f   = (float4)(0.0f);
    // tile atoms through shared memory
    for(int il0=0; il0<na; il0+=WG_scanNonBond2){
        int ia=il0+lid;      // global atom index
        if(ia<na){
            lPos[lid]=apos[ia];
            lPar[lid]=REQs[ia];
        }
        barrier(CLK_LOCAL_MEM_FENCE);
        // loop over the current tile
        #pragma unroll           // optional
        for (int j=0; j<WG_scanNonBond2; ++j) {
            int ja=il0+j;
            if(ia<na){
                const float3 dp  = lPos[j].xyz-p;
                float4 REQH      = lPar[j];
                REQH.x  +=REQH0.x;
                REQH.yzw*=REQH0.yzw;
                float4 fij;
                //fij=getForce(dp,REQH,ffpar.x);
                //<<<GET_FORCE_NONBOND   // this line will be replaced python pre-processor
                f+=fij;
            }
        }
        barrier(CLK_LOCAL_MEM_FENCE);
    }
    if(gid<n){
        force[gid]=f;
    }
}

__kernel void scanNonBond2PBC( 
    const int         n,      // 1  number of points
    const float4      REQH0,  // 2  non-bonded parameters of test atom (RvdW,EvdW,QvdW,Hbond)
    __global float4*  pos,    // 3  [n] positions of points
    __global float4*  force,  // 4  [n] forces on points
    const int         na,     // 5  number of atoms
    __global float4*  apos,   // 6  [na] postions of atoms
    __global float4*  REQs,   // 7  [na] non-bonded parameters of atoms (RvdW,EvdW,QvdW,Hbond)
    const float8      ffpar,  // 8  parameters specific to the potential function used
    const cl_Mat3     lvec,   // 9  lattice vectors for each system
    const int4        nPBC    // 10 number of PBC images in each direction (x,y,z)
){
    __local float4 lPos[WG_scanNonBond2];          // cached atom positions
    __local float4 lPar[WG_scanNonBond2];          // cached atom parameters
    const int    lid = get_local_id(0);  // 0 … WG-1
    const int    gid = get_global_id(0); // 0 … n-1
    const float3 p   = pos[gid].xyz;     // position of the test point
    float4       f   = (float4)(0.0f);
    // tile atoms through shared memory
    for(int il0=0; il0<na; il0+=WG_scanNonBond2){
        int ia=il0+lid;      // global atom index
        if(ia<na){
            lPos[lid]=apos[ia];
            lPar[lid]=REQs[ia];
        }
        barrier(CLK_LOCAL_MEM_FENCE);
        // loop over the current tile
        #pragma unroll           // optional
        for (int j=0; j<WG_scanNonBond2; ++j) {
            int ja=il0+j;
            if(ia<na){
                const float3 dp0  = lPos[j].xyz-p;
                float4 REQH      = lPar[j];
                REQH.x  +=REQH0.x;
                REQH.yzw*=REQH0.yzw;
                for(int ix=-nPBC.x; ix<=nPBC.x; ix++){
                    const float3 dp0x = dp0 + lvec.b.xyz*ix;
                    for(int iy=-nPBC.y; iy<=nPBC.y; iy++){
                        const float3 dp0y = dp0x + lvec.c.xyz*iy;
                        for(int iz=-nPBC.z; iz<=nPBC.z; iz++){
                            const float3 dp = dp0y + lvec.a.xyz*iz;
                            float4 fij;
                            //fij=getForce(dp,REQH,ffpar.x);
                            //<<<GET_FORCE_NONBOND   // this line will be replaced python pre-processor
                            f+=fij;
                        }
                    }
                }
            }
        }
        barrier(CLK_LOCAL_MEM_FENCE);
    }
    if(gid<n){
        force[gid]=f;
    }
}

__kernel void scanNonBond2PBC_2( 
    const int         n,      // 1  number of points
    const float4      REQH0,  // 2  non-bonded parameters of test atom (RvdW,EvdW,QvdW,Hbond)
    __global float4*  pos,    // 3  [n] positions of points
    __global float4*  force,  // 4  [n] forces on points
    const int         na,     // 5  number of atoms
    __global float4*  apos,   // 6  [na] postions of atoms
    __global float4*  REQs,   // 7  [na] non-bonded parameters of atoms (RvdW,EvdW,QvdW,Hbond)
    const float8      ffpar,  // 8  parameters specific to the potential function used
    const cl_Mat3     lvec,   // 9  lattice vectors for each system
    const int4        nPBC    // 10 number of PBC images in each direction (x,y,z)
){
    __local float4 lPos[WG_scanNonBond2];          // cached atom positions
    __local float4 lPar[WG_scanNonBond2];          // cached atom parameters
    const int    lid = get_local_id(0);  // 0 … WG-1
    const int    gid = get_global_id(0); // 0 … n-1
    const float3 p   = pos[gid].xyz;     // position of the test point
    float4       f   = (float4)(0.0f);
    // tile atoms through shared memory
    for(int il0=0; il0<na; il0+=WG_scanNonBond2){
        int ia=il0+lid;      // global atom index
        if(ia<na){
            lPos[lid]=apos[ia];
            lPar[lid]=REQs[ia];
        }
        barrier(CLK_LOCAL_MEM_FENCE);
        // loop over the current tile
        for(int ix=-nPBC.x; ix<=nPBC.x; ix++){
            const float3 p0x = p + lvec.b.xyz*ix;
            for(int iy=-nPBC.y; iy<=nPBC.y; iy++){
                const float3 p0y = p0x + lvec.c.xyz*iy;
                for(int iz=-nPBC.z; iz<=nPBC.z; iz++){
                    const float3 p0 = p0y + lvec.a.xyz*iz;
                    #pragma unroll           // optional
                    for (int j=0; j<WG_scanNonBond2; ++j) {
                        int ja=il0+j;
                        if(ia<na){
                            const float3 dp  = lPos[j].xyz-p0;
                            float4 REQH      = lPar[j];
                            REQH.x  +=REQH0.x;
                            REQH.yzw*=REQH0.yzw;
                            float4 fij;
                            //fij=getForce(dp,REQH,ffpar.x);
                            //<<<GET_FORCE_NONBOND   // this line will be replaced python pre-processor
                            f+=fij;
                        }
                    }
                }
            }
        }
        barrier(CLK_LOCAL_MEM_FENCE);
    }
    if(gid<n){
        force[gid]=f;
    }
}



__kernel void getNonBond_template(
    const int4        nDOFs,        // 1 // (natoms,nnode) dimensions of the system
    // Dynamical
    __global float4*  apos,         // 2 // positions of atoms  (including node atoms [0:nnode] and capping atoms [nnode:natoms] and pi-orbitals [natoms:natoms+nnode] )
    __global float4*  aforce,       // 3 // forces on atoms
    // Parameters
    __global float4*  REQs,         // 4 // non-bonded parameters (RvdW,EvdW,QvdW,Hbond)
    __global int4*    neighs,       // 5 // neighbors indices      ( to ignore interactions between bonded atoms )
    __global int4*    neighCell,    // 6 // neighbors cell indices ( to know which PBC image should be ignored  due to bond )
    __global cl_Mat3* lvecs,        // 7 // lattice vectors for each system
    const int4        nPBC,         // 8 // number of PBC images in each direction (x,y,z)
    const float4      GFFParams
    //,     // 9 // Grid-Force-Field parameters
    //__local float4*   LATOMS,
    //__local float4*   LCLJS
){
    // we use local memory to store atomic position and parameters to speed up calculation, the size of local buffers should be equal to local workgroup size
    //__local float4 LATOMS[2];
    //__local float4 LCLJS [2];
    //__local float4 LATOMS[4];
    //__local float4 LCLJS [4];
    //__local float4 LATOMS[8];
    //__local float4 LCLJS [8];
    //__local float4 LATOMS[16];
    //__local float4 LCLJS [16];
    __local float4 LATOMS[32];   // local buffer for atom positions
    __local float4 LCLJS [32];   // local buffer for atom parameters
    //__local float4 LATOMS[64];
    //__local float4 LCLJS [64];
    //__local float4 LATOMS[128];
    //__local float4 LCLJS [128];

    const int iG = get_global_id  (0); // index of atom
    const int nG = get_global_size(0); // number of atoms
    const int iS = get_global_id  (1); // index of system
    const int nS = get_global_size(1); // number of systems
    const int iL = get_local_id   (0); // index of atom in local memory
    const int nL = get_local_size (0); // number of atoms in local memory

    const int natoms=nDOFs.x;  // number of atoms
    const int nnode =nDOFs.y;  // number of node atoms
    //const int nAtomCeil =ns.w;
    const int nvec  =natoms+nnode; // number of vectors (atoms+node atoms)
    //const int i0n = iS*nnode; 
    const int i0a = iS*natoms;  // index of first atom in atoms array
    const int i0v = iS*nvec;    // index of first atom in vectors array
    //const int ian = iG + i0n;
    const int iaa = iG + i0a; // index of atom in atoms array
    const int iav = iG + i0v; // index of atom in vectors array
    
    //const int iS_DBG = 0;
    //const int iG_DBG = 0;

    // NOTE: if(iG>=natoms) we are reading from invalid adress => last few processors produce crap, but that is not a problem
    //       importaint is that we do not write this crap to invalid address, so we put   if(iG<natoms){forces[iav]+=fe;} at the end
    //       we may also put these if(iG<natoms){ .. } around more things, but that will unnecessarily slow down other processors
    //       we need these processors with (iG>=natoms) to read remaining atoms to the local memory.

    //if(iG<natoms){
    //const bool   bNode = iG<nnode;   // All atoms need to have neighbors !!!!
    const bool   bPBC  = (nPBC.x+nPBC.y+nPBC.z)>0;  // PBC is used if any of the PBC dimensions is >0
    //const bool bPBC=false;

    const int4   ng     = neighs   [iaa];  // neighbors indices
    const int4   ngC    = neighCell[iaa];  // neighbors cell indices
    const float4 REQKi  = REQs     [iaa];  // non-bonded parameters
    const float3 posi   = apos     [iav].xyz; // position of atom
    const float  R2damp = GFFParams.x*GFFParams.x; // squared damping radius
    float4 fe           = float4Zero;  // force on atom

    const cl_Mat3 lvec = lvecs[iS]; // lattice vectors for this system
    //if((iG==iGdbg)&&(iS==iSdbg)){ printf("OCL::getNonBond() getNonBond(): natoms=%i, nnode=%i nSys=%i nPBC=(%i,%i,%i)\n", natoms, nnode, get_global_size(1), nPBC.x, nPBC.y, nPBC.z); }
    // if((iG==iGdbg)&&(iS==iSdbg)){ 
    //     printf("OCL::getNonBond() getNonBond(): natoms=%i, nnode=%i nPBC=(%i,%i,%i)\n", natoms, nnode, nPBC.x, nPBC.y, nPBC.z);
    //     printf("OCL::getNonBond(): lvec.a=(%g,%g,%g) lvec.b=(%g,%g,%g) lvec.c=(%g,%g,%g)\n", lvec.a.x, lvec.a.y, lvec.a.z, lvec.b.x, lvec.b.y, lvec.b.z, lvec.c.x, lvec.c.y, lvec.c.z);
    //     printf("OCL::getNonBond(): GFFParams=(%g,%g,%g,%g) \n", GFFParams.x, GFFParams.y, GFFParams.z, GFFParams.w);
    //     for(int i=0; i<natoms; i++){
    //         float4 pi = apos[i];
    //         int4   ng = neighs[i];
    //         int4   ngC = neighCell[i];
    //         float4 REQKi = REQs[i];
    //         printf("OCL::getNonBond() atom %i: ng=(%i,%i,%i,%i), ngC=(%i,%i,%i,%i), REQKi=(%10.5f,%10.5f,%10.5f|%10.5f), posi=(%10.5f,%10.5f,%10.5f,%10.5f)\n", i, ng.x, ng.y, ng.z, ng.w, ngC.x, ngC.y, ngC.z, ngC.w, REQKi.x, REQKi.y, REQKi.z, REQKi.w, pi.x, pi.y, pi.z, pi.w);
    //     }   
    // }

    //if(iG==0){ printf("GPU[iS=%i] lvec{%6.3f,%6.3f,%6.3f}{%6.3f,%6.3f,%6.3f}{%6.3f,%6.3f,%6.3f} \n", iS, lvec.a.x,lvec.a.y,lvec.a.z,  lvec.b.x,lvec.b.y,lvec.b.z,   lvec.c.x,lvec.c.y,lvec.c.z );  }

    //if(iG==0){ for(int i=0; i<natoms; i++)printf( "GPU[%i] ng(%i,%i,%i,%i) REQ(%g,%g,%g) \n", i, neighs[i].x,neighs[i].y,neighs[i].z,neighs[i].w, REQs[i].x,REQs[i].y,REQs[i].z ); }

    const float3 shift0  = lvec.a.xyz*-nPBC.x + lvec.b.xyz*-nPBC.y + lvec.c.xyz*-nPBC.z;   // shift of PBC image 0
    const float3 shift_a = lvec.b.xyz + lvec.a.xyz*(nPBC.x*-2.f-1.f);                      // shift of PBC image in the inner loop
    const float3 shift_b = lvec.c.xyz + lvec.b.xyz*(nPBC.y*-2.f-1.f);                      // shift of PBC image in the outer loop
    //}
    /*
    if((iG==iG_DBG)&&(iS==iS_DBG)){ 
        printf( "OCL::getNonBond() natoms,nnode,nvec(%i,%i,%i) nS,nG,nL(%i,%i,%i) bPBC=%i nPBC(%i,%i,%i)\n", natoms,nnode,nvec, nS,nG,nL, bPBC, nPBC.x,nPBC.y,nPBC.z ); 
        for(int i=0; i<natoms; i++){
            printf( "GPU a[%i] ", i);
            printf( "p{%6.3f,%6.3f,%6.3f} ", atoms[i0v+i].x,atoms[i0v+i].y,atoms[i0v+i].z  );
            printf( "ng{%i,%i,%i,%i} ", neighs[i0a+i].x,neighs[i0a+i].y,neighs[i0a+i].z,neighs[i0a+i].w );
            printf( "ngC{%i,%i,%i,%i} ", neighCell[i0a+i].x,neighCell[i0a+i].y,neighCell[i0a+i].z,neighCell[i0a+i].w );
            printf( "\n");
        }
    }
    */

    // ========= Atom-to-Atom interaction ( N-body problem ), we do it in chunks of size of local memory, in order to reuse data and reduce number of reads from global memory  
    //barrier(CLK_LOCAL_MEM_FENCE);
    for (int j0=0; j0<nG; j0+=nL){     // loop over all atoms in the system, by chunks of size of local memory
        const int i=j0+iL;             // index of atom in local memory
        if(i<natoms){                  // j0*nL may be larger than natoms, so we need to check if we are not reading from invalid address
            LATOMS[iL] = apos [i+i0v]; // read atom position to local memory 
            LCLJS [iL] = REQs [i+i0a]; // read atom parameters to local memory
        }
        barrier(CLK_LOCAL_MEM_FENCE);   // wait until all atoms are read to local memory
        for (int jl=0; jl<nL; jl++){    // loop over all atoms in local memory (like 32 atoms)
            const int ja=j0+jl;         // index of atom in global memory
            if( (ja!=iG) && (ja<natoms) ){   // if atom is not the same as current atom and it is not out of range,  // ToDo: Should atom interact with himself in PBC ?
                const float4 aj = LATOMS[jl];    // read atom position   from local memory
                float4 REQK     = LCLJS [jl];    // read atom parameters from local memory
                float3 dp       = aj.xyz - posi; // vector between atoms
                //if((iG==44)&&(iS==0))printf( "[i=%i,ja=%i/%i,j0=%i,jl=%i/%i][iG/nG/na %i/%i/%i] aj(%g,%g,%g,%g) REQ(%g,%g,%g,%g)\n", i,ja,nG,j0,jl,nL,   iG,nG,natoms,   aj.x,aj.y,aj.z,aj.w,  REQK.x,REQK.y,REQK.z,REQK.w  );
                REQK.x  +=REQKi.x;   // mixing rules for vdW Radius
                REQK.yz *=REQKi.yz;  // mixing rules for vdW Energy
                const bool bBonded = ((ja==ng.x)||(ja==ng.y)||(ja==ng.z)||(ja==ng.w));
                //if( (j==0)&&(iG==0) )printf( "pbc NONE dp(%g,%g,%g)\n", dp.x,dp.y,dp.z ); 
                //if( (ji==1)&&(iG==0) )printf( "2 non-bond[%i,%i] bBonded %i\n",iG,ji,bBonded );

                if(bPBC){         // ===== if PBC is used, we need to loop over all PBC images of the atom
                    int ipbc=0;   // index of PBC image
                    dp += shift0; // shift to PBC image 0
                    // Fixed PBC size
                    for(int iy=0; iy<3; iy++){
                        for(int ix=0; ix<3; ix++){
                            //if( (ji==1)&&(iG==0)&&(iS==0) )printf( "GPU ipbc %i(%i,%i) shift(%7.3g,%7.3g,%7.3g)\n", ipbc,ix,iy, shift.x,shift.y,shift.z ); 
                            // Without these IF conditions if(bBonded) time of evaluation reduced from 61 [ms] to 51[ms]
                            if( !( bBonded &&(                     // if atoms are bonded, we do not want to calculate non-covalent interaction between them
                                      ((ja==ng.x)&&(ipbc==ngC.x))    // check if this PBC image is not the same as one of the bonded atoms
                                    ||((ja==ng.y)&&(ipbc==ngC.y))  // i.e. if ja is neighbor of iG, and ipbc is its neighbor cell index then we skip this interaction
                                    ||((ja==ng.z)&&(ipbc==ngC.z))
                                    ||((ja==ng.w)&&(ipbc==ngC.w))
                            ))){
                                // float4 fij = getLJQH( dp, REQK, R2damp );
                                float4 fij;
                                //<<<---GET_FORCE_NONBOND   // this line will be replaced python pre-processor
                                fe += fij;
                            }
                            ipbc++; 
                            dp    += lvec.a.xyz; 
                        }
                        dp    += shift_a;
                    }
                }else   // ===== if PBC is not used, it is much simpler
                if( !bBonded ){  
                    //float4 fij = getLJQH( dp, REQK, R2damp ); 
                    float4 fij;
                    //<<<---GET_FORCE_NONBOND   // this line will be replaced python pre-processor
                    fe += fij;
                    //if((iG==iGdbg)&&(iS==iSdbg)){   printf("OCL::getNonBond(): ia,ja %3i %3i aj(%10.5f,%10.5f,%10.5f) dp( %10.5f | %10.5f,%10.5f,%10.5f)  fij( %10.5f,%10.5f,%10.5f|%10.5f)\n", iG, ja, aj.x,aj.y,aj.z, length(dp), dp.x, dp.y, dp.z, fij.x, fij.y, fij.z, fij.w); }
                }  // if atoms are not bonded, we calculate non-bonded interaction between them
            }
        }
        //barrier(CLK_LOCAL_MEM_FENCE);
    }
    
    if(iG<natoms){
        //if(iS==0){ printf( "OCL::getNonBond(iG=%i) fe(%g,%g,%g,%g)\n", iG, fe.x,fe.y,fe.z,fe.w ); }
        aforce[iav] = fe;           // If we do    run it as first forcefield, we can just store force (non need to clean it before in that case)
        //aforce[iav] += fe;        // If we don't run it as first forcefield, we need to add force to existing force
        //aforce[iav] = fe*(-1.f);
    }
}

