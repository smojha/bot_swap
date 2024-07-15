import pandas as pd
import matplotlib.pyplot as plt
#from call_market_price2 import MarketPrice2

INPUT_DIR = "Analysis/input"
IMG_DIR = "Analysis/temp/img"

group_data = pd.read_csv(f"{INPUT_DIR}/group.csv").set_index(['session', 'round'])
order_data = pd.read_csv(f"{INPUT_DIR}/orders.csv").set_index(['session', 'round'])

class MarketPrice3:
    """
    Implementation of the Call Market price algorithm described by: Sun et al. (2010)
    https://www.researchgate.net/publication/241567616_Algorithm_of_Call_Auction_Price
   
    Usage:
       mp = MarketPrice(bids, offers)
       price, volume = mp.get_market_price()

       The bids and offers can be either lists of Orders or (price/quantity) tuples.

       Parameters:
       bids, offers:   The bids and offers passed into the constructed. They will be lists
                        of (price/quantity) tuples
        has_bids, has_offers:  True if the bids or offers (respectively) are non_null and
                            non-empty.
        price_df:  The pandas DataFrame that is used to process the price.  Accessing this
                    is useful for debugging since is contains a history of the algorithm's
                    progress
        final_principle:  The last Principle that the algorithm attempted to apply
    """

    def __init__(self, bids, offers):
        self.bids, self.offers = bids, offers

        self.has_bids =  len(bids) > 0
        self.has_offers = len(offers) > 0
        
        keyed_bids = [{'t': 'b', 'p': x[0], 'q': x[1]} for x in self.bids]
        keyed_offers = [{'t': 'o', 'p': x[0], 'q': x[1]} for x in self.offers]
        self.all_orders = sorted(keyed_bids+ keyed_offers, key=lambda x: x['p'])


        self.csq = None
        self.cbq = None



    def generate_cxq(self):
        
        all_prices = sorted(set([o[0] for o in self.bids + self.offers]))
        
        # Calculate CSQ
        csq = {}
        for p in all_prices:
            relevant_offers = filter(lambda x: x[0] <= p, self.offers)
            csq_p = sum([o[1] for o in relevant_offers])
            csq[p] = csq_p
            
        cbq = {}
        for p in all_prices[::-1]:
            relevant_bids = filter(lambda x: x[0] >= p, self.bids)
            cbq_p = sum([o[1] for o in relevant_bids])
            cbq[p] = cbq_p
 
        return csq, cbq



    def get_market_price(self):
        """
        Implementation of the Call Market price algorithm described by: Sun et al. (2010)
        https://www.researchgate.net/publication/241567616_Algorithm_of_Call_Auction_Price
        
           Parameters: 

            
            Return:
                A tuple containing
                market_price (number): The resulting market price
                volume (number):  the Market Exchange Volume
        """

        
        # Determine volume and candidate prices based the Max Exchange Volume principle
        self.csq, self.cbq = self.generate_cxq()


        # Begin no-trade
        #  Handle error cases where there are missing bids or offers       
        
        if not (self.has_bids or self.has_offers):  # No orders of any kind
            return None, 0
        
        min_offer_price = None
        if self.has_offers:
            all_offer_price = [o[0] for o in self.offers]
            min_offer_price = min(all_offer_price)
            
        max_bid_price = None
        if self.has_bids:
            all_bid_price = [b[0] for b in self.bids]
            max_bid_price = max(all_bid_price)
       
        
        if not self.has_bids: # no buys
            # the price is the lowest offer (sell).  That is the lowest price 
            # at which a share may can be traded.
            return min_offer_price, 0
        
        if not self.has_offers: # no buys
            # the price is the highest bid (buy).  That is the highest price 
            # at which a share may can be traded.
            return max_bid_price, 0
        
        # If there is a bid-ask spread return the midpoint price
        if min_offer_price > max_bid_price:
            return int((max_bid_price + min_offer_price)/2), 0


        all_prices = sorted(set([o[0] for o in self.bids + self.offers]))
        cand_mev = [] # artifact of loop, the candidate prices
        mev = -1  # this is an artifact of the following loop and is the final volume
        for p in all_prices:
            csq_p = self.csq[p]
            cbq_p = self.cbq[p]
            vol = min(csq_p, cbq_p)
             
            if vol > mev:
                cand_mev = [p]
                mev = vol
            elif vol == mev:
                cand_mev.append(p)
                
        if len(cand_mev) == 1:
            return cand_mev[0], mev

        price = (max(cand_mev) + min(cand_mev))/2
        
        return int(price), mev## plot it


def plot_it(_p, _v, _csq, _cbq, sess=None, _rnd=None, title=None):
    """
    Plots supply and demand curves.  This will place a green dot where the market price and volume will go.
    Parameters:  _p: int - The market price (this will be the price coordinate of the green dot)
        _v: int - The market volume.  (volume coordinate of green dot)
        _csq: dict - Cumulative Sell Quantity:  A dictionary keyed by price and the values are the number of shares available to share at that price)
        _cbq: dict - Cumulative Buy Quantity: Similar to csq but with buying instead of selling.
    """
    dx = list(_cbq.values()) if _cbq else None # the x values for the demand curve
    dy = list(_cbq.keys())  if _cbq else None  # the y values for the demand curve
    # this fills out the demand curve to guarantee that is starts 
    # at zero on the x-axis
    if dx and dx[0] != 0:     
        dx = [0] + dx
        dy = [dy[0]] + dy

    
    sx = list(_csq.values()) if _csq else None  # the x values for the supply curve
    sy = list(_csq.keys()) if _csq else None   # the y values for the supply curve
    # this fills out the supply curve to guarantee that is starts 
    # at zero on the x-axis
    if sx and sx[0] != 0:
        sx = [0] + sx
        sy = [sy[0]] + sy


    # Step plots are perfect for these discrete supply and demand curves
    if dx:
        plt.step(dx, dy, where='pre', label="Demand")
    if sx:
        plt.step(sx, sy, where='pre', label="Supply")
    
    dot_label = f"Price {_p}; Volume {_v}"
    plt.plot(_v, _p, color='g', marker='o', label=dot_label)  # Marke the price / volume point
    plt.legend()
    
    plt.xlabel('Quantity')
    plt.ylabel('Price')
    
    if sess and _rnd:
        plt.title(f"Session {sess} - Round {_rnd}")
    elif title:
        plt.title(title)
    
    plt.show()
    plt.close()
    
    




def get_orders(sess, rnd):
    _buys = []
    _sells = []
    a = order_data.loc[(sess, rnd)]
    for idx, row in a.iterrows():
        t = row['type']
        p = int(row.price)
        q = int(row.quantity)
        
        if t == 'BUY':
            _buys.append((p, q))
        else:
            _sells.append((p, q))
            
    # _mp = group_data.loc[(sess, rnd)].price
    # _v = group_data.loc[(sess, rnd)].volume
    
    return _buys, _sells

idx_vals = group_data.iloc[:50, :].index.values

SESSION = '8h0lckuw'
RND = 27


for sess, rnd in idx_vals:
    buys, sells = get_orders(sess, rnd)
    call_mkt = MarketPrice3(buys, sells)
    mp, v = call_mkt.get_market_price()
    plot_it(mp, v, call_mkt.csq, call_mkt.cbq, title="Example of Typical Market")