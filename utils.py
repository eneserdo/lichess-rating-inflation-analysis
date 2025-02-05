import datetime
import os
import sys
import time
from pprint import pprint

import chess
import chess.pgn

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

    # Progress bar in multiprocessed and multithreaded environment is a bit tricky
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

def count_games(pgn_file_path: str):
    counter = {tempo: {mean: 0 for mean in cfg.RATING_BIN_MEANS} for tempo in cfg.TIME_CONTROL.keys()}

    with open(pgn_file_path, "r") as f:
        count = 0
        while True:
            game_header = chess.pgn.read_headers(f)
            if game_header is None:
                break
            bin = get_rating_bin((int(game_header["WhiteElo"]) + int(game_header["BlackElo"])) / 2)
            tempo = get_time_control(game_header["TimeControl"])
            if tempo is not None and bin is not None:
                counter[tempo][bin] += 1
            count += 1
    
    print(f"Total games: {count}")
    pprint(counter)


if __name__ == "__main__":
    count_games("lichess_db/lichess_db_standard_rated_2018-01_filtered.pgn")
    # PrintInLine.print(1, "Hello")
    # PrintInLine.print(2, "World")
    # PrintInLine.print(3, "Helloasdfasdf")
    # time.sleep(1)
    # PrintInLine.print(3, "Hello")
    # PrintInLine.print(4, "World")