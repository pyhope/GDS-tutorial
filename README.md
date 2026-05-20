# Gibbs Dividing Surface Tutorial

This tutorial demonstrates a practical Gibbs Dividing Surface (GDS) workflow for
analyzing element partitioning across coexisting solid and liquid phases. It is
adapted from Haiyang Luo's GDS tutorial and reorganized for public GitHub use.

There are two supported ways to run the example:

1. **Mass-only GDS, recommended first.** Start directly from an extended XYZ file
   containing only species, coordinates, and the periodic cell. This path does
   not require LAMMPS, PLUMED, or any environment-similarity `k` values.
2. **Full k-enabled workflow.** Run LAMMPS `rerun` with PLUMED
   `ENVIRONMENTSIMILARITY`, generate per-atom local-environment similarity
   values, merge those outputs into a generated `merge.xyz`, and then run the
   same GDS analysis.

If you only need mass-density GDS analysis, use this top-level tutorial. If you
need the full workflow with `k`, use the platform-specific instructions:

- [macos-arm64/README.md](macos-arm64/README.md)
- [linux-cluster/README.md](linux-cluster/README.md)

## Important: Mass Mode Does Not Need k

The most important practical point is:

```bash
python scripts/similarity/stat.py -nw 2 -m mass -f input/mass_only_example.xyz
```

does **not** need the input XYZ file to contain a `k` column. In `mass` mode,
`stat.py` uses atomic masses as the density-field weights. The PLUMED-generated
`k` values are only needed if you explicitly run `stat.py -m k`, or if you want
to inspect local environment similarity itself.

Therefore, the mass-only input can be any extended XYZ file with species,
coordinates, and a cell. For example:

```text
34816
Lattice="59.03 0 0 0 59.03 0 0 0 59.03" Properties=species:S:1:pos:R:3
Mg 0.356578 15.111200 39.456800
...
```

A generated full-workflow XYZ file, often called `merge.xyz`, may also include
`k`:

```text
34816
Lattice="59.03 0 0 0 59.03 0 0 0 59.03" Properties=species:S:1:pos:R:3:k:R:1
Mg 0.356578 15.111200 39.456800 0.83
...
```

`stat.py -m mass` ignores the `k` column, so both forms are valid for mass-only
GDS.

## What the Example Represents

The example is a trimmed Mg-Si-O-Fe two-phase coexistence trajectory. The system
composition is:

```text
Fe5632 Mg6144 O17408 Si5632
```

The full input trajectory, `input/npt.dump`, contains only two frames at LAMMPS
timesteps 1500000 and 1501000. The purpose of this small example is not to
produce statistically meaningful averages; it is a compact reproducibility test
for the workflow and output files.

For the mass-only path, this repository includes:

```text
input/mass_only_example.xyz
```

This file contains the same two frames with species, coordinates, and cell
information, but no `k` values. It lets you start directly from `stat.py`.

For the full k-enabled path, the relevant inputs are:

- `input/conf.lmp`: LAMMPS data file.
- `input/npt.dump`: trajectory used by LAMMPS `rerun`.
- `input/env1.pdb`: reference local environment for PLUMED.
- `input/plumed.dat`: PLUMED input using `ENVIRONMENTSIMILARITY`.
- `input/similarity_in.lammps`: LAMMPS rerun input.

## Repository Layout

```text
GDS-tutorial/
├── README.md
├── environment.yml                  # mass-only environment
├── macos-arm64/
│   ├── README.md                    # full k-enabled workflow on Apple Silicon
│   └── environment.yml
├── linux-cluster/
│   ├── README.md                    # full k-enabled workflow on Linux clusters
│   └── environment.yml
├── input/
│   ├── mass_only_example.xyz
│   ├── conf.lmp
│   ├── npt.dump
│   ├── env1.pdb
│   ├── plumed.dat
│   └── similarity_in.lammps
├── scripts/
│   ├── plot.py
│   └── similarity/
│       ├── merge_mgsiofe.py
│       ├── stat.py
│       ├── gds_analyzer.py
│       └── stat_lib_base.py
├── src/                             # created/used for downloaded source trees
├── software/                        # local conda envs and local PLUMED installs
└── runs/                            # reproducible outputs
```

`software/`, downloaded source trees under `src/`, and run outputs under
`runs/` are intentionally ignored by Git. They are reproducible from the
instructions below.

## Quick Start: Mass-Only GDS

From this `GDS-tutorial/` directory:

```bash
mkdir -p software src runs
conda env create -p "$PWD/software/conda-env-mass" -f environment.yml
conda activate "$PWD/software/conda-env-mass"
```

