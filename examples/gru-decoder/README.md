# GRU decoder example

Data in `data/` is exported from the FNAL-AI4QC-GRU research repo.

| file | exporter | FNAL commit |
|---|---|---|
| `viz_data.json`, `svg/detector_{Z,X}_t1.svg` | `scripts/export_viz_data.py` (default args: d=9, p=0.004, rounds=9, seed 2026) | `7c73369` |

Circuit: `circuit_generators.build_circuit(9, 0.004, rounds=9)`, Stim's `surface_code:rotated_memory_z` with all four noise channels at p. Stim 1.16.0.
