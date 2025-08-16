#!/usr/bin/env python3
"""
Generic GPU Numerical Integral Testing Framework using OpenCL macro specialization.

This script demonstrates a single generic kernel template `NumIntegral.cl` specialized
at build-time via macro injection to run two examples:

1) Biot–Savart magnetic field accumulation from current elements to sample points.
2) Molecular non-bonded Morse potential accumulation from atoms to probe points.

It does NOT modify any existing example scripts. It uses utilities from OpenCLBase.

Run:
  python -u -m pyCruncher2.scientific.gpu.test_num_integral_cl | tee OUT-generic-integral
"""

import os
import numpy as np
import pyopencl as cl
import pyopencl.array as cl_array
import matplotlib.pyplot as plt

from .OpenCLBase import OpenCLBase

MU0_4PI = np.float32(1.0e-7)  # SI


def circle_loop(M=256, R=1.0, center=(0.0, 0.0, 0.0), I=1.0):
    """Discretize a circular loop in XY plane into M straight segments.
    Returns mid-point positions r_mid[M,3], segment vectors dl[M,3], currents I[M].
    """
    c = np.array(center, dtype=np.float32)
    t = np.linspace(0.0, 2.0*np.pi, M+1, dtype=np.float32)
    x = R*np.cos(t); y = R*np.sin(t)
    r = np.stack([x, y, np.zeros_like(x)], axis=1) + c  # (M+1,3)
    r0 = r[:-1]; r1 = r[1:]
    dl = (r1 - r0).astype(np.float32)                    # (M,3)
    r_mid = 0.5*(r0 + r1).astype(np.float32)             # (M,3)
    Iarr = np.full((M,), np.float32(I))
    return r_mid, dl, Iarr


def line_samples(N=200, p0=(-2.0, 0.0, 0.5), p1=(2.0, 0.0, 0.5)):
    """Generate N sampling points along a straight line from p0 to p1 (inclusive)."""
    p0 = np.array(p0, dtype=np.float32)
    p1 = np.array(p1, dtype=np.float32)
    t = np.linspace(0.0, 1.0, N, dtype=np.float32)[:, None]
    r = p0*(1.0 - t) + p1*t
    return r.astype(np.float32)


def ring_atoms(M=64, R=2.0, center=(0.0,0.0,0.0), REQ=(1.7, 0.1, 0.0, 0.0)):
    """Place M atoms evenly on a circle in XY plane. Returns positions and REQ params."""
    c = np.array(center, dtype=np.float32)
    t = np.linspace(0.0, 2.0*np.pi, M, endpoint=False, dtype=np.float32)
    x = R*np.cos(t); y = R*np.sin(t)
    r = np.stack([x, y, np.zeros_like(x)], axis=1) + c
    REQs = np.tile(np.array(REQ, dtype=np.float32), (M,1))
    return r.astype(np.float32), REQs.astype(np.float32)


