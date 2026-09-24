"""Plot experiments 4 and 5 from experiments_3_4_5_out.txt.

The comparison is between DMH (buffered MinHash) and LBBK (L-buffered
Bottom-K), using the same total sketch size:

    DMH:  k * l
    LBBK: l

Usage:

    python Python/Experiments345Visualizer.py
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Record:
    experiment: int
    sketch: str
    k: int
    l: int
    size: int
    faults: float
    probability: float | None
    seconds: float


def read_records(path: Path) -> list[Record]:
    records: list[Record] = []
    experiment: int | None = None

    with path.open("r", encoding="utf-8") as source:
        for raw_line in source:
            line = raw_line.strip()
            if not line:
                continue

            if "experiment4" in line.lower():
                experiment = 4
                continue
            if "experiment5" in line.lower():
                experiment = 5
                continue
            if experiment is None:
                continue

            row = next(csv.reader([line]))
            values = [value.strip() for value in row]
            if not values or values[0] not in {"DMH", "LBBK", "BottomK"}:
                continue

            try:
                numbers = [float(value) for value in values[1:]]
                if experiment == 4 and len(numbers) == 5:
                    k, l, size, _queries, seconds = numbers
                    records.append(
                        Record(4, values[0], int(k), int(l), int(size), 0, None, seconds)
                    )
                elif experiment == 5 and len(numbers) == 7:
                    k, l, size, _hashes, faults, probability, seconds = numbers
                    records.append(
                        Record(
                            5,
                            values[0],
                            int(k),
                            int(l),
                            int(size),
                            faults,
                            probability,
                            seconds,
                        )
                    )
            except ValueError:
                continue

    return records


def _comparison_records(records: list[Record], experiment: int) -> list[Record]:
    result = []
    for record in records:
        if record.experiment != experiment or record.l <= 0:
            continue
        if record.sketch == "DMH":
            result.append(record)
        elif record.sketch in {"LBBK", "BottomK"}:
            result.append(record)
    return result


def _total_size(record: Record) -> int:
    return record.k * record.l if record.sketch == "DMH" else record.l


def _plot(
    records: list[Record],
    experiment: int,
    metric: str,
    output: Path,
    normalize: bool = False,
) -> bool:
    records = _comparison_records(records, experiment)
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[tuple[str, int], dict[float, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in records:
        if metric == "faults":
            value = record.faults
        else:
            value = record.seconds
        x = float(_total_size(record))
        grouped[(record.sketch, record.k)][x].append(value)

    if not grouped:
        return False

    if experiment == 5:
        sizes_by_sketch = {
            sketch: {_total_size(record) for record in records if record.sketch == sketch}
            for sketch in {"DMH", "LBBK", "BottomK"}
        }
        common_sizes = sizes_by_sketch.get("DMH", set()) & (
            sizes_by_sketch.get("LBBK", set())
            | sizes_by_sketch.get("BottomK", set())
        )
        grouped = {
            key: {
                size: values
                for size, values in points.items()
                if size in common_sizes
            }
            for key, points in grouped.items()
        }
        grouped = {key: points for key, points in grouped.items() if points}

    figure, axis = plt.subplots(figsize=(11, 7))
    for (sketch, k), points in sorted(grouped.items()):
        x = sorted(points)
        means = [statistics.mean(points[value]) for value in x]
        positive_points = [(position, value) for position, value in zip(x, means) if value > 0]
        if not positive_points:
            continue
        x, y = zip(*positive_points)
        label = "MinHash (DMH)" if sketch == "DMH" else "LBBK"
        axis.plot(
            x,
            y,
            marker="o",
            linestyle="--" if sketch == "DMH" else "-",
            label=f"{label}, k={k}",
        )

    if experiment == 4:
        title = "Experiment 4: tempo medio query a parità di size"
        xlabel = "Size totale dello sketch (k*l MinHash, l LBBK)"
    elif metric == "faults":
        title = "Experiment 5: fault medi al variare della size"
        xlabel = "Size totale dello sketch (k*l MinHash, l LBBK)"
    else:
        title = "Experiment 5: tempo medio al variare della size"
        xlabel = "Size totale dello sketch (k*l MinHash, l LBBK)"

    axis.set(
        title=title,
        xlabel=xlabel,
        ylabel="Numero medio di fault" if metric == "faults" else "Tempo medio (s)",
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.grid(True, alpha=0.3)
    axis.legend(ncol=2, fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "experiments_3_4_5_out.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "plots_345",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file di input non trovato: {args.input}")

    try:
        import matplotlib
    except ImportError as error:
        parser.error(f"installare matplotlib con `python -m pip install matplotlib`: {error}")
    matplotlib.use("Agg")

    records = read_records(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    created = [
        _plot(
            records,
            4,
            "time",
            args.output_dir / "experiment4_query_time.png",
        ),
        _plot(
            records,
            5,
            "faults",
            args.output_dir / "experiment5_faults.png",
        ),
        _plot(
            records,
            5,
            "time",
            args.output_dir / "experiment5_time.png",
        ),
    ]
    print(f"Record letti: {len(records)}")
    print(f"Grafici creati: {sum(created)} in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
