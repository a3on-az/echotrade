#!/usr/bin/env python3
"""
EchoTradeBot - Professional Trading Dashboard
Dark mode Dash application with real-time trading metrics
"""

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import threading
import time

# Import Phase 1 core components
try:
    from main import EchoTradeBot
    from config import Config
    from risk import RiskManager
    from execution import OrderExecutor
    from signals import SignalFetcher
    from backtest import BacktestEngine
    from models import TradingMetrics
except ImportError:
    # Fallback for development
    print("⚠️  Some Phase 1 components not available - using mock data")
    class Config:
        TRADING_PAIRS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        PORTFOLIO_VALUE = 10000
        TARGET_TRADERS = [{'name': 'Yun Qiang'}, {'name': 'Crypto Loby'}]
    
    class TradingMetrics:
        def __init__(self):
            pass

# Initialize Dash app with dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
app.title = "EchoTrade Pro"

# Global variables for real-time data
trading_bot = None
metrics_data = {
    'portfolio_value': 10000,
    'daily_pnl': 0,
    'total_roi': 0,
    'max_drawdown': 0,
    'open_positions': [],
    'recent_trades': [],
    'active_traders': ['Yun Qiang', 'Crypto Loby']
}

# Color scheme for dark mode
COLORS = {
    'background': '#1e1e2e',
    'surface': '#313244',
    'primary': '#89b4fa',
    'success': '#a6e3a1',
    'warning': '#f9e2af',
    'danger': '#f38ba8',
    'text': '#cdd6f4',
    'muted': '#6c7086'
}

# =====================================================
# LAYOUT COMPONENTS
# =====================================================

def create_navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Dashboard", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("Traders", href="/traders", active="exact")),
            dbc.NavItem(dbc.NavLink("Analytics", href="/analytics", active="exact")),
            dbc.NavItem(dbc.NavLink("Settings", href="/settings", active="exact")),
        ],
        brand="🤖 EchoTrade Pro",
        brand_href="/",
        color="primary",
        dark=True,
        className="mb-4"
    )

def create_metric_card(title, value, change=None, icon="fa-chart-line", color="primary"):
    change_element = []
    if change is not None:
        change_color = "success" if change >= 0 else "danger"
        change_icon = "fa-arrow-up" if change >= 0 else "fa-arrow-down"
        change_element = [
            html.Div([
                html.I(className=f"fas {change_icon} me-1"),
                f"{change:+.2f}%"
            ], className=f"text-{change_color} small")
        ]
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.I(className=f"fas {icon} fa-2x text-{color} mb-2"),
                    html.H4(value, className="mb-0"),
                    html.P(title, className="text-muted small mb-1"),
                    *change_element
                ], className="text-center")
            ])
        ])
    ], className="h-100")

def create_dashboard_layout():
    return html.Div([
        # Top metrics row
        dbc.Row([
            dbc.Col([
                create_metric_card(
                    "Portfolio Value", 
                    "$1,234,567", 
                    change=15.2, 
                    icon="fa-wallet", 
                    color="success"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Daily P&L", 
                    "+$18,432", 
                    change=3.7, 
                    icon="fa-chart-line", 
                    color="primary"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Total ROI", 
                    "+47.82%", 
                    change=2.1, 
                    icon="fa-trophy", 
                    color="warning"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Max Drawdown", 
                    "-8.42%", 
                    icon="fa-exclamation-triangle", 
                    color="danger"
                )
            ], width=3),
        ], className="mb-4"),
        
        # Emergency stop and status
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-stop-circle me-2"), "Emergency Stop"],
                                id="emergency-stop-btn",
                                color="danger",
                                size="lg",
                                className="me-3"
                            ),
                            dbc.Badge(
                                [html.I(className="fas fa-circle me-1"), "Live Trading"],
                                color="success",
                                className="fs-6 px-3 py-2"
                            ),
                            html.Span("Paper Mode", className="text-warning ms-3 small")
                        ], className="d-flex align-items-center justify-content-between")
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Main content row
        dbc.Row([
            # Equity curve
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Portfolio Equity Curve"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="equity-curve",
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ])
            ], width=8),
            
            # Live positions
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Open Positions"),
                    dbc.CardBody([
                        html.Div(id="positions-table"),
                        html.Hr(),
                        html.H6("Recent Signals", className="text-muted"),
                        html.Div(id="recent-signals")
                    ])
                ])
            ], width=4)
        ], className="mb-4"),
        
        # Performance metrics
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Performance Analytics"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="performance-metrics",
                            config={'displayModeBar': False},
                            style={'height': '300px'}
                        )
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Risk Metrics"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="risk-metrics",
                            config={'displayModeBar': False},
                            style={'height': '300px'}
                        )
                    ])
                ])
            ], width=6)
        ]),
        
        # Auto-refresh interval
        dcc.Interval(
            id='dashboard-interval',
            interval=5*1000,  # Update every 5 seconds
            n_intervals=0
        )
    ])

