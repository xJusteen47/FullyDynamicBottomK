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
  - `Experiments345Visualizer.py`: plots for experiments 3, 4 and 5.
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
files listed below and save PNG images under `Python/plots/` or
`Python/plots_345/`.

## Main test visualizer

[`Python/TestVisualizer.py`](Python/TestVisualizer.py) reads `output2.txt` and
generates four plots comparing MinHash and L-buffered Bottom-K at equal
sketch memory:

```bash
python Python/TestVisualizer.py
```

The total sketch size is `k*l` for MinHash and `l` for Bottom-K. The generated
images are:

- `average_faults_fixed_updates.png`
- `average_time_fixed_updates.png`
- `average_faults_sliding_window.png`
- `average_time_sliding_window.png`

To use another output file or output directory:

```bash
python Python/TestVisualizer.py \
  --input path/to/output.txt \
  --output-dir Python/plots
```

## Experiments 3, 4 and 5

[`Python/Experiments345Visualizer.py`](Python/Experiments345Visualizer.py)
reads `experiments_3_4_5_out.txt`:

```bash
python Python/Experiments345Visualizer.py
```

It generates plots for query time in experiment 4 and fault/time results in
experiment 5. The plots are saved in `Python/plots_345/`.

## Experiment 6 RMSE

[`Python/Experiment6Visualizer.py`](Python/Experiment6Visualizer.py) reads
`SimQE_Plus_out.txt`, computes the RMSE from the squared errors, and generates
the similarity-estimation plot:

```bash
python Python/Experiment6Visualizer.py
```

The plot is saved as `Python/plots_345/experiment6_rmse.png`. The visualizer
also supports a custom input and output path:

```bash
python Python/Experiment6Visualizer.py \
  --input path/to/SimQE_Plus_out.txt \
  --output Python/plots_345/experiment6_rmse.png
```

The generated `.txt`, `.exe`, cache and PNG files are local experiment
artifacts and are excluded from version control by `.gitignore`.