Install Jie Deng's modified `pytim`:

```bash
git clone https://github.com/neojie/pytim.git src/pytim
cd src/pytim
python setup.py install
cd ../..
```

Check the installation:

```bash
python - <<'PY'
import pytim
print("pytim", getattr(pytim, "__version__", "unknown"))
print("file", pytim.__file__)
print("has WillardChandler", hasattr(pytim, "WillardChandler"))
PY
```

Run the mass-only example:

```bash
rm -rf runs/mass_only
mkdir -p runs/mass_only/nw2
cd runs/mass_only/nw2

python ../../../scripts/similarity/stat.py \
  -nw 2 \
  -m mass \
  -f ../../../input/mass_only_example.xyz

MPLBACKEND=Agg python ../../../scripts/plot.py
```

The key summary file is:

```text
runs/mass_only/nw2/sum_proximity_0_1.txt
```

Expected values:

```text
# ../../../input/mass_only_example.xyz
#  nw = 2
#  solid liquid interface
#  id O           Mg           Si           Fe          lw      chi
0 910 13195 3303    7 5309 828    678 3889 1065    3088 156 2388        7.1419    0.0198
1 895 13226 3287    8 5313 823    683 3891 1058    3066 159 2407        7.1188    0.0205
```

## Output Files

### `sum_proximity_0_1.txt`

This is usually the most useful summary. It classifies atoms by their signed
distance to the instantaneous interface, i.e. their proximity. For each element,
the three columns are:

```text
solid_count liquid_count interface_count
```

The last two columns are:

- `lw`: interface width from the proximity-density fit. With `-nw 2`, the
  interface region is taken as `2 * w`.
- `chi`: reduced chi-square of the single-sided GDS fit.

### `sum_counts_0_1.txt`

Element counts from the planar, double-sided GDS fit along the projection axis,
which is the z axis by default. For rough or curved interfaces, the
proximity-based summary is usually more interpretable.

### `sum_dimensions_0_1.txt`

Geometric quantities from the planar GDS fit:

```text
id, ls, ll, lw, lx, ly, lz, z0, z1_unpbc, chi
```

Here `ls` and `ll` are the solid and liquid slab thicknesses, `lw` is the planar
GDS interface width, and `z0`/`z1_unpbc` are the two fitted interface positions.

### `prox.xyz`

An XYZ file containing a per-atom phase label. The final property is still named
`k` by the original script, but in this file it means a phase label:

- `0`: interface
- `1`: one side of the interface
- `2`: the other side of the interface

### `prox.png`

The proximity-density profile and the fitted interface region.

### `gds.png`

The planar mass-density profile and the fitted double-sided GDS curve.

### `elemental_evolution.pdf`

A compact plot of element counts in solid, liquid, and interface regions, plus
`lw` and `chi`. This two-frame example is mainly a plotting and workflow check.

## Running Your Own File

For your own mass-only GDS analysis, prepare an extended XYZ with species,
positions, and cell information, then run:

```bash
python scripts/similarity/stat.py -nw 2 -m mass -f path/to/your_mass_only.xyz
```

Common options:

- `-nw`: interface-width multiplier. This tutorial uses `2`.
- `-m`: weighting mode, either `mass` or `k`.
- `-p`: projection axis, `0`, `1`, or `2` for x, y, or z. The default is z.
- `-b`, `-e`, `-s`: begin frame, end frame, and stride.

## Full k-Enabled Workflow

The full workflow computes PLUMED `ENVIRONMENTSIMILARITY` first, then creates
`runs/example/merge.xyz` with `species, x, y, z, k`. That file is generated by
the platform-specific instructions; it is not stored as a top-level input file
in this trimmed tutorial. Use the full workflow if you need local environment
similarity diagnostics or want to try `stat.py -m k`.

Open the platform-specific directory:

- [macos-arm64/](macos-arm64/)
- [linux-cluster/](linux-cluster/)

Each directory contains a rendered `README.md` and a matching `environment.yml`.

## Version Notes

The mass-only environment pins conservative versions for the old scripts:

```text
python=3.10
numpy=1.26
pandas=2.2
mdanalysis=2.8
cython<3
setuptools<81
```

`cython<3` avoids build issues in older Cython extensions. `setuptools<81`
keeps `pkg_resources` available for the current Jie-modified `pytim` code.

## Acknowledgement

This tutorial is adapted from Haiyang Luo's GDS tutorial. The workflow was
reorganized to make the mass-only path and the full LAMMPS+PLUMED path easier
to reproduce on macOS and Linux. It uses Jie Deng's modified `pytim` fork:

```text
https://github.com/neojie/pytim.git
```
