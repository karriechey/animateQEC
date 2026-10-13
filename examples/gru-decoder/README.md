# GRU decoder example

Data in `data/` is exported from the FNAL-AI4QC-GRU research repo.

| file | exporter | FNAL commit |
|---|---|---|
| `viz_data.json`, `svg/detector_{Z,X}_t1.svg` | `scripts/export_viz_data.py` (default args: d=9, p=0.004, rounds=9, seed 2026, 1M-shot MWPM-failure search) | `7c73369` |

Circuit: `circuit_generators.build_circuit(9, 0.004, rounds=9)`, Stim's `surface_code:rotated_memory_z` with all four noise channels at p. Stim 1.16.0.

Samples (`pick` field): five readable shots (fewest events, 4 to 27) and the fewest-event MWPM failure from the first 20k shots (7858, 33 events); the fewest-event failure in 1M shots of the same sampler (281049, 23 events). None of these is the RealShot shot, which comes from the eval block.
