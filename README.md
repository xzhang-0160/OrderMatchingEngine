# OrderMatchingEngine
This is a simple order matching engine in Python. It will match the orders based on price/time priority. It supports both market order and limit order.


<!-- ABOUT THE PROJECT -->
## Order class
The Order class contains following attributes:
* `order_id` (e.g. “Order 1”)
* `symbol` (e.g. “0700.HK”)
* `price` (e.g. "MKT" or 610)
* `side` (e.g. "Buy")
* `qty` (e.g. 10000)
* `qty_done` (e.g. 0, the amount of order qty that is already traded)
* `qty_remain` (e.g. 10000, the amount of order qty that is yet to be traded)

## OrderBook class:
The OrderBook class contains two attributes: `bids` and `asks`.

Both the `bids` and `asks` are dictionaries: the keys are the price levels, and the values are a list of `Order` object.
At each price level, there is a list of order, e.g. self.bids[610] = [Order1,Order2,...]

## OrderMatchingEngine class:
The OrderMatchingEngine class has one attribute: `central_order_book`, and one method:`match_order`

The `central_order_book` attribute is a dictionary: the keys are the symbols, and the values are the order_book of this symbol. The order_book of each symbol can be updated inplace in the order matching process.

The `match_order` method is the core of this engine. Need to pass in one parameter: a string variable which is the file name of the input csv file. For example:
```
ome = OrderMatchingEngine()
ome.match_order("sampleA")
```

Below is how the order matching works:

### Step1: get orders
get orders from csv file input, and save them in `orders` in list of list format.

### Step2: evaluate orders
"Ack" valid orders and "Reject" orders with too large size.

In the meantime, for MKT orders, convert order price from `MKT` into `+inf` (for Buy)/ `-inf` (for Sell). The purpose is to make the MKT order price comparable to limit order prices, so that we can handle orders by sorting.

### Step3: Match orders
Loop through the orders in `valid_orders`, within each loop:

###### The code handles buy and sell order separately, although the logic is the same. So taking Buy order as an example:

Find the `best_price` (the min ask price) in the orderbook asks list.
If the `best_price` is smaller than our bid (`price`), then it is tradable, start to make the trade.
###### How to make the trade?
1. Find the `match_qty`. 
The `match_qty` is the minimum of (order quantity, the sum of the quantity of best_price yet to be trade in the orderbook)
2. Find the `trade_price` (for limit orders, the `trade price` is just `best price`. however, for MKT orders, may need below special treatment)
If what we quote is MKT price:
If there is non-MKT price in the asks in the `order_book`, then take the best non-MKT price in the asks as `trade_price`.
Otherwise (if there is only MKT price in the asks in the order_book), then find the next available buy order’s price as `trade_price`.

Now we get the `match_qty` and `trade_price`.

First, execute the aggressive order (side of incoming order)
(The quantity = `match_qty`)
1.	Move the qty from the `qty_remain` into the `qty_done` of the order
2.	And append the trade details to the output file.

Then, execute the passive order (opposite side of incoming order)
(The quantity = `order_match_qty` = min(`match_qty`, the remaining quantity of this particular order))
Similarly:
1.	Move the qty from the `qty_remain` into the `qty_done` of the order
2.	And append the trade details to the output file.

###### In my logic, there can be cases in which there is one aggressive order execution and multiple small passive order executions (the sum of multiple passive order qty = the one aggressive order qty). 

After executing the orders, check the `order_book` asks list, if for current price, there are no pending orders now, then delete this entry from `order_book`.

Then update the `best_price` back to the new best asks in the `order_book`.
Also, add the remaining parts of current order into the `order_book`. 
Then ready for next loop.


## Key variables:

Variable Name | Data type | Description
--- | --- | --- 
`valid_orders` | List of list | All the acknowledged valid orders
`order` | `Order` object | the aggressive order that we are now handling
`hit_order` | `Order` object | 	the passive order that is matched with aggressive order	
`order_book` | `OrderBook` object | the orderbook correspond to the symbol of the order that we are handling. We make in-place changes on order_book after each execution.
`best_price` | float | The best price in the current order_book (if current order is “Buy”, then best_price is the best ask in the orderbook). This variable will be updated after each execution.
`trade_price` | float | The price to be traded (this is only useful if there is a MKT order. E.g. if current order is a Buy MKT order, and also there is no non-MKT price in the order_book, need to look into the next available Buy order price to make it as trade_price)
`match_qty` | float | the FillQuantity for aggressive order. i.e. the total qty that can be executed this round. 
`order_match_qty` | float | the FillQuantity for each passive order. i.e. the qty of each passive order that can be matched
`output` | List of list | The output of order matching engine. Including header, several lines of ack orders and several lines of fill orders.

