import argparse
import math
import statistics
from typing import List, Optional, Tuple

import numpy as np

from utils import divide_pgn_file, progress_bar

CEILING = 1000
INITIAL_CP = 15


def get_acpl(evals):
    diffs = np.diff(np.array(evals))

    # # Filter out positions where mate was found
    # mate_mask = np.abs(evals) >= 9000
    # diffs = diffs[~mate_mask[:-1]]

    # For white moves (even indices), negative diff means loss
    white_diffs = -diffs[::2]  # Negative because loss is positive
    # For black moves (odd indices), positive diff means loss
    black_diffs = diffs[1::2]

    # Only consider losses (positive values)
    white_acpl = np.mean(np.maximum(white_diffs, 0))
    black_acpl = np.mean(np.maximum(black_diffs, 0))

    return white_acpl, black_acpl


def clip(value: int) -> int:
    return min(max(value, -CEILING), CEILING)


# Based on https://github.com/lichess-org/scalachess/blob/42725a2e43bd3d18f0db5c2b1329edbcef457c46/core/src/main/scala/eval.scala#L79-L89
# [0, 100]
def centipawn_to_winpercent(cp: int) -> float:
    return 50 + 50 * centipawn_to_winchance(clip(cp))


# [-1, 1]
def centipawn_to_winchance(cp: int) -> float:
    MULTIPLIER = -0.00368208
    return max(min(2 / (1 + math.exp(MULTIPLIER * cp)) - 1, 1), -1)

# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L47-L55
def winpercents_to_accuracy(before_winpercent: float, after_winpercent: float) -> float:
    # Accuracy per move
    diff = after_winpercent - before_winpercent
    if diff >= 0:
        return 100.0
    raw = 103.1668100711649 * math.exp(0.04354415386753951 * diff) - 3.166924740191411
    raw += 1  # // uncertainty bonus (due to imperfect analysis)
    return max(0, min(100, raw))

def weighted_mean(pairs: List[Tuple[float, float]]) -> Optional[float]:
    """Calculate weighted mean from (value, weight) pairs"""
    if not pairs:
        return None
    values, weights = zip(*pairs)
    return np.average(values, weights=weights)

def harmonic_mean(values: List[float]) -> Optional[float]:
    """Calculate harmonic mean"""
    if not values:
        return None
    return statistics.harmonic_mean(values)

# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L81-L115
def game_accuracy(cps: List[float]) -> Tuple[float, float]:
    """
    Calculate game accuracy for both colors
        cps: List of centipawn evaluations from white's perspective
        Returns:
            Tuple of accuracy for white and black
    """
    # I assumed start_color is always white

    # Convert centipawns to win percentages (assuming we have this function)
    all_win_percents = [centipawn_to_winpercent(INITIAL_CP)] + [
        centipawn_to_winpercent(cp) for cp in cps
    ]

    # Calculate window size (10% of moves, between 2 and 8)
    window_size = min(max(len(cps) // 10, 2), 8)

    # Get raw win percent values
    # all_win_percent_values = [wp.value for wp in all_win_percents]
    all_win_percent_values = all_win_percents[:]  # copy

    # Create windows for volatility calculation
    initial_windows = [all_win_percent_values[:window_size]] * (
        min(window_size, len(all_win_percent_values)) - 2
    )
    sliding_windows = [
        all_win_percent_values[i : i + window_size]
        for i in range(len(all_win_percent_values) - window_size + 1)
    ]
    windows = initial_windows + sliding_windows

    # Calculate weights using standard deviation
    weights = [
        min(max(np.std(window) if len(window) > 1 else 0, 0.5), 12)
        for window in windows
    ]

    assert len(weights) + 1 == len(all_win_percents), (
        f"{len(weights)=} + 1 != {len(all_win_percents)=}"
    )

    # Calculate weighted accuracies
    weighted_accuracies = []
    for i, ((prev_wp, next_wp), weight) in enumerate(
        zip(zip(all_win_percents[:-1], all_win_percents[1:]), weights)
    ):
        # Determine whose move it was
        color = i % 2 == 0

        # Calculate accuracy
        before = prev_wp if color else next_wp
        after = next_wp if color else prev_wp
        accuracy = winpercents_to_accuracy(before, after)

        weighted_accuracies.append(((accuracy, weight), color))

    def color_accuracy(color: bool) -> Optional[float]:
        # Get accuracies for this color
        color_pairs = [
            (acc, weight) for (acc, weight), c in weighted_accuracies if c == color
        ]
        color_values = [acc for (acc, _), c in weighted_accuracies if c == color]

        # Calculate means
        weighted = weighted_mean(color_pairs)
        harm = harmonic_mean(color_values)

        if weighted is None or harm is None:
            return None

        return (weighted + harm) / 2

    # Return accuracies for both colors
    return color_accuracy(True), color_accuracy(False)


# Based on https://github.com/lichess-org/lila/blob/cf9e10df24b767b3bc5ee3d88c45437ac722025d/modules/analyse/src/main/Advice.scala#L52
def count_errors(cps: List[float]):
    """
    Count the number of blunders, mistakes, and inaccuracies in the game
    Blunder: 0.3 change in winpercent
    Mistake: 0.2 change in winpercent
    Inaccuracy: 0.1 change in winpercent
    """

    # Convert centipawns to win percentages (assuming we have this function)
    all_win_percents = [centipawn_to_winpercent(INITIAL_CP)] + [
        centipawn_to_winpercent(cp) for cp in cps
    ]
    for i, (prev_wp, next_wp) in enumerate(zip(all_win_percents[:-1], all_win_percents[1:])):
        color = i % 2 == 0
    raise NotImplementedError


def analyse_pgn(pgn_file_path: str):
    ...

def parallel_analyse_pgn(pgn_file_path: str, num_processes: int):
    ...

def main(args):
    ...

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Analyse pgn files")
    arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db", help="Output directory")
    arg_parser.add_argument("-p", "--num_processes", type=int, default=8, help="Number of processes to use for filtering (default 8)")
    args = arg_parser.parse_args()

    main(args)