# Data loading performance

[Project documentation](README.md) · [Dataset guide](../user/datasets.md)

Version 0.7.0 added a full JSON Schema traversal of data before decoding, on top
of Dataset's value checks. Version 0.7.1 replaces that traversal with a concrete
decoder using cached key/type metadata from the unchanged schema. Dataset checks
each decoded value once; binding retains its native checks and caller limits.
The [decision](decisions/yaml-and-json-schema.md) explains the boundary.

## Reproduce

Run the same script with each installed package version, outside its source tree:

```sh
/path/to/venv/bin/python -I /path/to/cardreport/scripts/benchmark_loading.py
```

The script defaults to seven repeats and both JSON/YAML; `--format json` or
`--format yaml` selects one. It emits JSON Lines with every sample, medians,
package/Python/platform versions and the SHA-256 of each input. It uses synthetic
1000-row, 100-column tables: integers, or a mix of Decimal/date/aware datetime.
Each column has one fixed declared type. The bound template declares all columns
and has no report blocks, so bind timing excludes rendering.

Imports, data creation, serialization and garbage collection are outside timing.
Each repeat measures loading and then binding separately; load+bind medians use
the sum of each paired sample. All seven samples are retained, including the
first. A round-trip assertion runs outside timing. No timing threshold is part
of CI; ordinary tests assert value preservation and one value check per cell.

## Local comparison

The release verification records the measured results here. These are local
measurements under normal desktop activity, not a cross-platform throughput
promise. YAML still pays for the unchanged safe parser and resource guards.

Measured on macOS 27.2 ARM64, Python 3.12.3, on 2026-11-05. Published 0.6.0 and
0.7.0 were installed in isolated environments; 0.7.1 used the candidate checkout.
Versions ran sequentially. Input hashes matched across all three versions.

Median load time, seconds (100,000 cells, seven repetitions):

| Format / cells | 0.6.0 | 0.7.0 | 0.7.1 |
| --- | ---: | ---: | ---: |
| JSON / numeric | 0.137 | 1.961 | 0.072 |
| JSON / typed | 0.414 | 6.523 | 0.290 |
| YAML / numeric | 9.090 | 11.100 | 9.129 |
| YAML / typed | 28.500 | 34.948 | 28.529 |

Median load + bind time, seconds:

| Format / cells | 0.6.0 | 0.7.0 | 0.7.1 |
| --- | ---: | ---: | ---: |
| JSON / numeric | 0.179 | 2.005 | 0.114 |
| JSON / typed | 0.478 | 6.595 | 0.358 |
| YAML / numeric | 9.129 | 11.144 | 9.172 |
| YAML / typed | 28.567 | 35.017 | 28.593 |

The JSON regression is removed, with lower load times than 0.6.0 in these cases.
YAML returns approximately to the 0.6.0 baseline; its parsing cost dominates.
These measurements do not cover file I/O, small-file startup or PDF rendering.
