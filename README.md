# READ ME
This repository is a fork of the repository containing the implementation of the $\ell$-buffered $k$-MinHash data structure, as described in the paper *"Maintaining $k$-MinHash Signatures Over Fully-Dynamic Data Streams with Recovery"*.


The structure of the repository is as follows:
- `src/`: contains all the source code of the project.
- `src/TreeKLMinHash.h`: contains the implementation of the $\ell$-buffered $k$-MinHash data structure.
- `src/DSS.cpp`: contains the implementation of the DSS sketch of ["Similarity Search for Dynamic Data Streams"](https://ieeexplore.ieee.org/abstract/document/8713878). 
- `src/DSSProactive.cpp`: contains the implementation of the proactive DSS sketch of ["Similarity Search for Dynamic Data Streams"](https://ieeexplore.ieee.org/abstract/document/8713878).
- `src/Sketch.cpp`: contains the interface of the sketches.
- `src/hash.cpp`: contains the implementation of the hash functions.
- `src/Utils.cpp`: contains the implementation of the utility functions.
- `src/BitArray.cpp`: implementation of set operations on bit arrays.
- `src/test/`: contains the test files.
- `experiments.cpp`: experiments to evaluate the performance of the $\ell$-buffered $k$-MinHash, DSS and proactive DSS sketches.
- `dataset/dataset.py`: script to generate the dataset used in the experiments.
- `Python/`: scripts to parse experiment outputs and generate comparison plots.
  - `TestVisualizer.py`: plots for fixed updates and sliding-window experiments.
  - `SpeedupAnalyzer.py`: compares DMH and LBBK runtimes and creates reports.
  - `Experiment6Visualizer.py`: RMSE plot for similarity estimation.

# How to compile
To compile the project, run the following command:
```bash
g++ experiments.cpp -O3 -mavx -fopenmp
```

# How to generate plots

The plotting scripts require Python and `matplotlib`. Install the dependency
once with:

```bash
python -m pip install matplotlib
```

Run the scripts from the repository root. By default, they read the output
files listed below and save generated plots and reports under `Python/`.

## Main test visualizer

[`Python/TestVisualizer.py`](Python/TestVisualizer.py) reads
`LBBK_LBKMH_out.txt` and generates plots comparing the dynamic MinHash sketch
(DMH) and L-buffered Bottom-K (LBBK):

```bash
python Python/TestVisualizer.py
```

For memory comparisons, total sketch size is `k*l` for DMH and `l` for LBBK.
The generated images are saved in `Python/plots/`:

- `average_faults_fixed_updates.png`
- `average_time_fixed_updates.png`
- `average_faults_sliding_window.png`
- `average_time_sliding_window.png`
- Raw and normalized variations of the fault and runtime plots

To use another output file or output directory:

```bash
python Python/TestVisualizer.py \
  --input path/to/output.txt \
  --output-dir Python/plots
```

## Average multiplicative speedup

[`Python/SpeedupAnalyzer.py`](Python/SpeedupAnalyzer.py) compares DMH and LBBK
runtime for fixed updates and sliding-window experiments:

```bash
python Python/SpeedupAnalyzer.py
```

It creates Markdown reports under `Python/speedup_reports/`. The default
reports include pairs with `k >= 2000` and `DMH buffer size >= log2(N)`,
matching the same `k` and input size and enforcing equal total sketch memory:
`DMH buffer size * k = LBBK buffer size`. Each report lists the matched
configurations, their mean runtimes, and the geometric mean of per-configuration
speedups `mean(DMH runtime) / mean(LBBK runtime)`. A value greater than 1 means
LBBK is faster. The report summary also includes the arithmetic mean of the
per-configuration mean runtimes for DMH and LBBK, and repeats the aggregate
speedup at the end.

The script additionally creates three fixed-update reports for `k = 2000`,
grouped by DMH buffer size (`10–19`, `20–40`, and `41+`). These band reports
intentionally omit the `l >= log2(N)` filter. Sliding-window band reports are
split first by `k` (`1–99`, `100–999`, `1000–4999`, and `5000+`) and then by
the same DMH buffer bands; they also omit the logarithmic-buffer filter.
Override the default input with `--input` and the report directory with
`--output-dir`.

## Experiment 6 RMSE

[`Python/Experiment6Visualizer.py`](Python/Experiment6Visualizer.py) reads
`SimQE_out.txt` by default, computes RMSE from squared errors, and generates
the similarity-estimation plot:

```bash
python Python/Experiment6Visualizer.py
```

The plot is saved as `Python/plots/experiment_rmse.png`. The visualizer also
supports a custom input and output path:

```bash
python Python/Experiment6Visualizer.py \
  --input path/to/SimQE_out.txt \
  --output Python/plots/experiment_rmse.png
```

The generated `.txt`, `.exe`, cache and PNG files are local experiment
artifacts and are excluded from version control by `.gitignore`.
