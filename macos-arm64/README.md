# Full k-Enabled Workflow on macOS arm64

This directory contains the Apple Silicon macOS environment file and setup
instructions for the full LAMMPS+PLUMED workflow.

Use this workflow only if you need PLUMED `ENVIRONMENTSIMILARITY` and the
per-atom local-environment similarity value `k`. If you only need GDS from mass
density, use the top-level [README.md](../README.md) and the top-level
`environment.yml`.

## What This Workflow Adds

Compared with the mass-only path, the full workflow starts from:

```text
../input/conf.lmp
../input/npt.dump
../input/env1.pdb
../input/plumed.dat
../input/similarity_in.lammps
```

and generates the run outputs:

```text
../runs/example/COLVAR
../runs/example/refmg-local.xyz
../runs/example/refsi-local.xyz
../runs/example/refo-local.xyz
../runs/example/reffe-local.xyz
../runs/example/merge.xyz
```

The generated `merge.xyz` contains `species, x, y, z, k`. You can then run
`stat.py -m mass` or, if appropriate for your analysis, `stat.py -m k`.

The reference result in this tutorial uses `stat.py -m mass`.

## 1. Create the Conda Environment

Start in this directory:

```bash
cd GDS-tutorial/macos-arm64
conda env create -p ../software/conda-env-full-macos-arm64 -f environment.yml
conda activate ../software/conda-env-full-macos-arm64
cd ..
```

Check the core packages:

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

This environment uses a no-MPI LAMMPS build. That is sufficient for this small
two-frame tutorial and avoids MPI/no-MPI runtime mismatches.

## 2. Install Jie Deng's Modified pytim

From the top-level `GDS-tutorial/` directory:

```bash
mkdir -p src software runs
git clone https://github.com/neojie/pytim.git src/pytim
cd src/pytim
python setup.py install
cd ../..
```

If the repository already exists:

```bash
cd src/pytim
git pull
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

The conda PLUMED package may not include the `crystallization` module that
contains `ENVIRONMENTSIMILARITY`. Build a local PLUMED kernel:

```bash
mkdir -p src software
curl -L -o src/plumed-2.9.2.tgz \
  https://github.com/plumed/plumed2/releases/download/v2.9.2/plumed-2.9.2.tgz
tar -xzf src/plumed-2.9.2.tgz -C src
cd src/plumed-2.9.2

export CC=${CC:-arm64-apple-darwin20.0.0-clang}
export CXX=${CXX:-arm64-apple-darwin20.0.0-clang++}
export FC=${FC:-arm64-apple-darwin20.0.0-gfortran}

./configure \
  --prefix="$PWD/../../software/plumed-envsim-macos-arm64" \
  --enable-modules=crystallization

make -j4
make install
cd ../..
```

Verify the action and MPI mode:

```bash
software/plumed-envsim-macos-arm64/bin/plumed manual \
  --action=ENVIRONMENTSIMILARITY | grep ENVIRONMENTSIMILARITY

software/plumed-envsim-macos-arm64/bin/plumed config has mpi || true
```

The second command should print `mpi off`. It may return a non-zero exit code
when MPI is off; that is fine.

## 4. Run LAMMPS rerun with PLUMED

```bash
rm -rf runs/example
mkdir -p runs/example
cd runs/example

export PLUMED_KERNEL="$PWD/../../software/plumed-envsim-macos-arm64/lib/libplumedKernel.dylib"
lmp -in ../../input/similarity_in.lammps
```

The beginning of the LAMMPS output should include:

```text
+++ Loading the PLUMED kernel runtime +++
+++ PLUMED_KERNEL=".../libplumedKernel.dylib" +++
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
