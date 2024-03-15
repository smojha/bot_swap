import pandas as pd
import matplotlib.pyplot as plt
import math


class SessionPlotter:
    MARKERS = ['*', 'X', '^', 'd', 'p']
    COLORS = [(.9, .6, 0), (.35, .7, .9), (.8, .6, .7), (.8, .4, 0), (0, .6, .5), (.95, .9, .25), (0, .45, .7)]
    LABEL_SIZE = 16
    SESSION_FIG_SIZE = (8,6)
    TOB = (2, 2)  # (<rows>, <columns>)


    def __init__(self, group_data: list, mod_cb=None, title_cb=lambda x: x, log_thold=99):
        """
        data:  Expecting a list of <session: str, price_data: pd.DataFrame> pairs
        file_base: path and file_name for saved results
        mod_db:  callback to determine the graph modifier
        title_cb: callback to determin the title of the session plot
        """
        self.price_data = SessionPlotter.get_price_data(group_data)
        self.mod_cb = mod_cb
        self.title_cb = title_cb
        self.log_thold = log_thold
        
    @staticmethod
    def get_price_data(group_data):
        prices = group_data.set_index(['session', 'round']).price
        price_data = []
        for sess in prices.index.get_level_values(0).unique():
            d = prices.loc[sess]
            price_data.append([sess, d])
        return price_data

    def group_sessions(self, figsize=SESSION_FIG_SIZE, tob=TOB, file_base: str = 'session_plots'):
        rows = tob[0]
        cols = tob[1]
        num_plots = len(self.price_data)
        plots_per_page = rows * cols
        num_pages = math.ceil(num_plots / plots_per_page)

        for page in range(num_pages):
            d_for_page = self.price_data[page * plots_per_page: (page + 1) * plots_per_page]
            f = plt.figure(figsize=figsize).set_facecolor('white')
            plots = [plt.subplot2grid(tob, (i // cols, i % cols)) for i in range(len(d_for_page))]

            for i, d in enumerate(d_for_page):
                session = d[0]
                price_d = d[1]
                
                mod = self.mod_cb(session) if self.mod_cb else None
                title = self.title_cb(session)

                p = plots[i]
                p.set_title(title)
                SessionPlotter.plot_session(p, price_d, modifier=mod, pm=None, log_thold=self.log_thold)

            if file_base:
                plt.savefig(f'{file_base}_{page}.png', transparent=False)

            plt.show()
            plt.close()
            
    def plot_sessions(self, figsize=SESSION_FIG_SIZE):
        self.plots = []
        
        for i, d in enumerate(self.price_data):
            sess = d[0]
            price = d[1]
            
            fig, ax = plt.subplots(figsize=figsize)
            fig.set_facecolor('white')
            self.plots.append((sess, fig, ax))
            
            #Set the title
            title = self.title_cb(sess)
            ax.set_title(title, fontsize=self.LABEL_SIZE)
            ax.set_ylabel('Price', fontsize=self.LABEL_SIZE)
            ax.set_xlabel('Period', fontsize=self.LABEL_SIZE)
            
            #get the modifier
            mod = self.mod_cb(sess) if self.mod_cb else None


            # plot price
            SessionPlotter.plot_session(ax, price, modifier=mod)
         
            
    def save_figures(self, path, base_name):
        for sess, fig, ax in self.plots:
            fig.savefig(f'{path}/{base_name}_{sess}.png')
    

    @staticmethod
    def plot_session(graph, price_data, modifier=None, log_thold=99, pm=None):

        rounds = price_data.index.values

        # Price Plot
        if price_data.max() > log_thold:
            graph.set_yscale('log')
            lab = 'Price (log scale)'
        else:
            lab = 'Price'

        graph.plot(rounds, price_data, marker=pm, color='black', label=lab)

        if modifier:
            modifier.modify(graph)

        graph.legend()


class SessionPlotModifier:
    def modify(self, plot):
        pass