class NumIntegralSim(OpenCLBase):
    def __init__(self, nloc=128, device_index=0):
        super().__init__(nloc=nloc, device_index=device_index)
        self.base_dir    = os.path.dirname(os.path.abspath(__file__))
        self.kernels_dir = os.path.join(self.base_dir, 'kernels')
        self.path_kernel = os.path.join(self.kernels_dir, 'NumIntegral.cl')
        self.path_forces = os.path.join(self.kernels_dir, 'Forces.cl')

    def build_program(self, macros=None, bPrint=False):
        subs = {
            'files': {'Forces': self.path_forces},
            'macros': macros or {}
        }
        src = self.preprocess_opencl_source(self.path_kernel, substitutions=subs, output_path=None, bPrint=bPrint)
        try:
            self.prg = cl.Program(self.ctx, src).build()
        except Exception as e:
            print('Build failed. Kernel source follows:\n' + src)
            raise
        self.kernelheaders = self.extract_kernel_headers(src)
        return True

    @staticmethod
    def to_f4(a):
        a = np.asarray(a, dtype=np.float32)
        if a.ndim != 2 or a.shape[1] < 3:
            raise ValueError(f"to_f4 expects (n,3/4) array, got {a.shape}")
        out = np.zeros((a.shape[0], 4), dtype=np.float32)
        out[:, :3] = a[:, :3]
        if a.shape[1] >= 4:
            out[:, 3] = a[:, 3]
        return out

    def alloc_and_upload(self, src_pos, src_vec, src_f, src_par, samples):
        # Prepare host arrays with float4 alignment
        h_src_pos = self.to_f4(src_pos)
        h_src_vec = self.to_f4(src_vec)
        h_src_f   = src_f.astype(np.float32)
        h_src_par = self.to_f4(src_par)
        h_samples = self.to_f4(samples)
        h_out     = np.zeros((samples.shape[0], 4), dtype=np.float32)
        # Allocate buffers with names matching kernel params
        self.check_buf('src_pos',    h_src_pos.nbytes)
        self.check_buf('src_vec',    h_src_vec.nbytes)
        self.check_buf('src_f',      h_src_f.nbytes)
        self.check_buf('src_par',    h_src_par.nbytes)
        self.check_buf('sample_pos', h_samples.nbytes)
        self.check_buf('out_sum',    h_out.nbytes)
        # Upload
        self.toGPU('src_pos',    h_src_pos)
        self.toGPU('src_vec',    h_src_vec)
        self.toGPU('src_f',      h_src_f)
        self.toGPU('src_par',    h_src_par)
        self.toGPU('sample_pos', h_samples)
        return h_out

    def run_accumulate(self, N, macros, M, REQH0=(0,0,0,0), ffpar=(), K=0.0, bPrint=False):
        # Build specialized program
        self.build_program(macros=macros, bPrint=bPrint)
        # Pack constants
        ffpar_arr = np.asarray(ffpar, dtype=np.float32).ravel()
        if ffpar_arr.size > 8: ffpar_arr = ffpar_arr[:8]
        ffpar8 = np.zeros(8, dtype=np.float32); ffpar8[:ffpar_arr.size] = ffpar_arr
        self.kernel_params = {
            'M':   np.int32(M),
            'N':   np.int32(N),
            'REQH0': cl_array.vec.make_float4(*np.asarray(REQH0, dtype=np.float32)),
            'ffpar': cl_array.vec.make_float8(*ffpar8),
            'K':   np.float32(K),
        }
        # Prepare args and enqueue
        args = self.generate_kernel_args('accumulatePairs', bPrint=bPrint)
        k = self.prg.accumulatePairs
        k.set_args(*args)
        gsz = (self.roundUpGlobalSize(int(N)),)
        lsz = (self.nloc,)
        cl.enqueue_nd_range_kernel(self.queue, k, gsz, lsz)
        self.queue.finish()

    # Example A: Biot–Savart
    def run_biot_savart(self, r_mid, dl, Iarr, samples, K=MU0_4PI, bPrint=False):
        M = r_mid.shape[0]; N = samples.shape[0]
        # src_par unused -> zeros
        src_par = np.zeros((M,4), dtype=np.float32)
        h_out = self.alloc_and_upload(src_pos=r_mid, src_vec=dl, src_f=Iarr, src_par=src_par, samples=samples)
        macros = {
            'GET_PAIR_EXPR': 'contrib = getBiotSavart_dB(-dp, dl, I, K);'
        }
        self.run_accumulate(N=N, macros=macros, M=M, REQH0=(0,0,0,0), ffpar=(), K=K, bPrint=bPrint)
        self.fromGPU('out_sum', h_out)
        return h_out[:, :3]

    # Example B: Non-bonded Morse potential (atoms -> probe points)
    def run_morse_ring(self, apos, aREQs, samples, REQH0=(3.0,1.0,0.0,0.0), bMorse=1.6, variant='Morse', bPrint=False):
        M = apos.shape[0]; N = samples.shape[0]
        # src_vec, src_f unused -> zeros
        src_vec = np.zeros_like(apos)
        src_f   = np.zeros((M,), dtype=np.float32)
        src_par = aREQs
        h_out = self.alloc_and_upload(src_pos=apos, src_vec=src_vec, src_f=src_f, src_par=src_par, samples=samples)
        # Macro builds REQH from per-atom par and global REQH0, and selects Morse variant
        if variant == 'Morse_lin5':
            expr = 'contrib = getMorse_lin5(dp, REQH.x, REQH.y, ffpar.x);'
        elif variant == 'Morse_lin9':
            expr = 'contrib = getMorse_lin9(dp, REQH.x, REQH.y, ffpar.x);'
        elif variant == 'Morse_lin17':
            expr = 'contrib = getMorse_lin17(dp, REQH.x, REQH.y, ffpar.x);'
        else:
            expr = 'contrib = getMorse(dp, REQH.x, REQH.y, ffpar.x);'
        macros = {
            'GET_PAIR_EXPR': (
                '    { float4 REQH=par; REQH.x+=REQH0.x; REQH.yzw*=REQH0.yzw; ' + expr + ' }'
            )
        }
        self.run_accumulate(N=N, macros=macros, M=M, REQH0=REQH0, ffpar=(bMorse,), K=0.0, bPrint=bPrint)
        self.fromGPU('out_sum', h_out)
        return h_out  # xyz = accumulated force, w = accumulated energy


