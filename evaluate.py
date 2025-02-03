import argparse
import glob
import math
import multiprocessing as mp
import os
import statistics
import sys
from time import perf_counter
from typing import List, Optional, Tuple

import chess
import chess.pgn
import numpy as np
from natsort import natsorted

import config as cfg
from prepare import divide_pgn_file, progress_bar

CEILING = 1000
INITIAL_CP = 15


def eval_game(game: chess.pgn.Game) -> chess.pgn.Game:
    """
    Returns the evaluated game
    """

    root = game
    start = perf_counter()
    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        while not game.is_end():
            game = game.next()
            analyse = engine.analyse(
                game.board(), chess.engine.Limit(depth=cfg.STOCKFISH_DEPTH)
            )
            game.set_eval(analyse["score"])
    end = perf_counter()
    return root


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


def eval_pgn(pgn_file_path: str, idx: int, start: int, end: int):
    # read pgn file, evaluate each game, write to file

    evaluated_pgn_file = pgn_file_path.replace(".pgn", f"_evaluated_p{idx}.pgn")

    with open(evaluated_pgn_file, "w") as f, open(pgn_file_path, "r") as pgn_file:
        exporter = chess.pgn.FileExporter(f)

        pgn_file.seek(start)
        curr = pgn_file.tell()
        while curr < end:
            progress_bar(curr - start, end - start, f"Evaluating {idx:02d}", 3+idx)
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            evaluated_game = eval_game(game)
            evaluated_game.accept(exporter)
            curr = pgn_file.tell()

    return True


def parallel_eval_pgn(pgn_file_path: str, num_processes: int):
    boundaries = divide_pgn_file(pgn_file_path, num_processes)

    with mp.Pool(num_processes) as pool:
        args = [
            (pgn_file_path, idx, start, end) for idx, (start, end) in enumerate(boundaries)
        ]
        results = pool.starmap(eval_pgn, args, chunksize=1)

    os.system(f"cat {pgn_file_path[:-4]}*_evaluated_*.pgn > {pgn_file_path[:-4]}_evaluated.pgn")
    os.system(f"rm {pgn_file_path[:-4]}*_evaluated_*.pgn")
    os.system(f"rm {pgn_file_path}")


def main(args):
    # for pgn_file_path in natsorted(glob.glob(os.path.join(args.output_dir, "*.pgn"))):
        # parallel_eval_pgn(pgn_file_path, args.num_processes)

    # eval_pgn("lichess_db/lichess_db_standard_rated_2015-01_filtered.pgn", 0, 0, math.inf)
    sys.stdout.write("\033[2J\033[H") # clear screen, move cursor to top left
    print("Concurently evaluating games...", flush=True)
    parallel_eval_pgn("lichess_db/lichess_db_standard_rated_2015-01_filtered.pgn", args.num_processes)

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Evaluate pgn files with Stockfish")
    arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db", help="Output directory")
    arg_parser.add_argument("-p", "--num_processes", type=int, default=12, help="Number of processes to use for filtering (default 8)")
    args = arg_parser.parse_args()

    start = perf_counter()
    main(args)
    end = perf_counter()
