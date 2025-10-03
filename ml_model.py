# ml_model.py
# This script ranks traders based on their performance metrics using a machine learning model.

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import sqlite3

# Connect to database
conn = sqlite3.connect('traders.db')

# Load data from database
query = 'SELECT name, ROI, win_rate, drawdown FROM traders'
data = pd.read_sql_query(query, conn)

# Check if data is not empty
if not data.empty:
    # Features and label setup
    X = data[['ROI', 'win_rate', 'drawdown']]
    y = data['ROI']  # Assuming ROI as the target for simplification

    # Model setup
    model = RandomForestRegressor(random_state=42)
    model.fit(X, y)

    # Predict and rank
    data['score'] = model.predict(X)
    data = data.sort_values(by='score', ascending=False)

    # Display top 5 traders
    print(data.head())
else:
    print('No data available for modeling.')

conn.close()