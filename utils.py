import datetime
import glob
import os
import sys
import time
from collections import defaultdict
from pprint import pprint
from turtle import heading

import chess
import chess.pgn
import zstandard

import config as cfg


def get_rating_bin(rating: int) -> str:
    for i, bin in enumerate(cfg.RATING_BINS):
        if bin[0] <= rating <= bin[1]:
            return cfg.RATING_BIN_MEANS[i]
    return None

def get_time_control(time_control: str) -> str:
    # time_control: "X+Y"
    if time_control == "-":
        return None
    x = int(time_control.split("+")[0])
    for tempo, (min, max) in cfg.TIME_CONTROL.items():
        if min <= x <= max:
            return tempo
    return None

# Printing to the console in a multiprocessed and multithreaded environment is a bit tricky
class PrintInLine:
    def __new__(cls):
        raise Exception("This class is a singleton!")

    @staticmethod
    def print(line: int, text: str):
        sys.stdout.write(f"\033[{line};1H") # should never 0,0
        sys.stdout.write("\033[K")
        sys.stdout.write(text)
        sys.stdout.flush()

    @staticmethod
    def reset():
        sys.stdout.write("\033c")
        sys.stdout.flush()

    # This is a simple but kind a hardcoded implementation that works for the current use case
    @staticmethod
    def get_pbar_function(update_period: int=100):
        stime = 0
        update_state = 0

        def progress_bar(progress: int, total: int, task_name: str, line: int):
            nonlocal stime
            nonlocal update_state

            if stime == 0:
                stime = time.time()
            
            # In order to avoid spamming the console, we only update the progress bar every 100 updates
            if update_state != update_period:
                update_state += 1
                return
            update_state = 0

            bar_length = 50  # Length of the progress bar
            filled_length = round(bar_length * progress / total)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            percent = (progress / total) * 100
            expected_time = (time.time() - stime) * (total - progress) / (progress+1e-6)
            expected_time = round(expected_time, 0)
            expected_time = datetime.timedelta(seconds=expected_time)
            sys.stdout.write(f"\033[{line};1H") # should never 0,0
            sys.stdout.write("\033[K")
            sys.stdout.write(f'{task_name}|{bar}| {percent:.2f}% Complete (remaining: {expected_time})')
            sys.stdout.flush()

        return progress_bar

def divide_pgn_file(file_path, num_processes):
    """
    Divide the file into approximately equal parts for each process. It respects the game boundaries.
    """
    file_size = os.path.getsize(file_path)
    chunk_size = file_size // num_processes
    boundaries = [i * chunk_size for i in range(num_processes)]
    boundaries.append(file_size)  # Ensure the last chunk covers the end

    # get the actual boundaries
    with open(file_path) as pgn_db:
        for idx, start in enumerate(boundaries[:-1]):
            pgn_db.seek(start)
            
            # skip until the next game
            line = pgn_db.readline()
            while "[Event" not in line:
                line = pgn_db.readline()

            boundaries[idx] = pgn_db.tell() - len(line)

    boundaries = [[boundaries[i-1], boundaries[i]] for i in range(1, len(boundaries))]

    return boundaries

def count_games(pgn_file_path: str, return_counter: bool = False):
    counter = {tempo: {mean: 0 for mean in cfg.RATING_BIN_MEANS} for tempo in cfg.TIME_CONTROL.keys()}

    with open(pgn_file_path, "r") as f:
        count = 0
        while True:
            game_header = chess.pgn.read_headers(f)
            if game_header is None:
                break
            bin = get_rating_bin((int(game_header["WhiteElo"]) + int(game_header["BlackElo"])) / 2)
            tempo = get_time_control(game_header["TimeControl"])
            if tempo is None or bin is None:
                raise ValueError(f"Invalid tempo or bin: {tempo}, {bin}")

            counter[tempo][bin] += 1
            count += 1
    
    # print(f"Total games: {count}")
    # pprint(counter)
    if return_counter:
        return counter
    else:
        return count

