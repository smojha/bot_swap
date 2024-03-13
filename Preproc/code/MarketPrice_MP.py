import pandas as pd
import os
from call_market_price2 import MarketPrice2
from time import sleep
from multiprocessing import Process, Manager, cpu_count


class MarketPrice_MP:
    def __init__(self):
        m = Manager()
        self.iq = m.Queue()
        self.oq = m.Queue()
        self.num_tasks = 0
        self.retrieved = 0

    def get_price(self, orders, prev_price):
        """
            Run the market price and volume calculations for the given DataFrame.  The DataFrame
            should contain columns is_sell (bool), price, quantity.
            Return a tuple containing price and volume
        """
        PQ = ['price', 'quantity']

        # split the orders DataFrame into buys and sells
        buys = orders[~orders.is_sell].copy()
        sells = orders[orders.is_sell].copy()

        # Convert buys and sells to tuples
        buy_tuples = [(o.price, o.quantity) for _, o in buys[PQ].iterrows()]
        sell_tuples = [(o.price, o.quantity) for _, o in sells[PQ].iterrows()]

        # Calculate the market price
        cmp = MarketPrice2(buy_tuples, sell_tuples)
        price, vol = cmp.get_market_price(last_price=prev_price)

        return price, vol


    def run_price_impact(self, key, orders, prev_price):
        counter_price, counter_vol = self.get_price(orders, prev_price)

        return *key, counter_price, counter_vol


    def task(self):
        for args in iter(self.iq.get, 'STOP'):
            self.oq.put(self.run_price_impact(*args))

    def get_status(self, t=1):
        while not(self.iq.empty()):
            sleep(t)
            done = self.num_tasks - self.iq.qsize()
            print(f"\tCompleted: {done} / {self.num_tasks}", flush=True, end="\r")
        print("\n")

    def start(self):
        procs = [Process(target=self.task) for _ in range(cpu_count())]
        status_proc = Process(target=self.get_status)

        for p in procs: p.start()

        return procs, status_proc

    def add_task(self, i):
        self.iq.put(i)
        self.num_tasks += 1

    def get_res(self):
        while self.retrieved < self.num_tasks:
            yield self.oq.get()
            self.retrieved += 1

    def stop(self, procs):
        for _ in range(cpu_count()): self.iq.put('STOP')
        for p in procs: p.join()




def run_markets(tasks):
    mp = MarketPrice_MP()
    procs , status_proc = mp.start()

    for t in tasks:
        mp.add_task(t)

    status_proc.start()
    res = list(mp.get_res())
    mp.stop(procs)
    status_proc.join()

    return res

