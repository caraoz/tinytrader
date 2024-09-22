import csv
import random

# Define the tickers
tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'BRK.A', 'BRK.B', 'LLY', 'TSM', 'TSLA']

# Define users
users = ['user1', 'user2', 'user3', 'user4', 'user5']

# Function to generate random price in multiples of 10
def generate_price(side):
    base_price = random.randint(1, 500) * 10  # Price between 10 and 5000, in multiples of 10
    if side == 'buy':
        return base_price
    elif side == 'sell':
        return base_price + random.randint(1, 50) * 10  # Sell price is higher

# Function to generate orders
def generate_orders(ticker):
    orders = []
    for _ in range(100):
        side = random.choice(['buy', 'sell'])
        price = generate_price(side)
        quantity = 100  # Quantity is 100
        user_id = random.choice(users)
        order_type = 'limit'
        orders.append([ticker, side, price, quantity, order_type, user_id])
    return orders

# Generate orders for all tickers and write to a CSV file
with open('100_orders.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['ticker', 'side', 'price', 'quantity', 'order_type', 'user_id'])
    for ticker in tickers:
        orders = generate_orders(ticker)
        writer.writerows(orders)

print("CSV file '100_orders.csv' with 100 orders per ticker has been created successfully.")