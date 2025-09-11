import argparse
import glob
import json
import multiprocessing as mp
import os
from pathlib import Path
from time import perf_counter

import chess
import chess.pgn
from natsort import natsorted

import config as cfg
from utils import PrintInLine, count_games, divide_pgn_file

CHECKPOINT_DIR = Path("eval-checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


def get_file_checkpoint_path(pgn_file_path: str) -> Path:
    """Get the checkpoint file path for a specific PGN file"""
    # Create a safe filename from the PGN file path
    safe_filename = pgn_file_path.replace("/", "_").replace("\\", "_").replace(".pgn", "_checkpoint.json")
    return CHECKPOINT_DIR / safe_filename


def get_process_checkpoint_path(pgn_file_path: str, process_idx: int) -> Path:
    """Get the checkpoint file path for a specific process"""
    safe_filename = pgn_file_path.replace("/", "_").replace("\\", "_").replace(".pgn", f"_p{process_idx}_checkpoint.json")
    return CHECKPOINT_DIR / safe_filename


def load_file_checkpoint(pgn_file_path: str) -> dict:
    """Load checkpoint data for a specific PGN file"""
    checkpoint_path = get_file_checkpoint_path(pgn_file_path)
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {"completed_processes": [], "total_games": 0}


def save_file_checkpoint(pgn_file_path: str, checkpoint_data: dict):
    """Save checkpoint data for a specific PGN file"""
    checkpoint_path = get_file_checkpoint_path(pgn_file_path)
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f)


def load_process_checkpoint(pgn_file_path: str, process_idx: int) -> dict:
    """Load checkpoint data for a specific process"""
    checkpoint_path = get_process_checkpoint_path(pgn_file_path, process_idx)
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {"current_position": 0, "games_evaluated": 0}


def save_process_checkpoint(pgn_file_path: str, process_idx: int, checkpoint_data: dict):
    """Save checkpoint data for a specific process"""
    checkpoint_path = get_process_checkpoint_path(pgn_file_path, process_idx)
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f)


def cleanup_checkpoints(pgn_file_path: str):
    """Clean up checkpoint files for a completed PGN file"""
    base_filename = pgn_file_path.replace("/", "_").replace("\\", "_").replace(".pgn", "")
    
    # Remove file checkpoint
    file_checkpoint = CHECKPOINT_DIR / f"{base_filename}_checkpoint.json"
    if file_checkpoint.exists():
        file_checkpoint.unlink()
    
    # Remove process checkpoints
    for file_checkpoint_part in CHECKPOINT_DIR.glob(f"{base_filename}_p*_checkpoint.json"):
        file_checkpoint_part.unlink()


def eval_game(game: chess.pgn.Game) -> chess.pgn.Game:
    """
    Returns the evaluated game
    """
    root = game
    assert not root.is_end(), f"Game {root.headers['GameId']} has no moves"
    
    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        config = {}
        
        if cfg.STOCKFISH_THREADS is not None:
            config["Threads"] = cfg.STOCKFISH_THREADS
        if cfg.STOCKFISH_HASH_SIZE is not None:
            config["Hash"] = cfg.STOCKFISH_HASH_SIZE
        if config:
            engine.configure(config)
        
        game = game.next()

        while True:
            # Remove all non-mainline variations
            if len(game.variations) > 0:
                assert game.variations[0].is_mainline()
                while len(game.variations) != 1:
                    game.remove_variation(-1)                            

            info = engine.analyse(game.board(), 
                                  chess.engine.Limit(depth=cfg.STOCKFISH_LIMIT_DEPTH, time=cfg.STOCKFISH_LIMIT_TIME))

            game.set_eval(info["score"])

            # We will only calculate errors if the move is different from the principal variation
            # This is what Lichess does: 
            # - https://github.com/lichess-org/lila/blob/a372b7fe49ccaddfe31a97fff8d2a298f0debd89/modules/tree/src/main/Analysis.scala#L32C63-L32C69
            # - https://github.com/lichess-org/lila/blob/a372b7fe49ccaddfe31a97fff8d2a298f0debd89/modules/fishnet/src/main/AnalysisBuilder.scala#L74 
            if game.next():
                if game.next().move != info["pv"][0]:
                    # Add the first move to the variation
                    game.add_variation(info["pv"][0]) 

            if game.is_end():
                break
            
            game = game.next()

    return root