def create_traders_layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Available Traders"),
                    dbc.CardBody([
                        html.Div(id="traders-selection"),
                        html.Hr(),
                        dbc.Button(
                            "Update Trader List", 
                            id="refresh-traders-btn", 
                            color="primary",
                            className="mb-3"
                        )
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Portfolio Allocation"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="allocation-pie",
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ])
            ], width=4)
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trader Performance Comparison"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="trader-comparison",
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        )
                    ])
                ])
            ], width=12)
        ])
    ])

def create_analytics_layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Backtesting"),
                    dbc.CardBody([
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Start Date"),
                                    dcc.DatePickerSingle(
                                        id='backtest-start-date',
                                        date=(datetime.now() - timedelta(days=30)).date(),
                                        display_format='YYYY-MM-DD'
                                    )
                                ], width=3),
                                dbc.Col([
                                    dbc.Label("End Date"),
                                    dcc.DatePickerSingle(
                                        id='backtest-end-date',
                                        date=datetime.now().date(),
                                        display_format='YYYY-MM-DD'
                                    )
                                ], width=3),
                                dbc.Col([
                                    dbc.Label("Initial Capital"),
                                    dbc.Input(
                                        id="backtest-capital",
                                        type="number",
                                        value=10000,
                                        min=1000,
                                        step=1000
                                    )
                                ], width=3),
                                dbc.Col([
                                    html.Br(),
                                    dbc.Button(
                                        "Run Backtest",
                                        id="run-backtest-btn",
                                        color="primary"
                                    )
                                ], width=3)
                            ], className="mb-3")
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Backtest results
        html.Div(id="backtest-results"),
        
        # Historical performance
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Historical Performance"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="historical-performance",
                            config={'displayModeBar': False},
                            style={'height': '500px'}
                        )
                    ])
                ])
            ], width=12)
        ])
    ])

