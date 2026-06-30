"""
HeatmapCanvas — matplotlib word-frequency heatmap embedded in PyQt6 (LLR-17, LLR-18)

Uses FigureCanvasQTAgg so the chart renders inside a Qt widget
rather than opening a separate matplotlib window.
"""

from collections import Counter
import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class HeatmapCanvas(FigureCanvasQTAgg):
    """
    Embeds a matplotlib figure as a native PyQt6 widget (LLR-18).

    Displays the top N most-frequent content words as a colour-coded grid.
    """

    def __init__(self, word_counts: Counter, top_n: int = 40, parent=None):
        self._fig = Figure(figsize=(9, 3), dpi=96)
        super().__init__(self._fig)
        self.setParent(parent)
        self._draw(word_counts, top_n)

    def _draw(self, word_counts: Counter, top_n: int) -> None:
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        pairs  = word_counts.most_common(top_n)
        if not pairs:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes)
            self.draw()
            return

        words, counts = zip(*pairs)
        counts_arr = np.array(counts, dtype=float)

        # Determine grid shape: try to make it roughly 5 rows
        cols = min(10, len(words))
        rows = int(np.ceil(len(words) / cols))

        # Pad counts to fill the grid
        padded = np.zeros(rows * cols)
        padded[:len(counts_arr)] = counts_arr
        grid = padded.reshape(rows, cols)

        # Build per-cell labels (word + count)
        cell_labels = []
        for i, (w, c) in enumerate(pairs):
            cell_labels.append(f"{w}\n{c}")
        cell_labels += [""] * (rows * cols - len(pairs))

        im = ax.imshow(grid, cmap="YlOrRd", aspect="auto")
        self._fig.colorbar(im, ax=ax, label="Frequency")

        # Annotate each cell with the word
        for idx, label in enumerate(cell_labels):
            r, c = divmod(idx, cols)
            ax.text(c, r, label, ha="center", va="center",
                    fontsize=6.5, color="black",
                    fontweight="bold" if grid[r, c] > grid.max() * 0.5 else "normal")

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("Top Word Frequency Heatmap", fontsize=10, pad=4)
        self._fig.tight_layout()
        self.draw()
