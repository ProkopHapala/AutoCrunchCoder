
# **Generate sampling function**

You should generate function which samples the forcefield for an array of points so that we can test it. To make it general we pass the DOFs and parameters as arrays, therefore you need to generate wrrapper function which will bind the argument to proper index in the array. 

Assume that we used function template like this:

```C++
template<typename Func>
void evalAtPoints( int nps, int nDOF, double* ps, double* params, double* Es, double* Fs, Func func ){
    for(int i=0; i<nps; i++){
        double* p = ps + i*nDOF;
        double* F = Fs + i*nDOF;
        double  E = func( p, params, F );
        Es[i] = E;
    }
}
```

This function template is already defined in imported header files, therefore you should not reimplement it.

#### Example of sampling inferface

This is example how to use `evalAtPoints()` function template to make sampling interface for coulomb potential:

```C++

double coulomb(
    double  r,     // DOF #0  distance of particles
    double& dE_r,  // derivative of energy with respect to r ( DOF #0 )
    double  Q      // parameter #0
){    
    double ir    = 1.0/r;
    double E     = Q*ir;
    double dE_r = -E*ir;
    return E;
}

// wrapper function to properly pass arguments between array and named-arguments
double wrap_coulomb( double* dofs, double* Fs, double* params ){
    return coulomb( dofs[0], Fs[0], params[0] );
}

extern "C" { // use extern C to make sure we can easily inport it from python ctypes
    // use evalAtPoints() with our wrapper function as parameter
    void eval_coumlomb( int nps, int nDOF, double* ps, double* Es, double* Fs, double* params ){
        evalAtPoints( nps, nDOF, ps, Es, Fs, params, wrap_coulomb );
    }
}
```

