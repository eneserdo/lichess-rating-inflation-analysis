import argparse
import asyncio
import copy
import glob
import multiprocessing as mp
import os
from time import perf_counter

import chess
import chess.pgn
from natsort import natsorted

import config as cfg
from utils import PrintInLine, divide_pgn_file


async def eval_game_async(game: chess.pgn.Game) -> chess.pgn.Game:
    """
    Returns the evaluated game using async analysis
    """
    root = game
    scores = []  # Collect scores instead of printing immediately
    
    transport, engine = await chess.engine.popen_uci(cfg.STOCKFISH_PATH)
    # engine.configure({"Threads": 2})
    # engine.configure({"Hash": 256})
    try:
        while not game.is_end():
            game = game.next()
            analyse = await engine.analyse(
                game.board(), chess.engine.Limit(depth=cfg.STOCKFISH_DEPTH)
            )
            scores.append(analyse["score"])  # Collect score
            # game.set_eval(analyse["score"])
    finally:
        await engine.quit()
    
    # Process collected scores after analysis is complete
    # You could also return them or process them in a different way
    for score in scores:
        print(score)
        
    return root

def eval_game(game: chess.pgn.Game) -> chess.pgn.Game:
    """
    Returns the evaluated game
    """
    root = game
    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        # engine.configure({"Threads": 1})
        # engine.configure({"Hash": 256})
        while not game.is_end():
            game = game.next()
            analyse = engine.analyse(
                game.board(), chess.engine.Limit(depth=cfg.STOCKFISH_DEPTH)
            )
            # print(analyse["score"])
            game.set_eval(analyse["score"])

    return root

def eval_game2(game1: chess.pgn.Game, game2: chess.pgn.Game, threads: int = -1, hash: int = -1) -> chess.pgn.Game:
    """
    Returns the evaluated game
    """

    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        if threads != -1:
            engine.configure({"Threads": threads})
        if hash != -1:
            engine.configure({"Hash": hash})
                
        for game in [game1, game2]:
            while not game.is_end():
                game = game.next()
                analyse = engine.analyse(
                    game.board(), chess.engine.Limit(depth=cfg.STOCKFISH_DEPTH)
                )
                # print(analyse["score"])
                game.set_eval(analyse["score"])

    return game1, game2


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
    PrintInLine.reset()
    PrintInLine.print(1, "Concurently evaluating games...")

    # pbar = PrintInLine.get_pbar_function(0)
    # pgn_files = natsorted(glob.glob(os.path.join(args.output_dir, "*.pgn")))
    # for idx, pgn_file_path in enumerate(pgn_files):
    #     fnames = pgn_file_path.split("_")[-1].split(".")[0]
    #     parallel_eval_pgn(pgn_file_path, args.num_processes)
    #     pbar(idx, len(pgn_files), f"Evaluating: {fnames}", 2)

    # eval_pgn("lichess_db/lichess_db_standard_rated_2015-01_filtered.pgn", 0, 0, math.inf)
    parallel_eval_pgn("lichess_db/lichess_db_standard_rated_2015-01_filtered.pgn", args.num_processes)

if __name__ == "__main__":
    # arg_parser = argparse.ArgumentParser(description="Evaluate pgn files with Stockfish")
    # arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db", help="Output directory")
    # arg_parser.add_argument("-p", "--num_processes", type=int, default=12, help="Number of processes to use for filtering (default 8)")
    # args = arg_parser.parse_args()

    # start = perf_counter()
    # main(args)
    # end = perf_counter()

    with open("./sample/not_evaluated.pgn", "r") as f:
        game1 = chess.pgn.read_game(f)

    with open("./sample/not_evaluated.pgn", "r") as f:
        game2 = chess.pgn.read_game(f)



    elapsed = []
    for i in range(3):
        start = perf_counter()
        # eval_game(game2)
        eval_game2(game1, game2, threads=-1, hash=128)
        end = perf_counter()
        elapsed.append(end - start)
        print(f"Time taken: {elapsed[-1]} seconds")

    print(f"On average, time taken: {sum(elapsed) / len(elapsed)} seconds")

    # print("########################")
    # start = perf_counter()
    # eval_game(game2)
    # end = perf_counter()
    # print(f"Time taken: {end - start} seconds")

# async def async_main():
#     with open("./sample/not_evaluated.pgn", "r") as f:
#         game = chess.pgn.read_game(f)
    
#     start = perf_counter()
#     await eval_game_async(game)
#     end = perf_counter()
#     print(f"Time taken: {end - start} seconds")

# # Run the async main
# if __name__ == "__main__":
#     asyncio.run(async_main())