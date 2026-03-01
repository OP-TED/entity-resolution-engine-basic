#!/usr/bin/env python3

from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def plot_cluster_distribution_continuous(
    size_to_count: dict[int, int],
    *,
    title: str = "Cluster size distribution",
    output_file: str = "distribution.png",
    show_cdf: bool = False,
) -> None:
    if not size_to_count:
        raise ValueError("Input dictionary is empty")

    # Determine full continuous range
    min_size = min(size_to_count)
    max_size = max(size_to_count)

    sizes = list(range(min_size, max_size + 1))
    counts = [size_to_count.get(size, 0) for size in sizes]

    fig, ax = plt.subplots(figsize=(12, 6))

    # Bar chart
    ax.bar(sizes, counts, width=0.9)

    ax.set_xlabel("Cluster size")
    ax.set_ylabel("Count")
    ax.set_title(title)

    ax.set_xticks(sizes)
    ax.set_xlim(min_size - 0.5, max_size + 0.5)

    # Force integer y-axis ticks
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    # Optional cumulative distribution
    if show_cdf:
        total = sum(counts)
        cumulative = []
        running = 0
        for c in counts:
            running += c
            cumulative.append(100.0 * running / total if total else 0)

        ax2 = ax.twinx()
        ax2.plot(sizes, cumulative, marker="o")
        ax2.set_ylabel("Cumulative (%)")
        ax2.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved chart to {output_file}")


if __name__ == "__main__":
    data = {1: 3, 2: 7, 3: 4, 4: 4, 5: 1}

    plot_cluster_distribution_continuous(
        data,
        title="Distribution of cluster sizes (continuous)",
        output_file="distribution.png",
        show_cdf=True,
    )