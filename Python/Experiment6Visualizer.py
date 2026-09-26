"""Plot RMSE results from experiment 6.

The C++ experiment writes squared errors, one row per repetition.  This
script aggregates those rows by true Jaccard similarity and computes:

    RMSE = sqrt(mean(squared errors))

For DSS and LBBK it also displays the standard deviation around the RMSE.
Diagnostic ``bottomk_sizes`` rows from the extended output are ignored.

Usage:

    python Python/Experiment6Visualizer.py
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


# Etichette mostrate nel grafico e metodi da escludere.
EXCLUDED_METHODS = {"LBBK_Cohen", "Cohen", "Tau", "tau"}
METHOD_LABELS = {
    "DMH": "DMH",
    "DSS": "DSS",
    "min_hash": "MinHash",
    "LBBK": "LBBK",
}


# Lettura input: raggruppa per similarità gli errori quadratici di ogni metodo.
def read_squared_errors(
    path: Path,
) -> tuple[list[str], dict[float, dict[str, list[float]]]]:
    """Read ``sim,method,...`` rows and group squared errors by similarity."""

    methods: list[str] = []
    grouped: dict[float, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    with path.open("r", encoding="utf-8") as source:
        for row in csv.reader(source):
            values = [value.strip() for value in row]
            if not values:
                continue
            if values[0] == "sim":
                methods = values[1:]
                continue
            if not methods or len(values) != len(methods) + 1:
                continue
            try:
                similarity = float(values[0])
                for method, value in zip(methods, values[1:]):
                    grouped[similarity][method].append(float(value))
            except ValueError:
                continue

    return methods, dict(grouped)


# Grafico: converte gli errori quadratici in RMSE e aggiunge le bande di deviazione.
def plot_rmse(
    methods: list[str],
    grouped: dict[float, dict[str, list[float]]],
    output: Path,
) -> int:
    import matplotlib.pyplot as plt

    similarities = sorted(grouped)
    figure, axis = plt.subplots(figsize=(10, 6))
    plotted = 0
    band_methods = {"DSS", "LBBK"}

    displayed_methods = [
        method for method in methods if method not in EXCLUDED_METHODS
    ]
    plotted_values: list[float] = []

    for method in displayed_methods:
        points: list[tuple[float, float]] = []
        standard_deviations: list[float] = []
        for similarity in similarities:
            errors = grouped[similarity].get(method, [])
            if not errors:
                continue
            mean_squared_error = statistics.mean(errors)
            rmse = math.sqrt(mean_squared_error)
            if len(errors) > 1:
                # The file stores squared errors; use absolute errors for the
                # standard-deviation band around the RMSE curve.
                absolute_errors = [math.sqrt(error) for error in errors]
                standard_deviation = statistics.stdev(absolute_errors)
            else:
                standard_deviation = 0.0
            if rmse > 0:
                points.append((similarity, rmse))
                standard_deviations.append(standard_deviation)
        if not points:
            continue
        x, y = zip(*points)
        plotted_values.extend(y)
        axis.plot(
            x,
            y,
            marker="o",
            linewidth=1.8,
            label=METHOD_LABELS.get(method, method),
        )
        if method in band_methods:
            lower = [
                max(0.0, value - deviation)
                for value, deviation in zip(y, standard_deviations)
            ]
            upper = [
                value + deviation
                for value, deviation in zip(y, standard_deviations)
            ]
            axis.fill_between(
                x,
                lower,
                upper,
                alpha=0.18,
                linewidth=0,
                label=f"{METHOD_LABELS.get(method, method)} ± deviazione standard",
            )
        plotted += 1

    if not plotted:
        plt.close(figure)
        return 0

    upper_y = max(plotted_values, default=1.0)
    axis.set(
        title="Experiment 6: RMSE della stima di similarità",
        xlabel="Similarità di Jaccard",
        ylabel="RMSE (radice dell'errore quadratico medio)",
        xlim=(min(similarities), max(similarities)),
        ylim=(0.0, upper_y * 1.15),
    )
    axis.ticklabel_format(axis="y", style="sci", scilimits=(-3, 3))
    axis.yaxis.get_offset_text().set_fontsize(9)
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return plotted


# Avvio da terminale: legge i dati e salva il grafico RMSE.
def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "SimQE_out.txt",
        help="output dell'esperimento 6",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent
        / "plots"
        / "experiment_rmse.png",
        help="file PNG di destinazione",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file di input non trovato: {args.input}")

    try:
        import matplotlib
    except ImportError as error:
        parser.error(f"installare matplotlib con `python -m pip install matplotlib`: {error}")
    matplotlib.use("Agg")

    methods, grouped = read_squared_errors(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plotted = plot_rmse(methods, grouped, args.output)
    repetitions = sum(
        len(values)
        for method_values in grouped.values()
        for values in method_values.values()
    )
    print(f"Similarità lette: {len(grouped)}")
    print(f"Metodi: {', '.join(methods)}")
    print(f"Errori quadratici letti: {repetitions}")
    print(f"Curve RMSE create: {plotted}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
