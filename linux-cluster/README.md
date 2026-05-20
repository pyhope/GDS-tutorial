# Full k-Enabled Workflow on a Linux Cluster

This directory contains the Linux x86_64 environment file and setup instructions
for the full LAMMPS+PLUMED workflow.

Use this workflow only if you need PLUMED `ENVIRONMENTSIMILARITY` and the
per-atom local-environment similarity value `k`. If you only need GDS from mass
density, use the top-level [README.md](../README.md) and the top-level
`environment.yml`.

The tested Linux route is:

- use conda to install Python, no-MPI LAMMPS, and compilers;
- build a local no-MPI PLUMED kernel with the `crystallization` module;
- explicitly point LAMMPS to that local kernel with `PLUMED_KERNEL`.

The local PLUMED build disables optional external libraries that are not needed
for this tutorial. This avoids cluster-specific link-time issues with GSL, FFTW,
BLAS/LAPACK, zlib, and OpenMP.

## 1. Create the Conda Environment

Start in this directory:

```bash
cd GDS-tutorial/linux-cluster
conda env create -p ../software/conda-env-full-linux -f environment.yml
conda activate ../software/conda-env-full-linux
cd ..
```

If conda solving is slow on your cluster, use `mamba` or `micromamba` with the
same `environment.yml`.

Check the environment:

```bash
python --version
python - <<'PY'
import numpy, pandas, MDAnalysis
print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("MDAnalysis", MDAnalysis.__version__)
PY
lmp -h | grep -i plumed
```

## 2. Install Jie Deng's Modified pytim

From the top-level `GDS-tutorial/` directory:

```bash
mkdir -p src software runs
git clone https://github.com/neojie/pytim.git src/pytim
cd src/pytim
python setup.py install
cd ../..
```

Check:

```bash
python - <<'PY'
import pytim
print("pytim", getattr(pytim, "__version__", "unknown"))
print("file", pytim.__file__)
print("has WillardChandler", hasattr(pytim, "WillardChandler"))
PY
```

## 3. Build PLUMED with the crystallization Module

From the top-level `GDS-tutorial/` directory:

```bash
mkdir -p src software
rm -rf src/plumed-2.9.2 software/plumed-envsim-linux
curl -L -o src/plumed-2.9.2.tgz \
  https://github.com/plumed/plumed2/releases/download/v2.9.2/plumed-2.9.2.tgz
tar -xzf src/plumed-2.9.2.tgz -C src
cd src/plumed-2.9.2

export CC=${CC:-x86_64-conda-linux-gnu-cc}
export CXX=${CXX:-x86_64-conda-linux-gnu-c++}
export FC=${FC:-x86_64-conda-linux-gnu-gfortran}

./configure \
  --prefix="$PWD/../../software/plumed-envsim-linux" \
  --enable-modules=crystallization \
  --disable-mpi \
  --disable-openmp \
  --disable-external-blas \
  --disable-external-lapack \
  --disable-gsl \
  --disable-fftw \
  --disable-zlib

make -j16
make install
cd ../..
```

Verify the local kernel directly:

```bash
export LOCAL_PLUMED_LIB="$PWD/software/plumed-envsim-linux/lib"
export PLUMED_KERNEL="$LOCAL_PLUMED_LIB/libplumedKernel.so"
export LD_LIBRARY_PATH="$LOCAL_PLUMED_LIB:${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH:-}"

test -f "$PLUMED_KERNEL" && echo "$PLUMED_KERNEL"
ldd "$PLUMED_KERNEL" | grep "not found" || true
grep -a -o -m 1 "ENVIRONMENTSIMILARITY" "$PLUMED_KERNEL"
```

The `ldd` command should print nothing. The `grep -a` command should print a
single line:

```text
ENVIRONMENTSIMILARITY
```

## 4. Run LAMMPS rerun with PLUMED

```bash
rm -rf runs/example
mkdir -p runs/example
cd runs/example

export PLUMED_KERNEL="$PWD/../../software/plumed-envsim-linux/lib/libplumedKernel.so"
export LD_LIBRARY_PATH="$PWD/../../software/plumed-envsim-linux/lib:${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH:-}"

lmp -in ../../input/similarity_in.lammps
```

Successful output should include:

```text
+++ Loading the PLUMED kernel runtime +++
+++ PLUMED_KERNEL=".../software/plumed-envsim-linux/lib/libplumedKernel.so" +++
```

`COLVAR` should contain two frames:

```text
#! FIELDS time refmg.morethan refsi.mean refsi.morethan reffe.mean reffe.morethan refo.mean refo.morethan
1500.000000 4547.730526 0.484441 3168.230605 0.225137 294.435617 0.431312 4732.679532
1501.000000 4605.811501 0.485705 3198.301597 0.224970 304.272589 0.432308 4760.098354
```

## 5. Merge PLUMED Outputs and Run GDS

From `runs/example/`:

```bash
python ../../scripts/similarity/merge_mgsiofe.py

mkdir -p nw2
cd nw2
python ../../../scripts/similarity/stat.py -nw 2 -m mass -f ../merge.xyz
python ../../../scripts/plot.py
```

Check:

```bash
cat sum_proximity_0_1.txt
```

Expected values:

```text
0 910 13195 3303    7 5309 828    678 3889 1065    3088 156 2388        7.1419    0.0198
1 895 13226 3287    8 5313 823    683 3891 1058    3066 159 2407        7.1188    0.0205
```