def count_games2(pgn_file_path: str, return_counter: bool = False):
    counter = {tempo: {mean: 0 for mean in cfg.RATING_BIN_MEANS} for tempo in cfg.TIME_CONTROL.keys()}

    with open(pgn_file_path, "r") as f:
        count = 0
        while True:
            game_header = chess.pgn.read_headers(f)
            if game_header is None:
                break
            # bin = get_rating_bin((int(game_header["WhiteElo"]) + int(game_header["BlackElo"])) / 2)
            # tempo = get_time_control(game_header["TimeControl"])
            # if tempo is not None and bin is not None:
            #     counter[tempo][bin] += 1
            count += 1
    
    # print(f"Total games: {count}")
    # pprint(counter)
    if return_counter:
        return counter
    else:
        return count


def compress_pgn_files(pgn_files):
    """
    Compress the pgn files using zstd.
    """
    for pgn_file in pgn_files:
        with open(pgn_file, "rb") as f:
            zstd_compressor = zstandard.ZstdCompressor()
            compressed_file = pgn_file+".zst"

            with open(compressed_file, "wb") as f_out:
                zstd_compressor.copy_stream(f, f_out)
            
        print(f"Compressed {pgn_file} to {compressed_file}")


def count_players(pgn_file_path: str):
    counter = {} # {player_name: number_of_games}

    with open(pgn_file_path, "r") as f:
        count = 0
        while True:
            game_header = chess.pgn.read_headers(f)
            if game_header is None:
                break
            count += 1
            if game_header["White"] not in counter:
                counter[game_header["White"]] = 0
            if game_header["Black"] not in counter:
                counter[game_header["Black"]] = 0
            counter[game_header["White"]] += 1
            counter[game_header["Black"]] += 1

    return counter


def check_player_distribution(pgn_file_path: str):
    for file in glob.glob(os.path.join(pgn_file_path, "*filtered.pgn")):
        counter = count_players(file)
        # get the most common player
        most_common_player = max(counter, key=counter.get)
        print(f"Most common player: {most_common_player} with {counter[most_common_player]} games in {file.split('/')[-1]}")


def eval_benchmark(game: chess.pgn.Game, hash_size: int = None, num_threads: int = None, depth_limit: int = None, time_limit: int = None):
    # This cant be parallelized because of the engine
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        config = {}
        
        if num_threads is not None:
            config["Threads"] = num_threads
        if hash_size is not None:
            config["Hash"] = hash_size
        if config:
            engine.configure(config)
        
        while not game.is_end():
            game = game.next()
            analyse = engine.analyse(
                game.board(), chess.engine.Limit(depth=depth_limit, time=time_limit)
            )
            pass

            # game.set_eval(analyse["score"])


def eval_benchmark_v2(game1: chess.pgn.Game, game2: chess.pgn.Game, hash_size: int = None, num_threads: int = None, depth_limit: int = None, time_limit: int = None):
    # This cant be parallelized because of the engine
    
    
    with chess.engine.SimpleEngine.popen_uci(cfg.STOCKFISH_PATH) as engine:
        config = {}
        
        if num_threads is not None:
            config["Threads"] = num_threads
        if hash_size is not None:
            config["Hash"] = hash_size
        if config:
            engine.configure(config)
        
        # First game
        start = time.perf_counter()
        while not game1.is_end():
            game1 = game1.next()
            analyse = engine.analyse(
                game1.board(), chess.engine.Limit(depth=depth_limit, time=time_limit)
            )
            game1.set_eval(analyse["score"])

        end = time.perf_counter()

        g1 = end - start

        # Second game (it is same as the first one)
        start = time.perf_counter()
        while not game2.is_end():
            game2 = game2.next()
            analyse = engine.analyse(
                game2.board(), chess.engine.Limit(depth=depth_limit, time=time_limit)
            )
            game2.set_eval(analyse["score"])

        end = time.perf_counter()
        g2 = end - start

        return g1, g2

