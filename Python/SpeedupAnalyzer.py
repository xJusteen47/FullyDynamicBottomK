"""Compare LBBK and DMH runtime using multiplicative speedup factors.

Run from the repository root:

    python Python/SpeedupAnalyzer.py

Only configurations with equal ``k`` and equal total sketch memory are
compared: ``DMH buffer size * k == LBBK buffer size``. The reported factor is
DMH runtime divided by LBBK runtime, so values above 1 mean that LBBK is
faster. The average across configurations is the geometric mean of their
individual speedup factors.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


DMH_NAMES = {"BufferKLMinhash", "MinHash", "DMH"}
LBBK_NAMES = {"BottomK", "LBBK"}
CONFIGURATION = tuple[int, int, int, int | None]


# Struttura normalizzata di una coppia di configurazioni confrontabile.
@dataclass(frozen=True)
class SpeedupRecord:
    k: int
    dmh_buffer_size: int
    lbbk_buffer_size: int
    data_size: int
    window_size: int | None
    dmh_seconds: float
    lbbk_seconds: float
    speedup: float


# Lettura: cinque valori numerici indicano fixed updates, sei sliding window.
def read_timings(
    path: Path,
) -> dict[tuple[str, CONFIGURATION], dict[str, list[float]]]:
    """Read repeated fixed-update and sliding-window timing records."""

    timings: dict[
        tuple[str, CONFIGURATION], dict[str, list[float]]
    ] = defaultdict(lambda: defaultdict(list))

    with path.open("r", encoding="utf-8", newline="") as source:
        for line_number, row in enumerate(csv.reader(source), start=1):
            if not row:
                continue

            sketch_name = row[0].strip()
            if sketch_name in DMH_NAMES:
                sketch = "DMH"
            elif sketch_name in LBBK_NAMES:
                sketch = "LBBK"
            else:
                continue

            try:
                values = [float(value.strip()) for value in row[1:]]
            except ValueError:
                continue

            if len(values) == 5:
                k, buffer_size, data_size, _faults, seconds = values
                window_size = None
                phase = "fixed"
            elif len(values) == 6:
                k, buffer_size, data_size, window_size, _faults, seconds = values
                phase = "sliding"
            else:
                continue

            if seconds <= 0:
                raise ValueError(
                    f"runtime non positivo alla riga {line_number}: {seconds}"
                )

            configuration = (
                int(k),
                int(buffer_size),
                int(data_size),
                int(window_size) if window_size is not None else None,
            )
            timings[(phase, configuration)][sketch].append(seconds)

    return dict(timings)


# Filtra DMH, abbina LBBK con stesso k e memoria e calcola lo speedup dei tempi medi.
def calculate_speedups(
    timings: dict[tuple[str, CONFIGURATION], dict[str, list[float]]],
    phase: str,
    minimum_k: int = 0,
    exact_k: int | None = None,
    maximum_k: int | None = None,
    minimum_buffer: int | None = None,
    maximum_buffer: int | None = None,
    require_log_buffer: bool = True,
) -> list[SpeedupRecord]:
    """Return filtered, same-k, equal-memory DMH/LBBK comparisons."""

    records: list[SpeedupRecord] = []
    for (record_phase, configuration), methods in timings.items():
        if record_phase != phase or "DMH" not in methods:
            continue

        k, dmh_buffer_size, data_size, window_size = configuration
        if k < minimum_k or (exact_k is not None and k != exact_k):
            continue
        if maximum_k is not None and k > maximum_k:
            continue
        if require_log_buffer and dmh_buffer_size < math.log2(data_size):
            continue
        if minimum_buffer is not None and dmh_buffer_size < minimum_buffer:
            continue
        if maximum_buffer is not None and dmh_buffer_size > maximum_buffer:
            continue

        lbbk_buffer_size = k * dmh_buffer_size
        lbbk_configuration = (
            k,
            lbbk_buffer_size,
            data_size,
            window_size,
        )
        lbbk_methods = timings.get((phase, lbbk_configuration), {})
        if "LBBK" not in lbbk_methods:
            continue

        dmh_seconds = statistics.mean(methods["DMH"])
        lbbk_seconds = statistics.mean(lbbk_methods["LBBK"])
        records.append(
            SpeedupRecord(
                k=k,
                dmh_buffer_size=dmh_buffer_size,
                lbbk_buffer_size=lbbk_buffer_size,
                data_size=data_size,
                window_size=window_size,
                dmh_seconds=dmh_seconds,
                lbbk_seconds=lbbk_seconds,
                speedup=dmh_seconds / lbbk_seconds,
            )
        )

    return sorted(
        records,
        key=lambda record: (
            record.k,
            record.dmh_buffer_size,
            record.data_size,
            record.window_size or 0,
        ),
    )


# Aggregazione geometrica e formattazione dei report.
def geometric_mean(values: list[float]) -> float:
    if not values:
        raise ValueError("non ci sono configurazioni confrontabili")
    return math.exp(math.fsum(math.log(value) for value in values) / len(values))


def write_report(
    path: Path,
    phase: str,
    records: list[SpeedupRecord],
    report_title: str | None = None,
    filter_description: str | None = None,
) -> None:
    """Write one standalone Markdown report for a filtered experiment phase."""

    title = report_title or ("Fixed updates" if phase == "fixed" else "Sliding window")
    filter_description = filter_description or (
        "Sono inclusi solo i casi `k >= 2000` e `buffer_DMH >= log2(N)`."
    )
    lines = [
        f"# Speedup report: {title}",
        "",
        "Confronto eseguito solo per coppie con lo stesso `k`, la stessa dimensione",
        "dell'input e memoria totale equivalente: `buffer_DMH * k = buffer_LBBK`.",
        filter_description,
        "",
        "Lo speedup è `tempo medio DMH / tempo medio LBBK`: valori maggiori di 1",
        "indicano che LBBK è più veloce. La media aggregata è la media geometrica",
        "degli speedup delle configurazioni elencate.",
        "Le medie dei tempi nel riepilogo sono medie aritmetiche delle medie",
        "per configurazione; ogni configurazione abbinata pesa allo stesso modo.",
        "",
    ]

    if not records:
        lines.extend(["Nessuna coppia di configurazioni soddisfa tutti i filtri.", ""])
    else:
        average_speedup = geometric_mean([record.speedup for record in records])
        increase = (average_speedup - 1.0) * 100.0
        lines.extend(
            [
                f"- Coppie confrontabili: **{len(records)}**",
                f"- Speedup medio geometrico: **{average_speedup:.3f}×**",
                f"- Aumento relativo della velocità LBBK rispetto a DMH: **{increase:.1f}%**",
                f"- Tempo medio DMH sulle configurazioni: **{statistics.mean(record.dmh_seconds for record in records):.9f} s**",
                f"- Tempo medio LBBK sulle configurazioni: **{statistics.mean(record.lbbk_seconds for record in records):.9f} s**",
                "",
                "| k | N | l DMH | buffer LBBK (= k × l DMH) | Finestra | Tempo DMH (s) | Tempo LBBK (s) | Speedup |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for record in records:
            window = str(record.window_size) if record.window_size is not None else "—"
            lines.append(
                f"| {record.k} | {record.data_size} | {record.dmh_buffer_size} "
                f"| {record.lbbk_buffer_size} | {window} "
                f"| {record.dmh_seconds:.9f} | {record.lbbk_seconds:.9f} "
                f"| {record.speedup:.3f}× |"
            )
        lines.append("")

    lines.extend(["## Risultato finale", ""])
    if records:
        mean_dmh = statistics.mean(record.dmh_seconds for record in records)
        mean_lbbk = statistics.mean(record.lbbk_seconds for record in records)
        lines.extend(
            [
                f"- **Speedup medio geometrico: {average_speedup:.3f}×**",
                f"- **Tempo medio DMH: {mean_dmh:.9f} s**",
                f"- **Tempo medio LBBK: {mean_lbbk:.9f} s**",
            ]
        )
    else:
        lines.append("Speedup e tempi medi non disponibili (nessuna coppia confrontabile).")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# Genera report dei fixed updates per k=2000, raggruppati per buffer DMH.
def write_k2000_buffer_band_reports(
    output_dir: Path,
    timings: dict[tuple[str, CONFIGURATION], dict[str, list[float]]],
) -> list[Path]:
    bands = (
        ("10-19", 10, 19),
        ("20-40", 20, 40),
        ("41-plus", 41, None),
    )
    reports: list[Path] = []

    for band_name, lower_bound, upper_bound in bands:
        records = calculate_speedups(
            timings,
            phase="fixed",
            minimum_k=2000,
            exact_k=2000,
            minimum_buffer=lower_bound,
            maximum_buffer=upper_bound,
            require_log_buffer=False,
        )
        if upper_bound is None:
            band_description = f"`l_DMH >= {lower_bound}`"
            title = f"Fixed updates, k=2000, buffer DMH {lower_bound} e oltre"
        else:
            band_description = f"`l_DMH` tra `{lower_bound}` e `{upper_bound}`"
            title = (
                f"Fixed updates, k=2000, buffer DMH "
                f"{lower_bound}-{upper_bound}"
            )
        report = output_dir / f"speedup_k2000_buffer_{band_name}.md"
        write_report(
            report,
            phase="fixed",
            records=records,
            report_title=title,
            filter_description=(
                f"Sono inclusi solo i casi `k = 2000` e {band_description}. "
                "Per questi report non si applica il filtro `l >= log2(N)`. "
                "L'abbinamento mantiene lo stesso k e la stessa memoria: "
                "`buffer_DMH * k = buffer_LBBK`."
            ),
        )
        reports.append(report)

    return reports


# Crea report sliding window per fasce di k e, al loro interno, per fasce l_DMH.
def write_sliding_window_band_reports(
    output_dir: Path,
    timings: dict[tuple[str, CONFIGURATION], dict[str, list[float]]],
) -> list[Path]:
    k_bands = (
        ("k-1-99", "1 <= k < 100", 1, 99),
        ("k-100-999", "100 <= k < 1000", 100, 999),
        ("k-1000-4999", "1000 <= k < 5000", 1000, 4999),
        ("k-5000-plus", "k >= 5000", 5000, None),
    )
    buffer_bands = (
        ("10-19", 10, 19),
        ("20-40", 20, 40),
        ("41-plus", 41, None),
    )
    reports: list[Path] = []

    for k_name, k_description, minimum_k, maximum_k in k_bands:
        for buffer_name, minimum_buffer, maximum_buffer in buffer_bands:
            records = calculate_speedups(
                timings,
                phase="sliding",
                minimum_k=minimum_k,
                maximum_k=maximum_k,
                minimum_buffer=minimum_buffer,
                maximum_buffer=maximum_buffer,
                require_log_buffer=False,
            )
            if maximum_buffer is None:
                buffer_description = f"`l_DMH >= {minimum_buffer}`"
                buffer_title = f"{minimum_buffer} e oltre"
            else:
                buffer_description = (
                    f"`l_DMH` tra `{minimum_buffer}` e `{maximum_buffer}`"
                )
                buffer_title = f"{minimum_buffer}-{maximum_buffer}"
            report = output_dir / (
                f"speedup_sliding_{k_name}_buffer_{buffer_name}.md"
            )
            write_report(
                report,
                phase="sliding",
                records=records,
                report_title=(
                    f"Sliding window, {k_description}, "
                    f"buffer DMH {buffer_title}"
                ),
                filter_description=(
                    f"Sono inclusi solo i casi con `{k_description}` e "
                    f"{buffer_description}. Per questi report non si applica "
                    "il filtro `l >= log2(N)`. L'abbinamento mantiene lo stesso "
                    "k, N e la stessa memoria: `buffer_DMH * k = buffer_LBBK`."
                ),
            )
            reports.append(report)

    return reports


# Avvio da terminale: legge l'output e genera un report per ciascuna fase.
def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "LBBK_LBKMH_out.txt",
        help="file degli esperimenti (default: LBBK_LBKMH_out.txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "speedup_reports",
        help="cartella dei report Markdown generati",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"file di input non trovato: {args.input}")

    try:
        timings = read_timings(args.input)
        fixed_records = calculate_speedups(timings, "fixed", minimum_k=2000)
        sliding_records = calculate_speedups(timings, "sliding", minimum_k=2000)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fixed_report = args.output_dir / "speedup_fixed_updates.md"
    sliding_report = args.output_dir / "speedup_sliding_window.md"
    write_report(fixed_report, "fixed", fixed_records)
    write_report(sliding_report, "sliding", sliding_records)
    band_reports = write_k2000_buffer_band_reports(args.output_dir, timings)
    sliding_band_reports = write_sliding_window_band_reports(
        args.output_dir, timings
    )

    print(f"Input: {args.input}")
    print("Filtri: k >= 2000, l_DMH >= log2(N), stesso k e memoria equivalente.")
    for label, records, report in (
        ("Fixed updates", fixed_records, fixed_report),
        ("Sliding window", sliding_records, sliding_report),
    ):
        if records:
            average = geometric_mean([record.speedup for record in records])
            print(
                f"{label}: {len(records)} coppie, speedup medio "
                f"{average:.3f}x, report {report}"
            )
        else:
            print(f"{label}: nessuna coppia valida, report {report}")
    print("Report fixed updates separati per k=2000:")
    for report in band_reports:
        print(f"  {report}")
    print(
        f"Report sliding window suddivisi in fasce di k e buffer DMH: "
        f"{len(sliding_band_reports)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
