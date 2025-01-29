import multiprocessing as mp
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def progress_bar(progress: int, total: int, task_name: str, line: int):
    bar_length = 50  # Length of the progress bar
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = (progress / total) * 100
    sys.stdout.write("\033[{};{}H".format(line, 1))
    sys.stdout.write("\033[K")
    sys.stdout.write(f'{task_name}|{bar}| {percent:.2f}% Complete')
    sys.stdout.flush()

def worker(idx):

    line_row = idx % 3  + 1 

    for i in range(10):
        progress_bar(i, 10, f"T{idx}", idx)


def main():
    sys.stdout.write("\033[2J\033[H")
    
    # processes = []
    # for i in range(1, 4):
    #     p = mp.Process(target=worker, args=(i,))
    #     processes.append(p)
    
    # for p in processes:
    #     p.start()
    
    # for i in range(100):
    #     sys.stdout.write("\033[{};{}H".format(4, i))
    #     sys.stdout.write("4")
    #     sys.stdout.flush()
    #     time.sleep(0.1)

    # for p in processes:
    #     p.join()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(1, 10):
            futures.append(executor.submit(worker, i))

        for future in as_completed(futures):
            # print(future.result())
            pass
            
if __name__ == "__main__":
    main()