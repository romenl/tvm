import tvm
import numpy as np

def test_add():
    # graph
    n = tvm.convert(1024)
    A = tvm.placeholder((n,), name='A')
    B = tvm.placeholder((n,), name='B')
    C = tvm.compute(A.shape, lambda *i: A(*i) + B(*i), name='C')
    # schedule
    s = tvm.Schedule(C.op)
    # create iter var and assign them tags.
    num_thread = 256
    block_x = tvm.thread_axis(None, "blockIdx.x")
    thread_x = tvm.thread_axis((0, num_thread), "threadIdx.x")
    _, x = s[C].split(C.op.axis[0], factor=num_thread*4, outer=block_x)
    _, x = s[C].split(x, outer=thread_x)
    _, x = s[C].split(x, factor=4)
    s[C].vectorize(x)

    # one line to build the function.
    def check_device(device, host="stackvm"):
        if not tvm.codegen.enabled(host):
            print("skip because %s is not enabled.." % host)
            return
        if not tvm.codegen.enabled(device):
            print("skip because %s is not enabled.." % device)
            return
        fadd = tvm.build(s, [A, B, C],
                         device, host,
                         name="myadd")
        ctx = tvm.gpu(0) if device == "cuda" else tvm.cl(0)
        # launch the kernel.
        n = 1024
        a = tvm.nd.array(np.random.uniform(size=n).astype(A.dtype), ctx)
        b = tvm.nd.array(np.random.uniform(size=n).astype(B.dtype), ctx)
        c = tvm.nd.array(np.zeros(n, dtype=C.dtype), ctx)
        fadd(a, b, c)
        np.testing.assert_allclose(
            c.asnumpy(), a.asnumpy() + b.asnumpy())

    if tvm.module.enabled("opencl"):
        tvm.module.init_opencl()
    check_device("cuda", "llvm")
    check_device("opencl")


if __name__ == "__main__":
    test_add()