# ----------------------
# Demo
# ----------------------

def main():
    sim = NumIntegralSim(nloc=128)

    # A) Biot–Savart demo
    print("\n=== Biot–Savart (generic kernel) ===")
    r_mid, dl, Iarr = circle_loop(M=512, R=1.0, I=1.0)
    samples = line_samples(N=401, p0=(-2.0,0.0,0.5), p1=(2.0,0.0,0.5))
    B = sim.run_biot_savart(r_mid, dl, Iarr, samples, K=MU0_4PI, bPrint=False)
    print("B field samples (first 5):")
    for i in range(5):
        print(i, samples[i], B[i])
    # Plot |B| along the line
    s = np.linspace(0.0, 1.0, samples.shape[0])
    Bmag = np.linalg.norm(B, axis=1)
    plt.figure(figsize=(7,4))
    plt.plot(s, Bmag, '-k', lw=1.5)
    plt.xlabel('Line parameter')
    plt.ylabel('|B| [T] (units per K,I)')
    plt.title('Biot–Savart: generic kernel')
    plt.grid(True, ls=':')
    plt.tight_layout()

    # B) Non-bonded Morse demo
    print("\n=== Morse non-bonded on ring of atoms (generic kernel) ===")
    apos, aREQs = ring_atoms(M=180, R=2.0, REQ=(1.4, 0.1, 0.0, 0.0))
    probes = line_samples(N=201, p0=(-4.0,0.0,0.0), p1=(4.0,0.0,0.0))
    REQH0 = (3.0, 1.0, 1.0, 1.0)  # combine with per-atom params inside macro
    feats = sim.run_morse_ring(apos, aREQs, probes, REQH0=REQH0, bMorse=1.6, variant='Morse', bPrint=False)
    Es = feats[:,3]
    print("Morse energies (first 5):", Es[:5])
    # Plot Morse energy along the line
    s2 = np.linspace(0.0, 1.0, probes.shape[0])
    plt.figure(figsize=(7,4))
    plt.plot(s2, Es, '-b', lw=1.5)
    plt.xlabel('Line parameter')
    plt.ylabel('Energy (arb)')
    plt.title('Morse energy: generic kernel')
    plt.grid(True, ls=':')
    plt.tight_layout()

    plt.show()


if __name__ == '__main__':
    # How to run:
    #   python -u -m pyCruncher2.scientific.gpu.test_num_integral_cl | tee OUT-generic-integral
    main()
