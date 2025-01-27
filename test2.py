from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import multiprocessing as mp
import time

def _print(text, x=0, y=0):
    sys.stdout.write("\033[{};{}H".format(y, x))
    sys.stdout.write("\033[K")
    sys.stdout.write(text)
    sys.stdout.flush()

def worker(idx):

    line_row = idx % 3  + 1 

    for i in range(5):
        sys.stdout.write("\033[{};{}H".format(line_row, i))
        sys.stdout.write(f"{idx}")
        sys.stdout.flush()
        time.sleep(0.1)


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