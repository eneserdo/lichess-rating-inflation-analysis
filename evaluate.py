import argparse
import glob
import multiprocessing as mp
import os
from time import perf_counter

import chess
import chess.pgn
from natsort import natsorted

import config as cfg
from utils import PrintInLine, count_games, divide_pgn_file


def eval_game(game: chess.pgn.Game, threads: int = -1, hash: int = -1) -> chess.pgn.Game:
    """
    Returns the evaluated game
    """
    root = game
    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        if threads != -1:
            engine.configure({"Threads": threads})
        if hash != -1:
            engine.configure({"Hash": hash})
        while not game.is_end():
            game = game.next()
            analyse = engine.analyse(
                game.board(), chess.engine.Limit(depth=cfg.STOCKFISH_DEPTH)
            )
            # print(analyse["score"])
            game.set_eval(analyse["score"])

    return root


def eval_pgn(pgn_file_path: str, idx: int, start: int, end: int):
    # read pgn file, evaluate each game, write to file

    evaluated_pgn_file = pgn_file_path.replace(".pgn", f"_evaluated_p{idx}.pgn")

    with open(evaluated_pgn_file, "w") as f, open(pgn_file_path, "r") as pgn_file:
        exporter = chess.pgn.FileExporter(f)

        pgn_file.seek(start)
        curr = pgn_file.tell()
        pbar = PrintInLine.get_pbar_function(0)
        while curr < end:
            pbar(curr - start, end - start, f"Evaluating {idx:02d}", 3+idx)
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            evaluated_game = eval_game(game)
            evaluated_game.accept(exporter)
            curr = pgn_file.tell()
        pbar(curr - start, end - start, f"Evaluating {idx:02d}", 3+idx)
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
    # os.system(f"rm {pgn_file_path}")


def main(args):
    PrintInLine.reset()
    PrintInLine.print(1, "Concurently evaluating games...")

    pbar = PrintInLine.get_pbar_function(0)
    pgn_files = natsorted(glob.glob(os.path.join(args.pgn_dir, "*_filtered.pgn")))
    pgn_files = [f for f in pgn_files if not os.path.exists(f.replace(".pgn", "_evaluated.pgn"))]
    
    
    for idx, pgn_file_path in enumerate(pgn_files):
        fnames = pgn_file_path.split("_")[-2].split(".")[0]
        pbar(idx, len(pgn_files), f"Evaluating: {fnames}", 2)
    
        start = perf_counter()
        parallel_eval_pgn(pgn_file_path, args.num_processes)
        end = perf_counter()

        game_count = count_games(pgn_file_path)
        PrintInLine.print(3+args.num_processes+1, f"{fnames} is done. Elapsed time: {end - start:.2f} s, {end - start / game_count:.2f} s/g")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Evaluate pgn files with Stockfish")
    arg_parser.add_argument("-p", "--pgn_dir", type=str, default="lichess_db", help="Directory to process pgn files")
    arg_parser.add_argument("-np", "--num_processes", type=int, default=8, help="Number of processes to use for filtering (default 8)")
    args = arg_parser.parse_args()
    
    main(args)