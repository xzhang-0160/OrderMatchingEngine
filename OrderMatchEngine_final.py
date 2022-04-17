import math
import csv

class Order:
    def __init__(self, order_id: str, symbol: str, price: float, side: str, qty: int):
        self.order_id = order_id
        self.symbol = symbol
        self.price = price
        self.side = side
        self.qty = qty
        self.qty_done = 0  # quantity already traded
        self.qty_remain = qty  # quantity yet to trade

class OrderBook:
    def __init__(self):
        """
        self.bid and self.ask are dictionaries:
        key:value -> price:list of Order() objects
        at each price level, there is a list of order, eg. self.bids[610] = [Order1,Order2,...]
        """
        self.bids = {}
        self.asks = {}

class OrderMatchingEngine:

    def __init__(self):
        """
        the central_order_book is a dictionary:
        key:value -> symbol: order book of this symbol
        in the order matching process, for each order, we update the values of this dictionary inplace.
        """
        self.central_order_book = {}

    def match_order(self,input_file):
       
        # =============================================================================
        #  get orders and save in orders[] list        
        orders = []
        with open(input_file+'.csv') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)
            for row in reader:
                orders.append(Order(row[0], row[1], (row[2] if row[2] == 'MKT' else round(float(row[2]),1)), row[3], float(row[4]))) 
        
        output = []
        output.append(["ActionType","OrderID","Symbol","Price","Side","OrderQuantity","FillPrice","FillQuantity"])       
        
        # =============================================================================
        #  evaluate orders (ack valid orders, reject invalid orders)  
        valid_orders = []
        for order in orders:
            assert order.side == "Sell" or order.side == "Buy", "invalid side %s" %order.side
            if order.qty > 1000000:
                output.append(["Reject",order.order_id,order.symbol,order.price,order.side,order.qty])
            else:
                output.append(["Ack",order.order_id,order.symbol,order.price,order.side,order.qty])
                if order.price == "MKT":
                    if order.side == "Sell": order.price = float("-inf")
                    elif order.side == "Buy": order.price = float("inf")
                valid_orders.append(order)
                
        # =============================================================================
        #  matching orders         
        i = 0
        num_order = len(valid_orders)
        while i < num_order:
            order = valid_orders[i]
            symbol, order_id, price, qty, side = order.symbol, order.order_id, order.price, order.qty, order.side
            order_book = self.central_order_book.setdefault(symbol, OrderBook())
            # order_book refers to the OrderBook() correspond to this symbol. the changes on order_book are in place

            if side == 'Buy':
                best_price = min(order_book.asks.keys()) if len(order_book.asks) > 0 else None
                # price = the bid (highest price they are willing to buy), need price >= lowest ask price to make the trade.
                while best_price is not None and (price == 0.0 or price >= best_price) and order.qty_remain >= 1e-9:
                # if the best_price is tradable, start to make a trade
                    best_price_qty = sum([ask.qty_remain for ask in order_book.asks[best_price]])
                    match_qty = min(best_price_qty, order.qty_remain)
                    assert match_qty >= 1e-9, "Match quantity must be larger than zero"

                    trade_price = best_price if not math.isinf(best_price) else price
                    #if there is no MKT order in ask, trade_price is the best_price tradable
                    #if there is MKT order in ask, then trade_price is what we quote
                    if math.isinf(trade_price):  # if what we quote is MKT
                        if not math.isinf(max(order_book.asks.keys())):
                        # if there is Non-MKT price in order_book.ask, trade_price is the smallest non-MKT ask price in the order_book
                            trade_price = sorted(set(order_book.asks.keys()))[1]
                        else:
                        # if there is only MKT price in order_book.ask, find next available buy order's price as trade_price
                            j = i
                            while j < num_order:
                                if valid_orders[j].side == 'Buy' and not math.isinf(valid_orders[j].price):
                                    trade_price = valid_orders[j].price
                                    break
                                j += 1
                            # if no available trade price is found and reach the end of orders
                            if j == num_order - 1 and math.isinf(trade_price):
                                break

                    # execute aggressive order first (side of incoming order)
                    order.qty_done += match_qty
                    order.qty_remain -= match_qty
                    aggresive_trade_list = ["Fill",order_id,symbol,('MKT' if math.isinf(price) else price),
                                            side,qty,trade_price,match_qty]

                    # execute the passive order then (opposite side of incoming order)
                    while match_qty >= 1e-9:
                        # find order hit
                        hit_order = order_book.asks[best_price][0]
                        order_match_qty = min(match_qty, hit_order.qty_remain)
                        output.append(["Fill",hit_order.order_id,hit_order.symbol,
                                       ('MKT' if math.isinf(hit_order.price) else hit_order.price),
                                       hit_order.side,hit_order.qty,trade_price,order_match_qty])
                        hit_order.qty_done += order_match_qty
                        hit_order.qty_remain -= order_match_qty
                        match_qty -= order_match_qty
                        if hit_order.qty_remain < 1e-9:
                            del order_book.asks[best_price][0]
                    output.append(aggresive_trade_list)

                    # if the price does not have pending orders after matching, delete it from order_book
                    if len(order_book.asks[best_price]) == 0:
                        del order_book.asks[best_price]

                    # update the best price
                    best_price = min(order_book.asks.keys()) if len(order_book.asks) > 0 else None

                # add the remaining order into the depth, this is where the time priority is maintained
                if order.qty_remain >= 1e-9:
                    depth = order_book.bids.setdefault(price, [])
                    depth.append(order)
            else:
                # Sell
                best_price = max(order_book.bids.keys()) if len(order_book.bids) > 0 else None
                while best_price is not None and (price == 0.0 or price <= best_price) and order.qty_remain >= 1e-9:
                    best_price_qty = sum([bid.qty_remain for bid in order_book.bids[best_price]])
                    match_qty = min(best_price_qty, order.qty_remain)
                    assert match_qty >= 1e-9, "Match quantity must be larger than zero"

                    trade_price = best_price if not math.isinf(best_price) else price
                    if math.isinf(trade_price):
                        if not math.isinf(min(order_book.bids.keys())):           # if there is a Non-MKT level
                            trade_price = sorted(set(order_book.bids.keys()))[-2]  # the largest except MKT level
                        else:
                            # find next available Sell order's price as trade price
                            j = i
                            while j < num_order:
                                if valid_orders[j].side == 'Sell' and not math.isinf(valid_orders[j].price):
                                    trade_price = valid_orders[j].price
                                    break
                                j += 1
                            # if no available trade price is found and reach the end of orders
                            if j == num_order - 1 and math.isinf(trade_price):
                                break

                    #trade_price = best_price if not math.isinf(best_price) else price
                    # execute aggressive order first (side of incoming order)
                    order.qty_done += match_qty
                    order.qty_remain -= match_qty
                    aggressive_trade_list = ["Fill",order_id,symbol,('MKT'if math.isinf(price) else price),
                                             side,qty,trade_price,match_qty] 

                    # execute the passive order then (opposite side of incoming order)
                    while match_qty >= 1e-9:
                        # find order hit
                        hit_order = order_book.bids[best_price][0]
                        order_match_qty = min(match_qty, hit_order.qty_remain)

                        output.append(["Fill",hit_order.order_id,hit_order.symbol,
                                       ('MKT' if math.isinf(hit_order.price) else hit_order.price),
                                       hit_order.side,hit_order.qty,trade_price,order_match_qty])
                        hit_order.qty_done += order_match_qty
                        hit_order.qty_remain -= order_match_qty
                        match_qty -= order_match_qty
                        if hit_order.qty_remain < 1e-9:
                            del order_book.bids[best_price][0]
                        output.append(aggresive_trade_list)

                    # if the price does not have pending orders after matching, delete it from order_book
                    if len(order_book.bids[best_price]) == 0:
                        del order_book.bids[best_price]

                    # update the best price
                    best_price = max(order_book.bids.keys()) if len(order_book.bids) > 0 else None

                # add the remaining order into the depth, this is where the time priority is maintained
                if order.qty_remain >= 1e-9:
                    depth = order_book.asks.setdefault(price, [])
                    depth.append(order)
            i += 1

        
        with open(input_file+'output.csv', 'w') as f:
            writer = csv.writer(f)
            for _ in output:
                writer.writerow(_)
                print(_)
        
if __name__ == '__main__':
    ome = OrderMatchingEngine()
    for id in ['sampleA','sampleB','sampleC','sampleD','sampleE']:
        print(id)
        ome.match_order(id)
