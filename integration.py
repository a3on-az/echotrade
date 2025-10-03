# integration.py
# Integration script to connect ML service with main EchoTradeBot

from flask import Flask, jsonify
import sqlite3
import pandas as pd
from ml_model import get_top_traders

app = Flask(__name__)

@app.route('/api/top_traders', methods=['GET'])
def get_top_traders_api():
    """Endpoint to get top-ranked traders for the main bot"""
    try:
        conn = sqlite3.connect('traders.db')
        query = 'SELECT name, ROI, win_rate, drawdown FROM traders ORDER BY (ROI * 0.5 + win_rate * 0.3 - drawdown * 0.2) DESC LIMIT 5'
        data = pd.read_sql_query(query, conn)
        conn.close()
        
        return jsonify({
            'status': 'success',
            'traders': data.to_dict('records')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'ml-trader-ranking'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8051, debug=False)