def check_evaluated_pgn_dir(pgn_dir: str):

    for pgn_file_evaluated in glob.glob(os.path.join(pgn_dir, "*_evaluated.pgn")):
        pgn_file_original = pgn_file_evaluated.replace("_evaluated.pgn", ".pgn")
        if not os.path.exists(pgn_file_original):
            print(f"Original pgn file does not exist: {pgn_file_original}")
            continue
        
        # count games
        counter_evaluated = count_games(pgn_file_evaluated, return_counter=True)
        counter_original = count_games(pgn_file_original, return_counter=True)
        for tempo in cfg.TIME_CONTROL.keys():
            for bin in cfg.RATING_BIN_MEANS:
                if counter_evaluated[tempo][bin] != counter_original[tempo][bin]:
                    print(f"Counter mismatch: {pgn_file_evaluated} {counter_evaluated[tempo][bin]} {pgn_file_original} {counter_original[tempo][bin]}")
                    break
        
        # compare game headers
        g_idx = 0
        with open(pgn_file_evaluated, "r") as f_evaluated, open(pgn_file_original, "r") as f_original:
            while True:
                heading_evaluated = chess.pgn.read_headers(f_evaluated)
                heading_original = chess.pgn.read_headers(f_original)
                if heading_evaluated is None or heading_original is None:
                    break
                ev_game_id = heading_evaluated.get("Site").split("/")[-1]
                ori_game_id = heading_original.get("Site").split("/")[-1]
                if ev_game_id != ori_game_id:
                    print(f"Game headers mismatch: {pgn_file_evaluated} {ev_game_id} {pgn_file_original} {ori_game_id}")
                    break
                g_idx += 1
        
        print("Total equal games: ", g_idx)
            
        # check if all games are evaluated
        with open(pgn_file_evaluated, "r") as f_evaluated:
            while True:
                game_evaluated = chess.pgn.read_game(f_evaluated)
                if game_evaluated is None:
                    break
                if not game_evaluated.next().eval():
                    site = game_evaluated.headers.get("Site")
                    print("Missing eval at game: ",  site)
                    break

        print("ok")
    print("All ok")

if __name__ == "__main__":
    # counter=count_games("lichess_db/lichess_db_standard_rated_2015-01_filtered_evaluated.pgn", return_counter=True)
    # pprint(counter)

    check_evaluated_pgn_dir("lichess_db")


        
    # with open("sample/not_evaluated.pgn") as f:
    #     game = chess.pgn.read_game(f)
    # start = time.perf_counter()
    # game = eval_benchmark(game, depth_limit=15)
    # end = time.perf_counter()
    # print(f"Time taken: {end - start:.4f} s")

    # for hash_size in [32, 512, 1024, 2048]:
    #     times_g1 = []
    #     times_g2 = []
    #     for run in range(10):
    #         with open("sample/new2.pgn") as f:
    #             game1 = chess.pgn.read_game(f)
    #         with open("sample/new2.pgn") as f:
    #             game2 = chess.pgn.read_game(f)

    #         g1, g2 = eval_benchmark_v2(game1, game2, depth_limit=18, hash_size=hash_size, num_threads=1)
    #         times_g1.append(g1)
    #         times_g2.append(g2)

    #     print(f"1st game: {sum(times_g1) / len(times_g1):.3f}, 2nd game: {sum(times_g2) / len(times_g2):.3f} s for hash_size: {hash_size}")


    # pprint(game)
    # count_games("sample/subset_evaluated.pgn")

    # PrintInLine.print(1, "Hello")
    # PrintInLine.print(2, "World")
    # PrintInLine.print(3, "Helloasdfasdf")
    # time.sleep(1)
    # PrintInLine.print(3, "Hello")
    # PrintInLine.print(4, "World")
    # c=count_players("lichess_db/lichess_db_standard_rated_2018-01_filtered.pgn")
    # pprint(c)
    # check_player_distribution("lichess_db")