def eval_pgn(pgn_file_path: str, idx: int, start: int, end: int):
    # read pgn file, evaluate each game, write to file

    evaluated_pgn_file = pgn_file_path.replace(".pgn", f"_evaluated_p{idx}.pgn")
    
    # Load process checkpoint
    checkpoint_data = load_process_checkpoint(pgn_file_path, idx)
    current_position = checkpoint_data["current_position"]
    games_evaluated = checkpoint_data["games_evaluated"]
    
    # If we have a checkpoint, adjust the start position
    if current_position > start:
        start = current_position

    with open(evaluated_pgn_file, "a" if current_position > start else "w") as f, open(pgn_file_path, "r") as pgn_file:
        exporter = chess.pgn.FileExporter(f)

        pgn_file.seek(start)
        curr = pgn_file.tell()
        pbar = PrintInLine.get_pbar_function(0)
        
        # Skip games that were already evaluated
        for _ in range(games_evaluated):
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            curr = pgn_file.tell()
        
        while curr < end:
            pbar(curr - start, end - start, f"Evaluating {idx:02d}", 3+idx)
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            evaluated_game = eval_game(game)
            evaluated_game.accept(exporter)
            curr = pgn_file.tell()
            
            # Save checkpoint after each game
            games_evaluated += 1
            checkpoint_data = {
                "current_position": curr,
                "games_evaluated": games_evaluated
            }
            save_process_checkpoint(pgn_file_path, idx, checkpoint_data)
            
        pbar(curr - start, end - start, f"Evaluating {idx:02d}", 3+idx)
    return True


def parallel_eval_pgn(pgn_file_path: str, num_processes: int):
    boundaries = divide_pgn_file(pgn_file_path, num_processes)
    
    # Load file checkpoint
    file_checkpoint = load_file_checkpoint(pgn_file_path)
    completed_processes = set(file_checkpoint["completed_processes"])
    
    # Filter out completed processes
    remaining_processes = []
    for idx, (start, end) in enumerate(boundaries):
        if idx not in completed_processes:
            remaining_processes.append((pgn_file_path, idx, start, end))

    if not remaining_processes:
        PrintInLine.print(3+num_processes+1, f"All processes completed for {os.path.basename(pgn_file_path)}")
        return True

    with mp.Pool(num_processes) as pool:
        results = pool.starmap(eval_pgn, remaining_processes, chunksize=1)
        
        # Mark completed processes
        for _, idx, _, _ in remaining_processes:
            completed_processes.add(idx)
            file_checkpoint["completed_processes"] = list(completed_processes)
            save_file_checkpoint(pgn_file_path, file_checkpoint)

    # Combine all partial files
    os.system(f"cat {pgn_file_path[:-4]}*_evaluated_*.pgn > {pgn_file_path[:-4]}_evaluated.pgn")
    os.system(f"rm {pgn_file_path[:-4]}*_evaluated_*.pgn")
    
    # Clean up checkpoints after successful completion
    cleanup_checkpoints(pgn_file_path)
    # os.system(f"rm {pgn_file_path}")


def main(args):

    PrintInLine.reset()
    PrintInLine.print(1, "Concurrently evaluating games...")

    pgn_files = natsorted(glob.glob(os.path.join(args.pgn_dir, "*_filtered.pgn")))
    pgn_files = [f for f in pgn_files if not os.path.exists(f.replace(".pgn", "_evaluated.pgn"))]
    
    pbar = PrintInLine.get_pbar_function(0)
    
    for idx, pgn_file_path in enumerate(pgn_files):
        fnames = pgn_file_path.split("_")[-2].split(".")[0]
        pbar(idx, len(pgn_files), f"Evaluating: {fnames}", 2)
    
        start = perf_counter()
        parallel_eval_pgn(pgn_file_path, args.num_processes)
        end = perf_counter()

        game_count = count_games(pgn_file_path)
        elapsed_hours = (end - start) / 3600
        PrintInLine.print(3+args.num_processes+1, f"{fnames} is done. Elapsed time: {elapsed_hours:.2f} h, {elapsed_hours / game_count:.2f} hours/game")


def debug():
    with open("sample/evaluated.pgn") as f:
        game = chess.pgn.read_game(f)
    game = eval_game(game)
    with open("sample/double_evaluated.pgn", "w") as f:
        exporter = chess.pgn.FileExporter(f)
        game.accept(exporter)

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Evaluate pgn files with Stockfish")
    arg_parser.add_argument("-p", "--pgn_dir", type=str, default="lichess_db", help="Directory to process pgn files")
    arg_parser.add_argument("-np", "--num_processes", type=int, default=8, help="Number of processes to use for filtering (default 8)")
    args = arg_parser.parse_args()
    main(args)
    # debug()