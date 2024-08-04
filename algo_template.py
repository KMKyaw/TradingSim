import backtrader as bt
import datetime
import pandas as pd

# Define a custom trading strategy inheriting from bt.Strategy
class CustomStrategy(bt.Strategy):
    def __init__(self):
        self.orders = {}          # Dictionary to store orders
        self.order_id_counter = 0 # Counter for order IDs
        self.dataclose = self.datas[0].close  # Close price of the first data feed

    def next(self):
        if self.position.size == 0:
            # Buy everything
            self.place_order(price=self.dataclose[0], size=self.broker.get_cash() / self.dataclose[0], order_type='market', action='buy')
        else:
            # Sell everything
            self.place_order(price=self.dataclose[0], size=self.position.size, order_type='market', action='sell')

    def get_cash(self):
        return self.broker.get_cash()
    
    def place_order(self, price, size, order_type='limit', action='buy'):
        if size <= 0:
            return None  # Do not place order if size is 0 or negative

        if action == 'buy':
            if order_type == 'limit':
                order = self.buy(price=price, size=size) 
            elif order_type == 'market':
                order = self.buy(size=size)              
            elif order_type == 'stop':
                order = self.buy(size=size, exectype=bt.Order.Stop, price=price) 
        elif action == 'sell':
            if order_type == 'limit':
                order = self.sell(price=price, size=size)  
            elif order_type == 'market':
                order = self.sell(size=size)              
            elif order_type == 'stop':
                order = self.sell(size=size, exectype=bt.Order.Stop, price=price) 

        if order:
            self.order_id_counter += 1  # Increase order ID counter
            self.orders[self.order_id_counter] = {
                'order': order,
                'status': 'active',  # Initially mark the order as active
                'price': price       # Store the price in the orders dictionary
            }
            return self.order_id_counter  # Return the order ID
        else:
            return None


    def cancel_order(self, order_id):
        if order_id in self.orders:
            self.cancel(self.orders[order_id]['order'])  # Cancel the order
            self.orders[order_id]['status'] = 'canceled'  # Update order status to canceled

    def get_all_orders(self):
        return self.orders  # Return dictionary of all orders

    def get_account_info(self):
        return {
            'cash': self.broker.get_cash(),               # Current cash balance
            'value': self.broker.get_value(),             # Current portfolio value
            'positions': {d._name: pos for d, pos in self.broker.positions.items()}  # Current positions
        }

# Function to load bar data from CSV
def load_bar_data(filename):
    return bt.feeds.GenericCSVData(
        dataname=filename,        # CSV file name
        datetime=0,               # Column index for datetime
        high=1,                   # Column index for high price
        low=2,                    # Column index for low price
        open=3,                   # Column index for open price
        close=4,                  # Column index for close price
        volume=5,                 # Column index for volume
        dtformat=('%Y-%m-%d'),    # Datetime format in the CSV
        openinterest=-1,          # Column index for open interest (-1 means not used)
        timeframe=bt.TimeFrame.Days  # Timeframe (daily bars)
    )

# Function to load tick data from CSV
def load_tick_data(filename):
    return bt.feeds.GenericCSVData(
        dataname=filename,                 # CSV file name
        datetime=0,                        # Column index for datetime
        volume=1,                          # Column index for volume
        bid_or_ask=2,                      # Column index for bid or ask
        dtformat=('%Y-%m-%d %H:%M:%S'),    # Datetime format in the CSV
        openinterest=-1,                   # Column index for open interest (-1 means not used)
        timeframe=bt.TimeFrame.Ticks       # Timeframe (tick data)
    )

# Main execution block
if __name__ == '__main__':
    try:
        # Initialize Backtrader Cerebro engine
        cerebro = bt.Cerebro()

        # Add custom strategy to Cerebro
        cerebro.addstrategy(CustomStrategy)

        # Load bar data from CSV and add to Cerebro
        bar_data = load_bar_data('bar_data.csv')
        cerebro.adddata(bar_data)

        # Load tick data from CSV and add to Cerebro
        # IN PROGRESS
        # tick_data = load_tick_data('tick_data.csv')
        # cerebro.adddata(tick_data)

        # Set initial cash for backtesting
        cerebro.broker.set_cash(10000)

        # Run the backtest
        cerebro.run()

        # Get all orders (including canceled ones)
        strategy_instance = cerebro.runstrats[0][0]
        all_orders = strategy_instance.get_all_orders()

        # Print all orders
        print("\nAll Orders:")
        for order_id, order_data in all_orders.items():
            print(f"Order ID: {order_id}, Status: {order_data['status']}, Size: {order_data['order'].size}, Price: {order_data['price']}")

        # Get account information
        account_info = strategy_instance.get_account_info()
        print("\nAccount Information:")
        print(f"Cash: {account_info['cash']}")
        print(f"Portfolio Value: {account_info['value']}")
        print("Positions:")
        for asset, position in account_info['positions'].items():
            print(f"{asset}: {position}")

    except Exception as e:
        print(f"Error during backtesting: {e}")
