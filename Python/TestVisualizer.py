"""Create comparison plots from the CSV-like output produced by experiments.cpp.

Usage from the repository root:

    python Python/TestVisualizer.py

The input and output directory can be overridden with ``--input`` and
``--output-dir``.  The script writes PNG files and does not require changes to
the C++ experiments.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


# Nomi riconosciuti nei dati e regole per distinguere gli sketch.
TIMING_SKETCHES = {
    "BottomK",
    "BufferKLMinhash",
    "MinHash",
    "DSS",
    "DSSp",
    "DMH",
    "LBBK",
}
FIXED_UPDATE_K_VALUES = {1, 100, 1000, 2000}
DMH_NAMES = {"BufferKLMinhash", "MinHash", "DMH"}
LBBK_NAMES = {"BottomK", "LBBK"}


# Record tipizzati: separano il parsing dei dati dalla generazione dei grafici.
@dataclass(frozen=True)
class TimingResult:
    sketch: str
    k: int
    l: int
    size: int
    faults: int
    probability: float | None
    seconds: float


@dataclass(frozen=True)
class SimilarityResult:
    similarity: float
    errors: dict[str, float]


# Lettura dell'output CSV-like: tempi e risultati di stima della similarità.
def _float(value: str) -> float:
    return float(value.strip())


def read_results(
    path: Path,
) -> tuple[list[TimingResult], list[SimilarityResult]]:
    """Read timing records and similarity records, ignoring experiment banners."""

    timings: list[TimingResult] = []
    similarity_names: list[str] = []
    similarities: list[SimilarityResult] = []

    with path.open("r", encoding="utf-8") as source:
        for row in csv.reader(source):
            values = [value.strip() for value in row]
            if not values or not values[0]:
                continue

            if values[0] in TIMING_SKETCHES:
                try:
                    numbers = [_float(value) for value in values[1:]]
                    if len(numbers) == 5:
                        k, l, size, faults, seconds = numbers
                        probability = None
                    elif len(numbers) == 6:
                        k, l, size, _max_size, faults, seconds = numbers
                        probability = None
                        values[0] = f"{values[0]}-window"
                    elif len(numbers) == 7:
                        k, l, size, _hashes, faults, probability, seconds = numbers
                    else:
                        continue
                    timings.append(
                        TimingResult(
                            values[0],
                            int(k),
                            int(l),
                            int(size),
                            int(faults),
                            probability,
                            seconds,
                        )
                    )
                except ValueError:
                    continue
                continue

            if values[0] == "sim":
                # The header names the columns used by the following rows.
                similarity_names = values[1:]
                continue

            if similarity_names and len(values) == len(similarity_names) + 1:
                try:
                    similarities.append(
                        SimilarityResult(
                            _float(values[0]),
                            {
                                name: _float(value)
                                for name, value in zip(
                                    similarity_names, values[1:]
                                )
                            },
                        )
                    )
                except ValueError:
                    continue

    return timings, similarities


# Grafici dei tempi: probabilità di fault, k e dimensione del buffer.
def _median(values: list[float]) -> float:
    return statistics.median(values)


def _plot_timing_by_probability(timings: list[TimingResult], output: Path) -> bool:
    records = [result for result in timings if result.probability is not None]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for result in records:
        grouped[result.sketch][result.probability].append(result.seconds)

    figure, axis = plt.subplots(figsize=(10, 6))
    for sketch, points in sorted(grouped.items()):
        x = sorted(points)
        y = [_median(points[value]) for value in x]
        axis.plot(x, y, marker="o", label=sketch)
    axis.set(
        title="Tempo medio per probabilità di fault",
        xlabel="Probabilità di fault (p)",
        ylabel="Tempo (s, mediana delle ripetizioni)",
    )
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


def _plot_timing_by_k(timings: list[TimingResult], output: Path) -> bool:
    records = [result for result in timings if result.probability is None]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[tuple[str, int], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for result in records:
        grouped[(result.sketch, result.size)][result.k].append(result.seconds)

    figure, axis = plt.subplots(figsize=(11, 7))
    for (sketch, size), points in sorted(grouped.items()):
        x = sorted(points)
        y = [_median(points[value]) for value in x]
        axis.plot(x, y, marker="o", label=f"{sketch} (N={size:,})")
    axis.set(
        title="Confronto dei tempi in funzione di k",
        xlabel="k",
        ylabel="Tempo (s, mediana delle ripetizioni)",
    )
    axis.grid(True, alpha=0.3)
    axis.legend(fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


def _plot_timing_by_l(
    timings: list[TimingResult], sketch: str, title: str, output: Path
) -> bool:
    records = [result for result in timings if result.sketch == sketch]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[int, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for result in records:
        grouped[result.k][result.l].append(result.seconds)

    figure, axis = plt.subplots(figsize=(10, 6))
    for k, points in sorted(grouped.items()):
        x = sorted(points)
        y = [_median(points[value]) for value in x]
        axis.plot(x, y, marker="o", label=f"k={k}")
    axis.set(
        title=title,
        xlabel="Dimensione del buffer (l)",
        ylabel="Tempo (s, mediana delle ripetizioni)",
    )
    axis.grid(True, alpha=0.3)
    axis.set_xscale("symlog", linthresh=1)
    axis.legend(ncol=2, fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


# Grafici di fault, tempi normalizzati e errore di similarità.
def _plot_faults_by_l(timings: list[TimingResult], output: Path) -> bool:
    records = [
        result
        for result in timings
        if result.sketch in DMH_NAMES | LBBK_NAMES
        and result.probability is None
        and result.size == 131072
        and result.k in FIXED_UPDATE_K_VALUES
        and result.l > 0
    ]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[tuple[str, int], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for result in records:
        # MinHash stores k buffers of size l; LBBK stores one buffer of size l.
        total_size = result.k * result.l if result.sketch in DMH_NAMES else result.l
        label = "DMH" if result.sketch in DMH_NAMES else "LBBK"
        grouped[(label, result.k)][total_size].append(result.faults)

    figure, axis = plt.subplots(figsize=(11, 7))
    for (sketch, k), points in sorted(grouped.items()):
        x = sorted(points)
        y = [statistics.mean(points[value]) for value in x]
        style = "-" if sketch == "LBBK" else "--"
        axis.plot(
            x,
            y,
            marker="o",
            linestyle=style,
            label=f"{sketch}, k={k}",
        )
    axis.set(
        title="Fault medi a parità di memoria (fixed update)",
        xlabel="Dimensione totale dello sketch (k*l per DMH, l per LBBK)",
        ylabel="Numero di fault (media)",
        ylim=(0, 30),
    )
    axis.grid(True, alpha=0.3)
    axis.set_xscale("log")
    axis.legend(ncol=2, fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


def _plot_normalized_time_by_l(
    timings: list[TimingResult], output: Path
) -> bool:
    records = [
        result
        for result in timings
        if result.sketch in DMH_NAMES | LBBK_NAMES
        and result.probability is None
        and result.size == 131072
        and result.k in FIXED_UPDATE_K_VALUES
        and result.l > 0
    ]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[tuple[str, int], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for result in records:
        total_size = result.k * result.l if result.sketch in DMH_NAMES else result.l
        label = "DMH" if result.sketch in DMH_NAMES else "LBBK"
        grouped[(label, result.k)][total_size].append(result.seconds)

    figure, axis = plt.subplots(figsize=(11, 7))
    for (sketch, k), points in sorted(grouped.items()):
        x = sorted(points)
        means = [statistics.mean(points[value]) for value in x]
        maximum = max(means)
        normalized = [value / maximum if maximum else 0.0 for value in means]
        style = "-" if sketch == "LBBK" else "--"
        axis.plot(
            x,
            normalized,
            marker="o",
            linestyle=style,
            label=f"{sketch}, k={k}",
        )
    axis.set(
        title="Tempo medio normalizzato a parità di memoria",
        xlabel="Dimensione totale dello sketch (k*l per DMH, l per LBBK)",
        ylabel="Tempo medio normalizzato (massimo della curva = 1)",
        ylim=(0, 1.05),
    )
    axis.grid(True, alpha=0.3)
    axis.set_xscale("log")
    axis.legend(ncol=2, fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


def _plot_similarity(
    similarities: list[SimilarityResult], output: Path
) -> bool:
    if not similarities:
        return False

    import matplotlib.pyplot as plt

    names = list(similarities[0].errors)
    figure, axis = plt.subplots(figsize=(10, 6))
    for name in names:
        points = [
            (result.similarity, result.errors[name])
            for result in similarities
            if name in result.errors
        ]
        grouped: dict[float, list[float]] = defaultdict(list)
        for similarity, error in points:
            grouped[similarity].append(error)
        x = sorted(grouped)
        y = [_median(grouped[value]) for value in x]
        axis.plot(x, y, marker="o", label=name)
    axis.set(
        title="Errore della stima di similarità",
        xlabel="Similarità di Jaccard",
        ylabel="Errore (mediana delle ripetizioni)",
    )
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


# Confronto per memoria totale: DMH usa k*l, LBBK usa l.
def _plot_average_metric_by_size(
    timings: list[TimingResult],
    window: bool,
    metric: str,
    output: Path,
    normalize: bool,
) -> bool:
    """Plot average faults or time against the total sketch size."""

    suffix = "-window" if window else ""
    records = [
        result
        for result in timings
        if result.sketch in {f"MinHash{suffix}", f"BottomK{suffix}"}
        and result.l > 0
    ]
    if not records:
        return False

    import matplotlib.pyplot as plt

    grouped: dict[tuple[str, int], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for result in records:
        sketch = "DMH" if result.sketch.startswith("MinHash") else "LBBK"
        total_size = result.k * result.l if sketch == "DMH" else result.l
        value = result.faults if metric == "faults" else result.seconds
        grouped[(sketch, result.k)][total_size].append(value)

    maxima_by_k: dict[int, float] = {}
    if normalize:
        for (_, k), points in grouped.items():
            maximum = max(
                (statistics.mean(values) for values in points.values()),
                default=0.0,
            )
            maxima_by_k[k] = max(maxima_by_k.get(k, 0.0), maximum)

    figure, axis = plt.subplots(figsize=(11, 7))
    for (sketch, k), points in sorted(grouped.items()):
        x = sorted(points)
        means = [statistics.mean(points[size]) for size in x]
        if normalize:
            maximum = maxima_by_k[k]
            y = [value / maximum if maximum else 0.0 for value in means]
        else:
            y = means
        linestyle = "--" if sketch == "DMH" else "-"
        axis.plot(
            x,
            y,
            marker="o",
            linestyle=linestyle,
            label=f"{sketch}, k={k}",
        )

    phase = "sliding window" if window else "fixed update"
    if metric == "faults":
        title = f"Fault medi{' normalizzati' if normalize else ''} - {phase}"
        ylabel = (
            "Fault medi normalizzati (massimo per k = 1)"
            if normalize
            else "Numero medio di fault"
        )
    else:
        title = f"Tempo medio{' normalizzato' if normalize else ''} - {phase}"
        ylabel = (
            "Tempo medio normalizzato (massimo per k = 1)"
            if normalize
            else "Tempo medio (s)"
        )
    axis.set(
        title=title,
        xlabel="Dimensione totale dello sketch (k*l DMH, l LBBK)",
        ylabel=ylabel,
    )
    axis.set_xscale("log")
    if normalize:
        axis.set_ylim(0, 1.05)
    elif metric == "faults":
        axis.set_ylim(bottom=0, top=50)
    axis.grid(True, alpha=0.3)
    axis.legend(ncol=2, fontsize="small")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return True


# Avvio da terminale e selezione degli otto grafici da produrre.
def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "LBBK_LBKMH_out.txt",
        help="file prodotto dagli esperimenti (default: LBBK_LBKMH_out.txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "plots",
        help="cartella in cui salvare i PNG",
    )
    parser.add_argument("--show", action="store_true", help="mostra i grafici")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file di input non trovato: {args.input}")

    try:
        import matplotlib
    except ImportError as error:
        parser.error(
            "dipendenza mancante: installare matplotlib con "
            f"`python -m pip install matplotlib` ({error})"
        )
    if not args.show:
        matplotlib.use("Agg")

    timings, similarities = read_results(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    created = [
        _plot_average_metric_by_size(
            timings,
            window=False,
            metric="faults",
            output=args.output_dir / "average_faults_fixed_updates.png",
            normalize=True,
        ),
        _plot_average_metric_by_size(
            timings,
            window=False,
            metric="time",
            output=args.output_dir / "average_time_fixed_updates.png",
            normalize=True,
        ),
        _plot_average_metric_by_size(
            timings,
            window=True,
            metric="faults",
            output=args.output_dir / "average_faults_sliding_window.png",
            normalize=True,
        ),
        _plot_average_metric_by_size(
            timings,
            window=True,
            metric="time",
            output=args.output_dir / "average_time_sliding_window.png",
            normalize=True,
        ),
        _plot_average_metric_by_size(
            timings,
            window=False,
            metric="faults",
            output=args.output_dir / "average_faults_fixed_updates_raw.png",
            normalize=False,
        ),
        _plot_average_metric_by_size(
            timings,
            window=False,
            metric="time",
            output=args.output_dir / "average_time_fixed_updates_raw.png",
            normalize=False,
        ),
        _plot_average_metric_by_size(
            timings,
            window=True,
            metric="faults",
            output=args.output_dir / "average_faults_sliding_window_raw.png",
            normalize=False,
        ),
        _plot_average_metric_by_size(
            timings,
            window=True,
            metric="time",
            output=args.output_dir / "average_time_sliding_window_raw.png",
            normalize=False,
        ),
    ]
    print(f"Record di tempo letti: {len(timings)}")
    print(f"Record di similarità letti: {len(similarities)}")
    print(f"Grafici creati: {sum(created)} in {args.output_dir}")

    if args.show:
        import matplotlib.pyplot as plt

        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())