import argparse
from itertools import product
import sys
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from rich.progress import Progress


NUM_PROCESSES = None
NUM_THREADS = None

# Progress bar in multiprocessed and multithreaded environment is a bit tricky
# This is a simple but kind a hardcoded implementation that works for the current use case
def progress_bar(progress: int, total: int, task_name: str, line: int):
    bar_length = 50  # Length of the progress bar
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = (progress / total) * 100
    sys.stdout.write("\033[{};{}H".format(line, 0))
    sys.stdout.write("\033[K")
    sys.stdout.write(f'{task_name}|{bar}| {percent:.2f}% Complete')
    sys.stdout.flush()


def dummy_download_db(date: str, output_dir: str, idx: int = None):
    for i in range(100):
        line_row = idx % NUM_THREADS + 3
        progress_bar(i, 100, f"Downloading {date}", line_row)
        time.sleep(0.01)

    return True



def dummy_filter_games(idx: int):

    for i in range(100):
        progress_bar(i, 100, f"Filtering pgn_name p{idx}", 3 + NUM_THREADS + idx)
        time.sleep(0.01)


    return True



def parallel_filter_games(pgn_db_path: str, num_processes: int):
    # pgn_db_path: path to the zst file
        
    with mp.Pool(num_processes) as pool:
        args = [(idx) for idx in range(num_processes)]
        results = pool.starmap(dummy_filter_games, args, chunksize=1)



def processor_process(download_queue, num_processes):
    """Process that handles filtering downloaded files"""

    while True:
        pgn_path = download_queue.get()
        if pgn_path is None:  # Signal to stop
            print("Stopping processor")
            break


        start = time.perf_counter()
        parallel_filter_games(pgn_path, num_processes)
        end = time.perf_counter()

        pgn_name = pgn_path[:-8].split("_")[-1]
        sys.stdout.write("\033[{};{}H".format(3+NUM_THREADS + NUM_PROCESSES, 0))
        sys.stdout.write(f"Filtered {pgn_name}")
        sys.stdout.flush()


def main(args):
    global NUM_PROCESSES, NUM_THREADS
    NUM_PROCESSES = args.num_processes
    NUM_THREADS = args.num_threads

    sys.stdout.write("\033[2J\033[H") # clear screen, move cursor to top left

    sys.stdout.write("\033[{};{}H".format(1, 0))
    sys.stdout.write("Concurently downloading and filtering games...")
    sys.stdout.flush()
    dates = []

    skip_dates = []
    for year, month in product(range(2015, 2025), range(1, 13, 6)):
        date = f"{year}-{month:02d}"
        dates.append(date)

    # if skip_dates:
    #     print(f"Skipping:", ", ".join(skip_dates))


    

    filter_queue = mp.Queue()
    # processor = mp.Process(target=processor_process, args=(filter_queue, args.num_processes), name="Processor")    
    # processor.start()
    
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        futures = []
        for idx, date in enumerate(dates):
            futures.append(executor.submit(dummy_download_db, date, args.output_dir, idx))

        for future in as_completed(futures):
            pgn_path = future.result()
            filter_queue.put(pgn_path)
       
    # Signal that we're done downloading
    filter_queue.put(None)

    # Wait for both processes to finish
    # processor.join()



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-o", "--output_dir", type=str, default="lichess_db", help="Output directory")
    arg_parser.add_argument("-p", "--num_processes", type=int, default=8, help="Number of processes to use for filtering (default 8)")
    arg_parser.add_argument("-t", "--num_threads", type=int, default=3, help="Number of threads to use for downloading (default 3)")
    args = arg_parser.parse_args()
    
    main(args)
