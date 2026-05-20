# Full k-Enabled Workflow on a Linux Cluster

This directory contains the Linux x86_64 environment file and setup instructions
for the full LAMMPS+PLUMED workflow.

Use this workflow only if you need PLUMED `ENVIRONMENTSIMILARITY` and the
per-atom local-environment similarity value `k`. If you only need GDS from mass
density, use the top-level [README.md](../README.md) and the top-level
`environment.yml`.

## Can This Run on a Linux Cluster?

Yes. The Python GDS analysis is platform independent. The main care point is
the LAMMPS+PLUMED part:

- LAMMPS and PLUMED should both be no-MPI, or both be built with the same MPI
  stack.
- The conda PLUMED package may not include the `crystallization` module that
  provides `ENVIRONMENTSIMILARITY`.
- For this small two-frame tutorial, a no-MPI LAMMPS plus a no-MPI local PLUMED
  kernel is the simplest robust setup.

For large production trajectories, use cluster-specific LAMMPS and PLUMED
builds that share the same MPI stack.

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

This file pins a Linux no-MPI LAMMPS build that remains compatible with
Python 3.10 and NumPy 1.26:

```text
lammps=2024.08.29=cpu_py310_h6af7cfc_nompi_1
```

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

```bash
mkdir -p src software
curl -L -o src/plumed-2.9.2.tgz \
  https://github.com/plumed/plumed2/releases/download/v2.9.2/plumed-2.9.2.tgz
tar -xzf src/plumed-2.9.2.tgz -C src
cd src/plumed-2.9.2

export CC=${CC:-x86_64-conda-linux-gnu-cc}
export CXX=${CXX:-x86_64-conda-linux-gnu-c++}
export FC=${FC:-x86_64-conda-linux-gnu-gfortran}

./configure \
  --prefix="$PWD/../../software/plumed-envsim-linux" \
  --enable-modules=crystallization

make -j4
make install
cd ../..
```

Verify:

```bash
software/plumed-envsim-linux/bin/plumed manual \
  --action=ENVIRONMENTSIMILARITY | grep ENVIRONMENTSIMILARITY

software/plumed-envsim-linux/bin/plumed config has mpi || true
```

The second command should print `mpi off`. It may return a non-zero exit code
when MPI is off; that is fine.

The PLUMED kernel file on Linux should be:

```text
software/plumed-envsim-linux/lib/libplumedKernel.so
```

If in doubt:

```bash
ls software/plumed-envsim-linux/lib/libplumedKernel.*
```

## 4. Run LAMMPS rerun with PLUMED

```bash
rm -rf runs/example
mkdir -p runs/example
cd runs/example

export PLUMED_KERNEL="$PWD/../../software/plumed-envsim-linux/lib/libplumedKernel.so"
lmp -in ../../input/similarity_in.lammps
```

Successful output should include:

```text
+++ Loading the PLUMED kernel runtime +++
+++ PLUMED_KERNEL=".../libplumedKernel.so" +++
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
MPLBACKEND=Agg python ../../../scripts/plot.py
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