def create_settings_layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("API Configuration"),
                    dbc.CardBody([
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Binance API Key"),
                                    dbc.Input(
                                        id="api-key-input",
                                        type="password",
                                        placeholder="Enter API Key"
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("API Secret"),
                                    dbc.Input(
                                        id="api-secret-input",
                                        type="password",
                                        placeholder="Enter API Secret"
                                    )
                                ], width=6)
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Checkbox(
                                        id="sandbox-mode",
                                        label="Sandbox Mode",
                                        value=True
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Button(
                                        "Save Configuration",
                                        id="save-config-btn",
                                        color="success"
                                    )
                                ], width=6)
                            ])
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Risk Management"),
                    dbc.CardBody([
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Position Size (%)"),
                                    dbc.Input(
                                        id="position-size-input",
                                        type="number",
                                        value=2.0,
                                        min=0.1,
                                        max=10.0,
                                        step=0.1
                                    )
                                ], width=4),
                                dbc.Col([
                                    dbc.Label("Stop Loss (%)"),
                                    dbc.Input(
                                        id="stop-loss-input",
                                        type="number",
                                        value=2.0,
                                        min=0.5,
                                        max=20.0,
                                        step=0.1
                                    )
                                ], width=4),
                                dbc.Col([
                                    dbc.Label("Max Drawdown (%)"),
                                    dbc.Input(
                                        id="max-drawdown-input",
                                        type="number",
                                        value=30.0,
                                        min=5.0,
                                        max=50.0,
                                        step=1.0
                                    )
                                ], width=4)
                            ], className="mb-3"),
                            dbc.Button(
                                "Update Risk Settings",
                                id="save-risk-btn",
                                color="primary"
                            )
                        ])
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Status"),
                    dbc.CardBody([
                        html.Div(id="system-status"),
                        html.Hr(),
                        dbc.Button(
                            "Restart Bot",
                            id="restart-bot-btn",
                            color="warning",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Emergency Stop",
                            id="emergency-stop-settings-btn",
                            color="danger"
                        )
                    ])
                ])
            ], width=4)
        ])
    ])

# =====================================================
# MAIN LAYOUT
# =====================================================

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    create_navbar(),
    dbc.Container([
        html.Div(id='page-content')
    ], fluid=True)
], style={'backgroundColor': COLORS['background'], 'minHeight': '100vh'})

# =====================================================
# CALLBACKS
# =====================================================

@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/traders':
        return create_traders_layout()
    elif pathname == '/analytics':
        return create_analytics_layout()
    elif pathname == '/settings':
        return create_settings_layout()
    else:
        return create_dashboard_layout()

@app.callback(
    [Output('equity-curve', 'figure'),
     Output('positions-table', 'children'),
     Output('recent-signals', 'children'),
     Output('performance-metrics', 'figure'),
     Output('risk-metrics', 'figure')],
    Input('dashboard-interval', 'n_intervals')
)
def update_dashboard(n):
    # Generate sample equity curve
    dates = pd.date_range(start='2024-01-01', end='2024-09-24', freq='D')
    portfolio_values = np.cumsum(np.random.randn(len(dates)) * 100) + 10000
    
    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_values,
        mode='lines',
        name='Portfolio Value',
        line=dict(color=COLORS['primary'], width=2)
    ))
    
    equity_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['surface'],
        title="Portfolio Growth Over Time",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        showlegend=False
    )
    
    # Sample positions table
    positions_data = [
        {"Symbol": "BTC/USDT", "Side": "Long", "Size": "0.1", "P&L": "+$1,234"},
        {"Symbol": "ETH/USDT", "Side": "Long", "Size": "2.5", "P&L": "+$567"},
        {"Symbol": "BNB/USDT", "Side": "Short", "Size": "10", "P&L": "-$123"}
    ]
    
    positions_table = dash_table.DataTable(
        data=positions_data,
        columns=[{"name": i, "id": i} for i in positions_data[0].keys()],
        style_cell={'textAlign': 'left', 'backgroundColor': COLORS['surface'], 'color': COLORS['text']},
        style_header={'backgroundColor': COLORS['primary'], 'color': 'white'},
        style_data_conditional=[
            {
                'if': {'filter_query': '{P&L} contains +'},
                'color': COLORS['success'],
            },
            {
                'if': {'filter_query': '{P&L} contains -'},
                'color': COLORS['danger'],
            }
        ]
    )
    
    # Recent signals
    recent_signals = html.Div([
        dbc.ListGroup([
            dbc.ListGroupItem([
                html.Div([
                    html.Strong("Yun Qiang"), 
                    dbc.Badge("BUY", color="success", className="ms-2")
                ]),
                html.Small("BTC/USDT @ $47,856", className="text-muted")
            ]),
            dbc.ListGroupItem([
                html.Div([
                    html.Strong("Crypto Loby"), 
                    dbc.Badge("SELL", color="danger", className="ms-2")
                ]),
                html.Small("ETH/USDT @ $3,124", className="text-muted")
            ])
        ])
    ])
    
    # Performance metrics chart
    metrics = ['Sharpe Ratio', 'Win Rate', 'Profit Factor', 'Max DD']
    values = [1.85, 67.4, 1.92, -8.42]
    
    perf_fig = go.Figure(data=[
        go.Bar(x=metrics, y=values, marker_color=COLORS['primary'])
    ])
    
    perf_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['surface'],
        title="Key Performance Metrics"
    )
    
    # Risk metrics
    risk_fig = go.Figure(data=[
        go.Scatter(
            x=dates[-30:],
            y=np.random.randn(30).cumsum() * 2,
            mode='lines+markers',
            name='Daily Returns',
            marker=dict(color=COLORS['warning'])
        )
    ])
    
    risk_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['surface'],
        title="Rolling 30-Day Returns"
    )
    
    return equity_fig, positions_table, recent_signals, perf_fig, risk_fig

