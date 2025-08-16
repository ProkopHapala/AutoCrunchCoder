import os
import numpy as np
import pyopencl as cl
import matplotlib.pyplot as plt

from .OpenCLBase import OpenCLBase

MU0_4PI = np.float32(1.0e-7)  # SI


def circle_loop(M=256, R=1.0, center=(0.0, 0.0, 0.0), I=1.0):
    """
    Discretize a circular loop in XY plane into M straight segments.
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


class BiotSavartSim(OpenCLBase):
    def __init__(self, nloc=64, device_index=0):
        super().__init__(nloc=nloc, device_index=device_index)
        # Paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.kernels_dir = os.path.join(self.base_dir, 'kernels')
        self.path_biot = os.path.join(self.kernels_dir, 'BiotSavart.cl')
        self.path_forces = os.path.join(self.kernels_dir, 'Forces.cl')

    def build_program(self, macros=None, bPrint=False):
        subs = {
            'files': {'Forces': self.path_forces},
            'macros': macros or {}
        }
        src = self.preprocess_opencl_source(self.path_biot, substitutions=subs, output_path=None, bPrint=bPrint)
        try:
            self.prg = cl.Program(self.ctx, src).build()
        except Exception as e:
            print('Build failed. Kernel source follows:\n' + src)
            raise
        self.kernelheaders = self.extract_kernel_headers(src)
        return True

    def run(self, r_mid, dl, Iarr, samples, K=MU0_4PI, bPrint=False):
        M = np.int32(r_mid.shape[0]); N = np.int32(samples.shape[0])
        # Prepare host arrays as float32/float4 alignment
        def to_f4(a3):
            out = np.zeros((a3.shape[0], 4), dtype=np.float32)
            out[:, :3] = a3.astype(np.float32)
            return out
        h_src_pos = to_f4(r_mid)
        h_src_dl  = to_f4(dl)
        h_src_I   = Iarr.astype(np.float32)
        h_samples = to_f4(samples)
        h_out_B   = np.zeros((samples.shape[0], 4), dtype=np.float32)

        # Allocate buffers (names must match kernel params)
        self.check_buf('src_pos',   h_src_pos.nbytes)
        self.check_buf('src_dl',    h_src_dl.nbytes)
        self.check_buf('src_I',     h_src_I.nbytes)
        self.check_buf('sample_pos',h_samples.nbytes)
        self.check_buf('out_B',     h_out_B.nbytes)

        # Upload
        self.toGPU('src_pos',   h_src_pos)
        self.toGPU('src_dl',    h_src_dl)
        self.toGPU('src_I',     h_src_I)
        self.toGPU('sample_pos',h_samples)

        # Params for kernel
        self.kernel_params = {
            'M': np.int32(M),
            'N': np.int32(N),
            'K': np.float32(K),
        }

        # Ensure program is built
        if self.prg is None:
            self.build_program(bPrint=False)

        # Generate args and enqueue
        args = self.generate_kernel_args('accumulateB', bPrint=bPrint)
        k = self.prg.accumulateB
        k.set_args(*args)
        gsz = (self.roundUpGlobalSize(int(N)),)
        lsz = (self.nloc,)
        cl.enqueue_nd_range_kernel(self.queue, k, gsz, lsz)
        self.queue.finish()

        # Download
        self.fromGPU('out_B', h_out_B)
        return h_out_B[:, :3]


def main():
    # Geometry
    M = 512; R = 1.0; I = 1.0
    N = 401; p0 = (-2.0, 0.0, 0.5); p1 = (2.0, 0.0, 0.5)

    r_mid, dl, Iarr = circle_loop(M=M, R=R, I=I)
    samples = line_samples(N=N, p0=p0, p1=p1)

    sim = BiotSavartSim(nloc=128)
    sim.build_program(bPrint=False)
    B = sim.run(r_mid, dl, Iarr, samples, K=MU0_4PI, bPrint=False)

    # Print few samples
    print('B field samples (first 5):')
    for i in range(5):
        print(i, samples[i], B[i])

    # Plot |B| along the line
    s = np.linspace(0.0, 1.0, samples.shape[0])
    Bmag = np.linalg.norm(B, axis=1)
    plt.figure(figsize=(7,4))
    plt.plot(s, Bmag, '-k', lw=1.5)
    plt.xlabel('Line parameter')
    plt.ylabel('|B| [T] (units per K,I)')
    plt.title('Biot–Savart: circular loop vs line samples')
    plt.grid(True, ls=':')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    # how to run this script
    # python -u -m pyCruncher2.scientific.gpu.run_biot_savart
    main()
