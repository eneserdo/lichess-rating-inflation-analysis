from multiprocessing import Process, Value, Lock
import time
import multiprocessing as mp
def increment_counter(counter, lock):
    for _ in range(1000):
        with lock:
            counter[0][0] += 1
        time.sleep(0.001)  # Small delay to simulate work

def main():
    with mp.Manager() as manager:

        counter = {0: manager.dict({0: 0})}
        counter = manager.dict(counter)
        lock = manager.Lock()
        with mp.Pool(4) as pool:
            pool.starmap(increment_counter, [(counter, lock) for _ in range(4)])

        print(f"Final counter value: {counter[0][0]}")


if __name__ == '__main__':
    main()



