
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
