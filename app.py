from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import os
import re
import textwrap
import subprocess
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Qwertyuiop'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('main'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():
    output = None
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.py'):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash('File uploaded successfully!', 'success')
            print('file received')
            try:
                # Extract myStrategy function and create a new file with the modified strategy
                with open(filepath, 'r') as f:
                    file_content = f.read()
                strategy_code = extract_mystrategy_code(file_content)
                new_filepath = create_new_strategy_file(strategy_code)
                os.remove(filepath)  # Remove the uploaded file
                print('Running...')    
                # Run the newly created Python file and capture the output
                time.sleep(2)
                print(new_filepath)
                if not os.path.exists(new_filepath):
                    raise FileNotFoundError(f"File not found: {new_filepath}")
                result = subprocess.run(['python3', new_filepath], capture_output=True, text=True)
                print(result)
                print('Return code:', result.returncode)
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)

                if result.returncode != 0:
                    output = f"Error: {result.stderr}"
                else:
                    output = result.stdout
                # output = 'Test'
            except Exception as e:
                print(e)
                flash(f'Error processing file: {e}', 'danger')
                output = str(e)
            return render_template('main.html', output=output)
    return render_template('main.html', output=output)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def extract_mystrategy_code(file_content):
    """Extracts the code inside myStrategy function."""
    match = re.search(r'def myStrategy\(\):\s*((?:\n\s+.*)+)', file_content, re.DOTALL)
    lines = file_content.split('\n')
    new_lines = []
    for line in lines:
        # Skip the function definition line
        if not line.startswith('def myStrategy():'):
            # Remove one level of indentation (4 spaces)
            new_lines.append(line[4:] if line.startswith('    ') else line)
    match = '\n'.join(new_lines)
    print(match)
    if match:
        return match
    else:
        raise ValueError('myStrategy function not found in the uploaded file.')

def create_new_strategy_file(strategy_code):
    """Creates a new Python file with the modified strategy."""
    strategy_code = textwrap.indent(strategy_code, ' ' * 8)  # Indent strategy code with 8 spaces
    new_strategy_template = f"""
import backtrader as bt
import datetime
import pandas as pd

class CustomStrategy(bt.Strategy):
    def __init__(self):
        self.orders = {{}}          # Dictionary to store orders
        self.order_id_counter = 0   # Counter for order IDs
        self.dataclose = self.datas[0].close  # Close price of the first data feed

    def next(self):
{strategy_code}
        # End of next

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
            self.orders[self.order_id_counter] = {{
                'order': order,
                'status': 'active',  # Initially mark the order as active
                'price': price       # Store the price at which the order was placed
            }}
            return self.order_id_counter  # Return the order ID
        return None

    def cancel_order(self, order_id):
        if order_id in self.orders:
            self.cancel(self.orders[order_id]['order'])  # Cancel the order
            self.orders[order_id]['status'] = 'canceled'  # Update order status to canceled

    def get_all_orders(self):
        return self.orders  # Return dictionary of all orders

    def get_account_info(self):
        return {{
            'cash': self.broker.get_cash(),               
            'value': self.broker.get_value(),             
            'positions': {{d._name: pos for d, pos in self.broker.positions.items()}}
        }}

    def get_cash(self):
        return self.broker.get_cash()

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

        # Set initial cash for backtesting
        cerebro.broker.set_cash(10000)

        # Run the backtest
        cerebro.run()

        # Get all orders (including canceled ones)
        strategy_instance = cerebro.runstrats[0][0]
        all_orders = strategy_instance.get_all_orders()

        # Print all orders
        print("\\nAll Orders:")
        for order_id, order_data in all_orders.items():
            print(f"Order ID: {{order_id}}, Status: {{order_data['status']}}, Size: {{order_data['order'].size}}, Price: {{order_data['price']}}")

        # Get account information
        account_info = strategy_instance.get_account_info()
        print("\\nAccount Information:")
        print(f"Cash: {{account_info['cash']}}")
        print(f"Portfolio Value: {{account_info['value']}}")
        print("Positions:")
        for asset, position in account_info['positions'].items():
            print(f"{{asset}}: {{position}}")

    except Exception as e:
        print(f"Error during backtesting: {{e}}")
"""

    new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'user_strategy.py')
    with open(new_filepath, 'w') as f:
        f.write(new_strategy_template)
    return new_filepath

if __name__ == '__main__':
    app.run(debug=False)
