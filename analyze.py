# TODO

# - Download the database from 2013-01 to 2013-12 for every 3 months
# - Get the player list for each database, save it to a file
# - Find the players who showed up in at least half of the databases
# - Randomly sample 1000 players from the list
# - Track their rating changes over time and centipawn changes over time


import os
from time import perf_counter
from typing import List, Optional, Tuple

import chess
import chess.pgn
import numpy as np

import config as cfg

def eval_pgn(game: chess.pgn.Game, engine_path, return_extra=False, depth=22, mate_score=10000) -> list[int]:

    evals = []
    extra = []
    board = game.board()
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        analyse = engine.analyse(board, chess.engine.Limit(depth=depth))
        extra.append(analyse)
        ret = analyse["score"].white().score(mate_score=mate_score)
        evals.append(ret)

        for move in game.mainline_moves():
            board.push(move)
            analyse = engine.analyse(board, chess.engine.Limit(depth=depth))
            extra.append(analyse)
            ret = analyse["score"].white().score(mate_score=mate_score)
            evals.append(ret)
            # print(".", end="", flush=True)
    # print()

    if return_extra:
        return evals, extra
    else:
        return evals




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



# Below code are not checked yet
# It is based on lichess analysis code


def from_centipawns(cp: int) -> float:
    # Convert centipawn to win percentage
    return 2 / (1 + np.exp(-0.00368208 * cp)) - 1


# Based on https://github.com/lichess-org/lila/blob/4336bf020e746413e0039f1583a186442084bafa/modules/analyse/src/main/AccuracyPercent.scala#L47-L55
def from_win_percents(before: float, after: float) -> float:
    if after >= before:
        return 100.0
    win_diff = before - after
    raw = 103.1668100711649 * np.exp(-0.04354415386753951 * win_diff) - 3.166924740191411
    raw += 1  # uncertainty bonus
    return max(0, min(100, raw))


def weighted_mean(values: List[Tuple[float, float]]) -> Optional[float]:
    if not values:
        return None
    total_weight = sum(weight for _, weight in values)
    if total_weight == 0:
        return None
    return sum(value * weight for value, weight in values) / total_weight


def harmonic_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    n = len(values)
    return n / sum(1 / value for value in values if value != 0)


def game_accuracy(start_color: str, cps: List[int]) -> Optional[Tuple[float, float]]:
    all_win_percents = [from_centipawns(cp) for cp in [0] + cps]
    window_size = max(2, min(8, len(cps) // 10))
    all_win_percent_values = all_win_percents

    windows = [all_win_percent_values[:window_size]] * (window_size - 2) + [
        all_win_percent_values[i : i + window_size]
        for i in range(len(all_win_percent_values) - window_size + 1)
    ]

    weights = [max(0.5, min(12, np.std(window))) for window in windows]

    weighted_accuracies = []
    for i, (prev, next) in enumerate(zip(all_win_percents[:-1], all_win_percents[1:])):
        color = "white" if (i % 2 == 0) == (start_color == "white") else "black"
        accuracy = from_win_percents(prev, next)
        weighted_accuracies.append(((accuracy, weights[i]), color))

    def color_accuracy(color: str) -> Optional[float]:
        weighted = weighted_mean(
            [(acc, weight) for (acc, weight), c in weighted_accuracies if c == color]
        )
        harmonic = harmonic_mean(
            [acc for (acc, _), c in weighted_accuracies if c == color]
        )
        if weighted is not None and harmonic is not None:
            return (weighted + harmonic) / 2
        return None

    return color_accuracy("white"), color_accuracy("black")


if __name__ == "__main__":
    # Example usage

    pgn_file = "sample/example.pgn" 
    with open(pgn_file) as pgn:
        game = chess.pgn.read_game(pgn)

    start=perf_counter()
    evals, extra = eval_pgn(game, cfg.STOCKFISH_PATH, depth=cfg.STOCKFISH_DEPTH)
    end=perf_counter()
    print(f"Time taken: {end-start} seconds")
    print(evals)
    # print(extra)

    # cps = [15, 900, -900, 0]  # Example centipawn values    
    # start_color = "black"
    # accuracy = game_accuracy(start_color, cps)
    # print(f"White accuracy: {accuracy[0]}, Black accuracy: {accuracy[1]}")