@app.callback(
    Output('traders-selection', 'children'),
    Input('refresh-traders-btn', 'n_clicks')
)
def update_traders_list(n_clicks):
    traders = [
        {"name": "Yun Qiang", "roi": "+1,700%", "win_rate": "75%", "active": True},
        {"name": "Crypto Loby", "roi": "+2,071%", "win_rate": "81%", "active": True},
        {"name": "ETH Expert", "roi": "+1,287%", "win_rate": "85%", "active": False},
        {"name": "UsGuiY", "roi": "+33.6%", "win_rate": "85.7%", "active": False},
    ]
    
    trader_cards = []
    for trader in traders:
        card = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H5(trader["name"], className="mb-1"),
                        html.P([
                            dbc.Badge(f"ROI: {trader['roi']}", color="success", className="me-2"),
                            dbc.Badge(f"Win: {trader['win_rate']}", color="primary")
                        ], className="mb-2")
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id=f"trader-switch-{trader['name']}",
                            value=trader["active"],
                            className="mb-2"
                        )
                    ], width=4)
                ])
            ])
        ], className="mb-3")
        trader_cards.append(card)
    
    return trader_cards

@app.callback(
    Output('backtest-results', 'children'),
    [Input('run-backtest-btn', 'n_clicks')],
    [State('backtest-start-date', 'date'),
     State('backtest-end-date', 'date'),
     State('backtest-capital', 'value')]
)
def run_backtest(n_clicks, start_date, end_date, capital):
    if n_clicks is None:
        return html.Div()
    
    # Simulate backtest results
    results = {
        'total_return': 47.82,
        'annual_return': 23.4,
        'max_drawdown': -8.42,
        'sharpe_ratio': 1.85,
        'win_rate': 67.4,
        'total_trades': 156
    }
    
    return dbc.Card([
        dbc.CardHeader("Backtest Results"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4(f"+{results['total_return']}%", className="text-success"),
                    html.P("Total Return", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"{results['max_drawdown']}%", className="text-danger"),
                    html.P("Max Drawdown", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"{results['sharpe_ratio']}", className="text-primary"),
                    html.P("Sharpe Ratio", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"{results['win_rate']}%", className="text-info"),
                    html.P("Win Rate", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"{results['total_trades']}", className="text-warning"),
                    html.P("Total Trades", className="text-muted")
                ], width=2),
                dbc.Col([
                    html.H4(f"${capital * (1 + results['total_return']/100):,.0f}", className="text-success"),
                    html.P("Final Value", className="text-muted")
                ], width=2)
            ])
        ])
    ], className="mb-4")

# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == '__main__':
    print("🚀 Starting EchoTrade Pro Dashboard...")
    print("📊 Dashboard: http://localhost:8050")
    print("🤖 Bot Status: Paper Trading Mode")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=8050
    )
