#!/usr/bin/env python3
"""
Test script for scanNonBond and scanNonBond2 kernels.

This script demonstrates the improved workflow with explicit file paths
and debugging capabilities for testing non-bonded force fields.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

#sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pyBall'))
#from .MolecularDynamics import MolecularDynamics
from ..plotUtils import plot1d


import sys
import os
import numpy as np
import re

import pyopencl as cl
# from . import clUtils as clu
import pyopencl.array as cl_array
import pyopencl.cltypes as cltypes
import matplotlib.pyplot as plt
import time

from . import clUtils as clu
#from .MMFF import MMFF
from .OpenCLBase import OpenCLBase

REQ_DEFAULT = np.array([1.7, 0.1, 0.0, 0.0], dtype=np.float32)  # R, E, Q, padding

verbose=False

def pack(iSys, source_array, target_buffer, queue):
    offset = iSys * source_array.size * source_array.dtype.itemsize
    cl.enqueue_copy(queue, target_buffer, source_array, offset=offset)

def copy(source, target, queue, iSys):
    pack(iSys, source, target, queue)

def copy_add(source, source_add, target, offset, queue):
    pass

def mat3_to_cl(mat3_np):
    return mat3_np.flatten().astype(np.float32)

def vec3_to_cl(vec3_np):
    return np.append(vec3_np, 0.0).astype(np.float32)

class MolecularDynamics(OpenCLBase):
    """
    Class for molecular dynamics simulations using OpenCL.
    
    This class inherits from OpenCLBase and implements specific functionality
    for molecular dynamics simulations using the relax_multi_mini.cl kernel.
    """
    
    def __init__(self, nloc=32, perBatch=10):
        # Initialize the base class
        super().__init__(nloc=nloc, device_index=0)
        
        # Load the OpenCL program
        base_path = os.path.dirname(os.path.abspath(__file__))
        rel_path = "kernels/Molecular.cl"
        if not self.load_program(rel_path=rel_path, base_path=base_path, bPrint=False):
            exit(1)
        
        # Initialize other attributes that will be set in realloc
        self.nSystems       = 0
        self.mmff_list      = []
        self.MD_event_batch = None
        self.perBatch       = perBatch
        self.nstep          = 1


    def realloc_scan(self, n, na=-1):
        sz_f  = 4
        buffs = {
            "poss":    (sz_f*4 * n),
            "forces":  (sz_f*4 * n),
        }
        if na>0:
            buffs.update({
                "apos":   (sz_f*4 * na),
                "aREQs":  (sz_f*4 * na),
            })
        self.try_make_buffers(buffs)

    def scanNonBond(self, pos, force, REQH, ffpar, bRealloc=True ):
        n = len(pos)
        if bRealloc:  self.realloc_scan(n)
        # Upload data to GPU
        self.toGPU_( self.poss_buff,   pos)
        self.toGPU_( self.forces_buff, force)
        # Get kernel
        kernel = self.prg.scanNonBond
        # Set arguments
        # Ensure ffpar is length-8 for float8 (pad with zeros if needed)
        ffpar_arr = np.asarray(ffpar, dtype=np.float32).ravel()
        if ffpar_arr.size > 8:
            ffpar_arr = ffpar_arr[:8]
        ffpar8 = np.zeros(8, dtype=np.float32)
        ffpar8[:ffpar_arr.size] = ffpar_arr
        kernel.set_args(
            np.int32(n),
            cl_array.vec.make_float4(*REQH),
            self.poss_buff,
            self.forces_buff,
            cl_array.vec.make_float8(*ffpar8)
        )
        # Run kernel
        global_size = (n,)
        local_size = None
        cl.enqueue_nd_range_kernel(self.queue, kernel, global_size, local_size)
        result = self.fromGPU_( self.forces_buff, shape=(n, 4))
        self.queue.finish()
        return result

    def scanNonBond2(self, pos, force, apos, aREQs, REQH0, ffpar, bRealloc=True, nPBC=None, lvec=None, name=""):
        n  = len(pos)
        na = len(apos)
        if bRealloc:  self.realloc_scan(n, na=na)
        # Upload data to GPU
        self.toGPU_( self.poss_buff,   pos)
        self.toGPU_( self.forces_buff, force)
        self.toGPU_( self.apos_buff,   apos)
        self.toGPU_( self.aREQs_buff,  aREQs)  
        # Ensure ffpar is length-8 for float8 (pad with zeros if needed)
        ffpar_arr = np.asarray(ffpar, dtype=np.float32).ravel()
        if ffpar_arr.size > 8:
            ffpar_arr = ffpar_arr[:8]
        ffpar8 = np.zeros(8, dtype=np.float32)
        ffpar8[:ffpar_arr.size] = ffpar_arr
        # Get kernel

        if nPBC is not None:
            # Convert lvec to cl_Mat3 structure (3 float4 vectors)
            lvec_cl = np.zeros((3,4), dtype=np.float32)
            lvec_cl[:,:3] = lvec
            npbc_cl = np.zeros((4), dtype=np.int32)
            npbc_cl[:3] = nPBC
            #kernel = self.prg.scanNonBond2PBC
            kernel = self.prg.scanNonBond2PBC_2
            kernel.set_args(
                np.int32(n),
                cl_array.vec.make_float4(*REQH0),
                self.poss_buff,
                self.forces_buff,
                np.int32(na),
                self.apos_buff,
                self.aREQs_buff,
                cl_array.vec.make_float8(*ffpar8),
                lvec_cl,
                npbc_cl,
            )
        else:
            kernel = self.prg.scanNonBond2        
            kernel.set_args(
                np.int32(n),
                cl_array.vec.make_float4(*REQH0),
                self.poss_buff,
                self.forces_buff,
                np.int32(na),
                self.apos_buff,
                self.aREQs_buff,
                cl_array.vec.make_float8(*ffpar8)
            )        
        nloc=32
        local_size  = (nloc,)
        global_size = (clu.roundup_global_size(n, nloc),)
        T0 = time.time()
        cl.enqueue_nd_range_kernel(self.queue, kernel, global_size, local_size)
        self.queue.finish()
        T = time.time() - T0

        if nPBC is not None:
            npbc=(nPBC[0]*2+1)*(nPBC[1]*2+1)*(nPBC[2]*2+1)
            ntot = n*na*npbc
            #print(f"scanNonBond2() {name:<15} | {(T*1.e+9/ntot):>2.6f} [ns/op] {(T*1.e+12/ntot):>4.6f} [TOPS] | ntot: {ntot:<12}  np: {n:<6} na: {na:<6} nPBC({npbc:<6},{nPBC}) time: {T:3.6f} [s]")
            print(f"scanNonBond2PBC() {name:<15} | {T*1.e+9/ntot:>8.4f} [ns/op] {(ntot/(T*1.e+9)):>8.4f} [GOPS] | ntot: {ntot:>12} np: {n:>6} na: {na:>6} nPBC({npbc:>6},{nPBC}) time: {T:>8.4f} [s]")
        else:
            ntot = n*na
            #print(f"scanNonBond2() {name:<15} | {(T*1.e+9/ntot):>2.6f} [ns/op] {(T*1.e+12/ntot):>4.6f} [TOPS] | ntot: {ntot:<12}  np: {n:<6} na: {na:<6} nPBC({npbc:<6},{nPBC}) time: {T:3.6f} [s]")
            print(f"scanNonBond2() {name:<15} | {T*1.e+9/ntot:>8.4f} [ns/op] {(ntot/(T*1.e+9)):>8.4f} [GOPS] | ntot: {ntot:>12} np: {n:>6} na: {na:>6} time: {T:>8.4f} [s]")

        # Download results
        result = self.fromGPU_( self.forces_buff, shape=(n, 4))
        return result


def exp_fe( x, b=1.6):
    y  = np.exp(-b*x)
    dy = -b*y
    return y, dy

def exp_pow_cubic( bMorse=1.6, n=5, x1=3.0, x2=5.0 ):
    # 1. Define the target function g(r) = exp(-b*(r-Ri)/n) and its derivative
    y1, dy1 = exp_fe(x1, bMorse/n)
    y2, dy2 = exp_fe(x2, bMorse/n)
    
    # 3. Set up and solve the 4x4 linear system for the coefficients of p(r)
    A = np.array([
        [   x1**3,   x1**2 ,x1 , 1 ], 
        [ 3*x1**2, 2*x1    ,1  , 0 ],
        [   x2**3,   x2**2 ,x2 , 1 ], 
        [ 3*x2**2, 2*x2    ,1  , 0 ]
    ])
    rhs            = np.array([y1, dy1, y2, dy2])
    coeffs         = np.linalg.solve(A, rhs)
    all_roots      = np.roots(coeffs)
    real_roots     = all_roots[np.isreal(all_roots)].real
    if len(real_roots) == 0: raise ValueError("Could not find a physical cutoff root for the given parameters.")
    Rc = np.max(real_roots)
    print(f"exp_pow_cubic() Rc: {Rc}", real_roots )
    print(f"exp_pow_cubic() coeffs: {coeffs}")
    return Rc, coeffs

def eval_exp_lin( x, b, n=5 ):
    p  = (1-x*b/n)
    dp = -b/n + (x*0.)
    #Rc = n/b
    mask = p<0
    p [mask]=0
    dp[mask]=0
    y  = p**n
    dy = n*p**(n-1)*dp 
    return y, dy

def eval_exp_pow_cubic( x, cs, n=5 ):
    dcs  = cs[:-1] * np.array([3, 2, 1])
    p    = np.polyval(cs , x)
    dp   = np.polyval(dcs, x)
    mask = p<0
    p [mask]=0
    dp[mask]=0
    y  = p**n
    dy = n*p**(n-1)*dp 
    return y, dy

def eval_Morse_pow_cubic(rs, R0, E0, cs, n=5):
    x = rs - R0
    p_base = np.polyval(cs, x)
    dcs = cs[:-1] * np.array([3, 2, 1])
    dp_base_dx = np.polyval(dcs, x)
    mask = p_base < 0
    p_base    [mask] = 0
    dp_base_dx[mask] = 0
    p = p_base**n
    dpdr = n * (p_base**(n-1)) * dp_base_dx
    E =        E0 * p*(p-2.0)
    F = -2.0 * E0 *   (p-1.0) * dpdr
    return E, F

def eval_Morse_exact(rs, R0, E0, b):
    x = rs - R0
    p = np.exp(-b * x)
    E = E0 * p * (p - 2.0)
    F =  2 * b *  E0*p*(p - 1.0)
    return E, F

def test_potential_scans( n=100, xmin=0.0, xmax=10.0, R0=3.0, E0=1.0, bMorse=1.6):
    md = MolecularDynamics(nloc=32)
    
    # Define file paths
    base_path   = os.path.dirname(os.path.abspath(__file__))
    forces_path = os.path.join(base_path, 'kernels/Forces.cl')
    kernel_path = os.path.join(base_path, 'kernels/Molecular.cl')
    print(f"[DEBUG] forces_path: {forces_path}")
    print(f"[DEBUG] kernel_path (template): {kernel_path}")
    rs  = np.linspace(xmin, xmax, n)
    pos = np.zeros((n, 4), dtype=np.float32)
    pos[:, 0] = rs
    
    # Test atom parameters (REQH)
    REQH = np.array([R0, E0, 0.0, 0.0], dtype=np.float32)   # R, E, Q, H
    #REQH = np.array([3.0, 1.0, 1.0, 0.0], dtype=np.float32)  # R, E, Q, H
            
    # Parse Forces.cl to extract force functions
    print("\n=== Parsing Forces.cl ===")
    force_defs = md.parse_forces_cl(forces_path)
    print(f"Found {len(force_defs['functions'])} functions and {len(force_defs['macros'])} macros")
    
    #print(f"pos: \n", pos)
    #print(f"apos: \n", apos)
    
    # Test scanNonBond
    print("\n=== Testing scanNonBond ===")
    force = np.zeros((n, 4), dtype=np.float32)
    
    print("\n##################################")
    print("1. scanNonBond with getLJQH      ")
    print("##################################")

    #Rc, morse_pcub = exp_pow_cubic(bMorse, 5, 3.0, 5.0)
    Rc, morse_pcub = exp_pow_cubic(bMorse, 5, 0.0, 2.0);   Rc+=3.0 


    Rcl5 = 5/bMorse

    # y_ref, dy_ref = exp_fe(rs, bMorse)
    # y_lin, dy_lin = eval_exp_lin      (rs, bMorse,     5 )
    # y_cub, dy_cub = eval_exp_pow_cubic(rs, morse_pcub, 5 )
    # fig, (ax1, ax2) = plot1d(rs, [y_ref, y_lin, y_cub], [-dy_ref, -dy_lin, -dy_cub], labels=["exp", "exp_lin", "exp_pow_cubic"],colors=['k','r','g'], figsize=(8,12))
    # #ax1.set_ylim(-1,1)
    # ax1.axvline( Rcl5, c='r', ls='--')
    # ax1.axvline( Rc,   c='g', ls='--')
    # #plt.show()
    
    morse_pcub_ = morse_pcub[::-1]

    #exit()


    # potentials={
    #     #  name    ffpar             code                             
    #     #"LJ"         :  ( [ R2damp ],          "fij = getLJQH(dp, REQH, ffpar.x);"             ),
    #     #"Morse"      :  ( [ R2damp, bMorse],   "fij = getMorseQH(dp, REQH, ffpar.y, ffpar.x);" ),
    #     "exp_r"      :  ( [ bMorse ],          "fij = exp_r     ( dp, ffpar.x );"               ),
    #     "exp_r_lin4" :  ( [ bMorse ],          "fij = exp_r_lin4( dp, ffpar.x );"               ),
    #     "exp_r_lin8" :  ( [ bMorse ],          "fij = exp_r_lin8( dp, ffpar.x );"               ),
    #     "exp_r_lin16":  ( [ bMorse ],          "fij = exp_r_lin16( dp, ffpar.x );"              ),
    #     "exp_r_cub4" :  ( [ *morse_pcub_, Rc], "fij = exp_r_cub4( dp, ffpar.lo, ffpar.hi.x );"  ),
    # }
  

    # inline float4 getMorse_lin5( float3 dp, float R0, float E0, float b ){
    potentials={
        #  name    ffpar             code                             
        "Morse"      :  ( [ bMorse ],          "fij = getMorse      ( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_lin5" :  ( [ bMorse ],          "fij = getMorse_lin5 ( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_lin9" :  ( [ bMorse ],          "fij = getMorse_lin9 ( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_lin17":  ( [ bMorse ],          "fij = getMorse_lin17( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_cub5" :  ( [ *morse_pcub_, Rc], "fij = getMorse_cub5 ( dp, REQH.x, REQH.y, ffpar.lo,ffpar.hi.x );"  ),
    }

    names    = []
    energies = []
    forces   = []
    print( "REQH: ", REQH )
    print( "pos:  ", pos )
    for name,(ffpar, code) in potentials.items():
        #print(f"{name}: {ffpar}")
        output_path   = os.path.join(base_path, f"tests/tmp/cl/tmp_{name}.cl")
        substitutions = { "macros": { "GET_FORCE_NONBOND": code } }
        md.preprocess_opencl_source(kernel_path, substitutions, output_path)
        md.load_program(kernel_path=output_path)
        ffpar = np.array(ffpar, dtype=np.float32)
        fes = md.scanNonBond( pos=pos, force=force, REQH=REQH, ffpar=ffpar )

        print(f"   scanNonBond ({name}) completed cl_file={output_path} ffpar={ffpar} E: ", fes[:,3] )

        names    .append(name)
        energies .append(fes[:,3])
        forces   .append(fes[:,0])
        
        #print(f"   scanNonBond ({name}) completed cl_file={output_path}")
        #print(f"   Result forces: \n", forces)
        #print(f"   result forces.shape {fes.shape} range: [{fes.min():.3f}, {fes.max():.3f}]")

    fig, (ax1, ax2) = plot1d( rs, energies, forces, labels=names, colors=['k', 'b','c','g',   'r'], figsize=(10,15) )
    ax1.set_ylim(-1,1)
    ax2.set_ylim(-1,1)
    ax1.axvline( Rcl5, c='r', ls='--')
    ax1.axvline( Rc,   c='g', ls='--')
    plt.show()


def test_speed( n=1000, na=1000, bMorse=1.6, Rc=5.0, nPBC=None, lvec=[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]] ):

    # Initialize MolecularDynamics
    md = MolecularDynamics(nloc=32)
    
    # Define file paths
    base_path   = os.path.dirname(os.path.abspath(__file__))
    forces_path = os.path.join(base_path, '../../tests/tmp/data/cl/Forces.cl')
    kernel_path = os.path.join(base_path, 'kernels/Molecular.cl')
    print(f"[DEBUG] kernel_path (template): {kernel_path}")
        
    # Create test data
    np.random.seed(42)
    
    # Test positions (random points in 3D space)
    rs  = np.linspace(0.0, 10.0, n)
    pos = np.zeros((n, 4), dtype=np.float32)
    pos[:, 0] = rs
    
    # Atom positions
    apos = np.random.randn(na, 4).astype(np.float32)
    apos[:,0] = 0.0
    
    # Test atom parameters (REQH)
    REQH = np.array([3.0, 1.0, 0.0, 0.0], dtype=np.float32)  # R, E, Q, H
    #REQH = np.array([3.0, 1.0, 1.0, 0.0], dtype=np.float32)  # R, E, Q, H
    
    # Atom parameters
    aREQs = np.zeros((na, 4), dtype=np.float32)
    aREQs[:, 0]  = 1.4 +       np.random.rand(na)*0.6    # R values between 0-2
    aREQs[:, 1]  = 0.1 * ( 1 + np.random.rand(na)*1.0 )  # E values between 0-0.5
    aREQs[:, 2]  = 0.0  # Q values (neutral)
    aREQs[:, 3]  = 0.0  # H values
        
    # Parse Forces.cl to extract force functions
    #print("\n=== Parsing Forces.cl ===")
    #force_defs = md.parse_forces_cl(forces_path)
    #print(f"Found {len(force_defs['functions'])} functions and {len(force_defs['macros'])} macros")
    
    force = np.zeros((n, 4), dtype=np.float32)
    
    #Rc, morse_pcub = exp_pow_cubic(bMorse, 5, 3.0, 5.0)
    Rc, morse_pcub = exp_pow_cubic(bMorse, 5, 0.0, 2.0);   Rc+=3.0 
    
    morse_pcub_ = morse_pcub[::-1]

    # inline float4 getMorse_lin5( float3 dp, float R0, float E0, float b ){
    potentials={
        #  name    ffpar             code                             
        "invR2"      :  ( [],                  "fij = invR2      ( dp );"  ),
        "R2gauss"    :  ( [],                  "fij = R2gauss    ( dp );"  ),
        "Morse_lin5" :  ( [ bMorse ],          "fij = getMorse_lin5 ( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_lin9" :  ( [ bMorse ],          "fij = getMorse_lin9 ( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_lin17":  ( [ bMorse ],          "fij = getMorse_lin17( dp, REQH.x, REQH.y, ffpar.x );"  ),
        "Morse_cub5" :  ( [ *morse_pcub_, Rc], "fij = getMorse_cub5 ( dp, REQH.x, REQH.y, ffpar.lo,ffpar.hi.x );"  ),
        "Morse"      :  ( [ bMorse ],          "fij = getMorse      ( dp, REQH.x, REQH.y, ffpar.x );"  ),
    }

    names    = []
    energies = []
    forces   = []
    for name,(ffpar, code) in potentials.items():
        #print(f"{name}: {ffpar}")
        output_path   = os.path.join(base_path, f"tests/tmp/cl/tmp_{name}.cl")
        substitutions = { "macros": { "GET_FORCE_NONBOND": code } }
        md.preprocess_opencl_source(kernel_path, substitutions, output_path)
        md.load_program(kernel_path=output_path)
        fes = md.scanNonBond2( pos=pos, force=force, apos=apos, aREQs=aREQs, REQH0=REQH, ffpar=ffpar, name=name, nPBC=nPBC, lvec=lvec )

        names    .append(name)
        energies .append(fes[:,3])
        forces   .append(fes[:,0])

        #print(f"   scanNonBond ({name}) completed cl_file={output_path}")
        #print(f"   Result forces: \n", forces)
        #print(f"   result forces.shape {fes.shape} range: [{fes.min():.3f}, {fes.max():.3f}]")

    # fig, (ax1, ax2) = plot1d( rs, energies, forces, labels=names, colors=['k', 'b','c','g',   'r'], figsize=(10,15) )
    # ax1.set_ylim(-1,1)
    # ax2.set_ylim(-1,1)
    # ax1.axvline( Rcl5, c='r', ls='--')
    # ax1.axvline( Rc,   c='g', ls='--')
    # plt.show()


if __name__ == "__main__":
    # run it like this:
    #   python -u -m pyCruncher2.scientific.gpu.run_scanNonBond | tee OUT-scanNonBond

    test_potential_scans()

    
    #test_speed( n=10000, na=1000000 )
    #test_speed( n=100000, na=1000000 )
    #test_speed( n=1000000, na=1000000 )
    #test_speed( n=1000, na=1000, nPBC=[20,20,20]   )