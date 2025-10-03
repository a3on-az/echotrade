#!/usr/bin/env python3
"""
EchoTradeBot - Enhanced Dashboard with Real Data Integration
Includes loading states, error handling, and improved UX
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

# Import dashboard data provider
from dashboard_data import get_data_provider

# Import Phase 1 components
try:
    from config import Config
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False
    print("⚠️  Backend not available - using mock data")

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        dbc.icons.FONT_AWESOME,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    suppress_callback_exceptions=True
)
app.title = "EchoTrade Pro"

# Initialize data provider
data_provider = get_data_provider()

# Enhanced color scheme
COLORS = {
    'background': '#0d1117',
    'surface': '#161b22',
    'surface_light': '#21262d',
    'primary': '#58a6ff',
    'success': '#3fb950',
    'warning': '#d29922',
    'danger': '#f85149',
    'text': '#c9d1d9',
    'text_secondary': '#8b949e',
    'border': '#30363d'
}

# =====================================================
# LAYOUT COMPONENTS
# =====================================================

def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div([
                    html.Span("🤖", style={'fontSize': '24px', 'marginRight': '10px'}),
                    html.Span("EchoTrade Pro", className="navbar-brand mb-0 h1",
                             style={'fontFamily': 'Inter, sans-serif', 'fontWeight': '600'})
                ])),
            ], align="center", className="g-0"),
            dbc.Row([
                dbc.Col([
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink("Dashboard", href="/", active="exact", className="px-3")),
                        dbc.NavItem(dbc.NavLink("Traders", href="/traders", active="exact", className="px-3")),
                        dbc.NavItem(dbc.NavLink("Analytics", href="/analytics", active="exact", className="px-3")),
                        dbc.NavItem(dbc.NavLink("Settings", href="/settings", active="exact", className="px-3")),
                    ], navbar=True)
                ])
            ], align="center"),
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4",
        style={'backgroundColor': COLORS['surface']}
    )

def create_loading_spinner(component_id):
    """Create a loading spinner overlay"""
    return dbc.Spinner(
        html.Div(id=component_id),
        color="primary",
        type="border",
        fullscreen=False,
        spinner_style={"width": "3rem", "height": "3rem"}
    )

def create_metric_card(title, value_id, change_id=None, icon="fa-chart-line", color="primary"):
    """Create animated metric card with loading state"""
    change_element = []
    if change_id:
        change_element = [
            html.Div(id=change_id, className="metric-change")
        ]

    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x mb-3",
                      style={'color': COLORS[color]}),
                html.Div(id=value_id, className="metric-value",
                        style={'fontSize': '1.8rem', 'fontWeight': '700', 'fontFamily': 'Inter'}),
                html.P(title, className="metric-title text-muted small mb-1"),
                *change_element
            ], className="text-center")
        ])
    ], className="h-100 metric-card", style={
        'backgroundColor': COLORS['surface'],
        'border': f'1px solid {COLORS["border"]}',
        'transition': 'all 0.3s ease'
    })

def create_dashboard_layout():
    return html.Div([
        # Top metrics row with loading states
        dbc.Row([
            dbc.Col([
                create_metric_card(
                    "Portfolio Value",
                    "portfolio-value",
                    "portfolio-change",
                    icon="fa-wallet",
                    color="success"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Daily P&L",
                    "daily-pnl",
                    "daily-pnl-change",
                    icon="fa-chart-line",
                    color="primary"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Total ROI",
                    "total-roi",
                    "total-roi-change",
                    icon="fa-trophy",
                    color="warning"
                )
            ], width=3),
            dbc.Col([
                create_metric_card(
                    "Max Drawdown",
                    "max-drawdown",
                    icon="fa-exclamation-triangle",
                    color="danger"
                )
            ], width=3),
        ], className="mb-4"),

        # Status bar with paper trading badge
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
                                [html.I(className="fas fa-circle me-1"), "Paper Trading Mode"],
                                id="status-badge",
                                color="warning",
                                className="fs-6 px-3 py-2"
                            ),
                            dbc.Badge(
                                [html.I(className="fas fa-sync-alt me-1"), "Auto-Refresh: 5s"],
                                color="info",
                                className="fs-6 px-3 py-2 ms-2"
                            )
                        ], className="d-flex align-items-center")
                    ], className="py-2")
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ])
        ], className="mb-4"),

        # Charts and positions
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("Portfolio Growth", className="mb-0"),
                        html.Small("Real-time equity curve", className="text-muted")
                    ]),
                    dbc.CardBody([
                        dbc.Spinner(
                            dcc.Graph(id='equity-curve', config={'displayModeBar': True}),
                            color="primary"
                        )
                    ])
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Recent Signals", className="mb-0")),
                    dbc.CardBody(id='recent-signals', style={'maxHeight': '400px', 'overflowY': 'auto'})
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ], width=4)
        ], className="mb-4"),

        # Positions table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("Open Positions", className="mb-0 d-inline-block"),
                            dbc.Badge(id="position-count", color="primary", className="ms-2")
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Spinner(
                            html.Div(id='positions-table'),
                            color="primary"
                        )
                    ])
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ])
        ], className="mb-4"),

        # Performance metrics
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Performance Metrics", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='performance-metrics', config={'displayModeBar': False})
                    ])
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Risk Utilization", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(id='risk-metrics', config={'displayModeBar': False})
                    ])
                ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
            ], width=6)
        ]),

        # Auto-refresh interval
        dcc.Interval(id='dashboard-interval', interval=5000, n_intervals=0),

        # Toast for notifications
        html.Div(id='notification-container')
    ])

def create_trader_card(trader_data):
    """Create a trader management card (simplified - read-only for now)"""
    trader_id = trader_data.get('id', '')
    is_active = trader_data.get('active', False)
    status_color = COLORS['success'] if is_active else COLORS['text_secondary']
    status_icon = '🟢' if is_active else '🔴'

    return dbc.Card([
        dbc.CardBody([
            # Header row with name
            dbc.Row([
                dbc.Col([
                    html.H5([
                        html.Span(status_icon, className="me-2"),
                        trader_data.get('name', 'Unknown'),
                        dbc.Badge(
                            "PAPER" if trader_data.get('paper_trade_only') else "LIVE",
                            color="warning" if trader_data.get('paper_trade_only') else "danger",
                            className="ms-2"
                        ),
                        dbc.Badge(
                            "ACTIVE" if is_active else "INACTIVE",
                            color="success" if is_active else "secondary",
                            className="ms-2"
                        )
                    ], className="mb-1"),
                    html.Small([
                        f"Source: {trader_data.get('source', 'unknown').title()} | ",
                        f"Priority: {trader_data.get('priority', 1)}"
                    ], className="text-muted")
                ], width=12),
            ], className="mb-3"),

            # Performance metrics
            html.Div([
                html.H6("Performance", className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        html.Small("Signals", className="text-muted d-block"),
                        html.Strong(f"{trader_data.get('signals_copied', 0)}/{trader_data.get('total_signals', 0)}")
                    ], width=3),
                    dbc.Col([
                        html.Small("Win Rate", className="text-muted d-block"),
                        html.Strong(f"{trader_data.get('win_count', 0)}/{trader_data.get('signals_copied', 0)}" if trader_data.get('signals_copied', 0) > 0 else "N/A")
                    ], width=3),
                    dbc.Col([
                        html.Small("Total P&L", className="text-muted d-block"),
                        html.Strong(
                            f"${trader_data.get('total_pnl', 0):+,.2f}",
                            style={'color': COLORS['success'] if trader_data.get('total_pnl', 0) >= 0 else COLORS['danger']}
                        )
                    ], width=3),
                    dbc.Col([
                        html.Small("Avg/Trade", className="text-muted d-block"),
                        html.Strong(
                            f"${trader_data.get('total_pnl', 0) / max(trader_data.get('signals_copied', 1), 1):+,.2f}"
                        )
                    ], width=3)
                ])
            ], className="mb-3 p-2", style={'backgroundColor': COLORS['surface_light'], 'borderRadius': '4px'}),

            # Configuration display (read-only for now)
            html.Div([
                html.H6("Configuration", className="mb-2"),
                html.Ul([
                    html.Li(f"Position Multiplier: {trader_data.get('position_multiplier', 1.0)}x"),
                    html.Li(f"Min Confidence: {trader_data.get('min_confidence', 0.7)*100:.0f}%"),
                    html.Li(f"Max Leverage: {trader_data.get('max_leverage', 5)}x"),
                    html.Li(f"Token Filter: {', '.join(trader_data.get('token_whitelist', [])) if trader_data.get('token_whitelist') else 'All tokens'}"),
                ], className="small mb-0")
            ], className="mb-2 p-2", style={'backgroundColor': COLORS['surface_light'], 'borderRadius': '4px'})
        ])
    ], className="mb-3", style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})

def create_traders_layout():
    return html.Div([
        # Header with add button
        dbc.Row([
            dbc.Col([
                html.H3("🎯 Trader Management", className="mb-0")
            ], width=8),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-plus me-2"), "Add Trader"],
                    id="add-trader-btn",
                    color="success",
                    className="float-end"
                )
            ], width=4)
        ], className="mb-4"),

        # Filters
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='trader-filter',
                    options=[
                        {'label': 'All Traders', 'value': 'all'},
                        {'label': 'Active Only', 'value': 'active'},
                        {'label': 'Inactive Only', 'value': 'inactive'},
                        {'label': 'Paper Trade', 'value': 'paper'},
                        {'label': 'Live Trade', 'value': 'live'}
                    ],
                    value='all',
                    clearable=False,
                    style={'backgroundColor': COLORS['surface']}
                )
            ], width=6),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-sync me-2"), "Refresh"],
                    id="refresh-traders-btn",
                    color="primary",
                    outline=True,
                    className="float-end"
                )
            ], width=6)
        ], className="mb-4"),

        # Trader cards container
        html.Div(id='traders-container'),

        # Add trader modal
        dbc.Modal([
            dbc.ModalHeader("Add New Trader"),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Trader Name"),
                            dbc.Input(id="new-trader-name", placeholder="e.g., My Telegram Friend")
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Source"),
                            dcc.Dropdown(
                                id="new-trader-source",
                                options=[
                                    {'label': 'Binance', 'value': 'binance'},
                                    {'label': 'Telegram', 'value': 'telegram'},
                                    {'label': 'Manual', 'value': 'manual'}
                                ],
                                value='telegram'
                            )
                        ], width=6)
                    ], className="mb-3"),
                    dbc.Label("Position Multiplier"),
                    dcc.Slider(id="new-trader-multiplier", min=0.5, max=2.0, step=0.1, value=1.0,
                               marks={0.5: '0.5x', 1.0: '1.0x', 1.5: '1.5x', 2.0: '2.0x'}),
                    dbc.Label("Min Confidence", className="mt-3"),
                    dcc.Slider(id="new-trader-confidence", min=0.6, max=0.95, step=0.05, value=0.7,
                               marks={0.6: '60%', 0.7: '70%', 0.8: '80%', 0.9: '90%'}),
                    dbc.Label("Max Leverage", className="mt-3"),
                    dcc.Slider(id="new-trader-leverage", min=1, max=20, step=1, value=5,
                               marks={1: '1x', 5: '5x', 10: '10x', 20: '20x'}),
                    dbc.Switch(id="new-trader-paper", label="Paper Trade Only (Recommended)",
                              value=True, className="mt-3")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="cancel-add-trader", color="secondary", outline=True),
                dbc.Button("Add Trader", id="confirm-add-trader", color="success")
            ])
        ], id="add-trader-modal", size="lg", is_open=False),

        # Notification toast
        html.Div(id='trader-notification', className="position-fixed top-0 end-0 p-3", style={'zIndex': '9999'}),

        # Auto-refresh interval
        dcc.Interval(id='traders-refresh-interval', interval=10000, n_intervals=0)
    ])

def create_analytics_layout():
    return html.Div([
        dbc.Card([
            dbc.CardHeader(html.H4("Analytics & Backtesting", className="mb-0")),
            dbc.CardBody([
                html.P("Advanced analytics and backtesting tools coming soon...", className="text-muted")
            ])
        ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
    ])

def create_settings_layout():
    return html.Div([
        dbc.Card([
            dbc.CardHeader(html.H4("Settings & Configuration", className="mb-0")),
            dbc.CardBody([
                html.P("Configuration settings coming soon...", className="text-muted")
            ])
        ], style={'backgroundColor': COLORS['surface'], 'border': f'1px solid {COLORS["border"]}'})
    ])

# =====================================================
# APP LAYOUT
# =====================================================

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    create_navbar(),
    dbc.Container([
        html.Div(id='page-content')
    ], fluid=True, style={'backgroundColor': COLORS['background'], 'minHeight': '100vh'})
], style={'backgroundColor': COLORS['background']})

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
    [Output('portfolio-value', 'children'),
     Output('portfolio-change', 'children'),
     Output('daily-pnl', 'children'),
     Output('daily-pnl-change', 'children'),
     Output('total-roi', 'children'),
     Output('total-roi-change', 'children'),
     Output('max-drawdown', 'children'),
     Output('position-count', 'children')],
    Input('dashboard-interval', 'n_intervals')
)
def update_metrics(n):
    """Update top metrics cards with real data"""
    metrics = data_provider.get_portfolio_metrics()
    risk_metrics = data_provider.get_risk_metrics()

    # Format portfolio value
    portfolio_value = data_provider.format_currency(metrics['portfolio_value'])
    portfolio_change = create_change_badge(metrics['daily_pnl_pct'])

    # Format daily P&L
    daily_pnl = data_provider.format_currency(metrics['daily_pnl'])
    daily_pnl_change = create_change_badge(metrics['daily_pnl_pct'])

    # Format ROI
    total_roi = data_provider.format_percentage(metrics['total_roi'])
    total_roi_change = create_change_badge(metrics['total_roi'])

    # Format drawdown
    max_drawdown = data_provider.format_percentage(metrics['max_drawdown'], include_sign=False)

    # Position count
    position_count = f"{risk_metrics['open_positions_count']}/{risk_metrics['max_positions']}"

    return (portfolio_value, portfolio_change, daily_pnl, daily_pnl_change,
            total_roi, total_roi_change, max_drawdown, position_count)

def create_change_badge(value):
    """Create a colored badge for percentage changes"""
    if value == 0:
        return html.Span("")

    color = "success" if value >= 0 else "danger"
    icon = "fa-arrow-up" if value >= 0 else "fa-arrow-down"

    return html.Div([
        html.I(className=f"fas {icon} me-1"),
        f"{value:+.2f}%"
    ], className=f"text-{color} small mt-2")

@app.callback(
    Output('equity-curve', 'figure'),
    Input('dashboard-interval', 'n_intervals')
)
def update_equity_curve(n):
    """Update equity curve with real portfolio data"""
    equity_data = data_provider.get_equity_curve(days=30)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_data['dates'],
        y=equity_data['values'],
        mode='lines',
        name='Portfolio Value',
        line=dict(color=COLORS['primary'], width=3),
        fill='tozeroy',
        fillcolor=f"rgba(88, 166, 255, 0.1)"
    ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['surface'],
        plot_bgcolor=COLORS['surface'],
        font=dict(family='Inter, sans-serif', color=COLORS['text']),
        xaxis=dict(
            title="Date",
            gridcolor=COLORS['border'],
            showgrid=True
        ),
        yaxis=dict(
            title="Value (USD)",
            gridcolor=COLORS['border'],
            showgrid=True
        ),
        hovermode='x unified',
        margin=dict(l=50, r=20, t=20, b=50)
    )

    return fig

@app.callback(
    Output('positions-table', 'children'),
    Input('dashboard-interval', 'n_intervals')
)
def update_positions_table(n):
    """Update positions table with real data"""
    positions = data_provider.get_open_positions()

    if not positions:
        return html.Div([
            html.I(className="fas fa-inbox fa-3x text-muted mb-3"),
            html.P("No open positions", className="text-muted")
        ], className="text-center py-5")

    return dash_table.DataTable(
        data=positions,
        columns=[{"name": i, "id": i} for i in positions[0].keys()],
        style_cell={
            'textAlign': 'left',
            'backgroundColor': COLORS['surface_light'],
            'color': COLORS['text'],
            'border': f'1px solid {COLORS["border"]}',
            'fontFamily': 'Inter, sans-serif',
            'padding': '12px'
        },
        style_header={
            'backgroundColor': COLORS['primary'],
            'color': 'white',
            'fontWeight': '600',
            'border': f'1px solid {COLORS["primary"]}'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'side', 'filter_query': '{side} = LONG'},
                'backgroundColor': 'rgba(63, 185, 80, 0.1)',
                'color': COLORS['success']
            },
            {
                'if': {'column_id': 'side', 'filter_query': '{side} = SHORT'},
                'backgroundColor': 'rgba(248, 81, 73, 0.1)',
                'color': COLORS['danger']
            },
            {
                'if': {'filter_query': '{current_pnl} contains +'},
                'color': COLORS['success'],
            },
            {
                'if': {'filter_query': '{current_pnl} contains -'},
                'color': COLORS['danger'],
            }
        ],
        page_size=10
    )

@app.callback(
    Output('recent-signals', 'children'),
    Input('dashboard-interval', 'n_intervals')
)
def update_signals(n):
    """Update recent signals list"""
    signals = data_provider.get_recent_signals(limit=5)

    if not signals:
        return html.Div([
            html.I(className="fas fa-signal fa-2x text-muted mb-2"),
            html.P("No recent signals", className="text-muted small")
        ], className="text-center py-4")

    signal_items = []
    for signal in signals:
        badge_color = "success" if signal['side'] == 'BUY' else "danger"
        signal_items.append(
            dbc.ListGroupItem([
                html.Div([
                    html.Strong(signal['trader'], style={'color': COLORS['text']}),
                    dbc.Badge(signal['side'], color=badge_color, className="ms-2")
                ]),
                html.Small([
                    f"{signal['symbol']} @ {signal['price']}",
                    html.Span(f" • {signal['confidence']}", className="text-muted ms-2"),
                    html.Span(f" • {signal['time']}", className="text-muted ms-2")
                ], className="text-muted")
            ], style={'backgroundColor': COLORS['surface_light'], 'border': f'1px solid {COLORS["border"]}'})
        )

    return dbc.ListGroup(signal_items)

@app.callback(
    [Output('performance-metrics', 'figure'),
     Output('risk-metrics', 'figure')],
    Input('dashboard-interval', 'n_intervals')
)
def update_analytics(n):
    """Update performance and risk metrics"""
    perf = data_provider.get_performance_metrics()
    risk = data_provider.get_risk_metrics()

    # Performance metrics chart
    perf_fig = go.Figure(data=[
        go.Bar(
            x=['Sharpe Ratio', 'Win Rate %', 'Profit Factor', 'Max DD %'],
            y=[perf['sharpe_ratio'], perf['win_rate'], perf['profit_factor'], -perf['max_drawdown']],
            marker_color=[COLORS['primary'], COLORS['success'], COLORS['warning'], COLORS['danger']]
        )
    ])

    perf_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['surface'],
        plot_bgcolor=COLORS['surface'],
        font=dict(family='Inter, sans-serif', color=COLORS['text']),
        xaxis=dict(gridcolor=COLORS['border']),
        yaxis=dict(gridcolor=COLORS['border']),
        margin=dict(l=50, r=20, t=20, b=50)
    )

    # Risk utilization gauge
    risk_fig = go.Figure()

    risk_fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=risk['drawdown_utilization'],
        title={'text': "Drawdown Utilization %"},
        delta={'reference': 0},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': COLORS['primary']},
            'steps': [
                {'range': [0, 50], 'color': COLORS['success']},
                {'range': [50, 75], 'color': COLORS['warning']},
                {'range': [75, 100], 'color': COLORS['danger']}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    risk_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=COLORS['surface'],
        plot_bgcolor=COLORS['surface'],
        font=dict(family='Inter, sans-serif', color=COLORS['text']),
        height=300
    )

    return perf_fig, risk_fig

# =====================================================
# TRADER MANAGEMENT CALLBACKS
# =====================================================

import requests

API_BASE = "http://localhost:8000"  # API server

@app.callback(
    Output('traders-container', 'children'),
    [Input('traders-refresh-interval', 'n_intervals'),
     Input('refresh-traders-btn', 'n_clicks'),
     Input('trader-filter', 'value')]
)
def update_traders_container(n_intervals, n_clicks, filter_value):
    """Load and display trader cards"""
    try:
        # Fetch traders from API
        response = requests.get(f"{API_BASE}/api/traders", timeout=2)
        if response.status_code == 200:
            data = response.json()
            traders = data.get('traders', [])
        else:
            traders = []
    except:
        # Fallback to trader_config if API not running
        from trader_config import get_trader_manager
        manager = get_trader_manager()
        traders = [t.to_dict() for t in manager.get_all_traders()]

    # Apply filter
    if filter_value == 'active':
        traders = [t for t in traders if t.get('active')]
    elif filter_value == 'inactive':
        traders = [t for t in traders if not t.get('active')]
    elif filter_value == 'paper':
        traders = [t for t in traders if t.get('paper_trade_only')]
    elif filter_value == 'live':
        traders = [t for t in traders if not t.get('paper_trade_only')]

    if not traders:
        return html.Div([
            html.I(className="fas fa-users fa-3x text-muted mb-3"),
            html.H5("No traders found", className="text-muted"),
            html.P("Click 'Add Trader' to get started", className="text-muted")
        ], className="text-center py-5")

    return [create_trader_card(trader) for trader in traders]

@app.callback(
    Output('add-trader-modal', 'is_open'),
    [Input('add-trader-btn', 'n_clicks'),
     Input('cancel-add-trader', 'n_clicks'),
     Input('confirm-add-trader', 'n_clicks')],
    [State('add-trader-modal', 'is_open')]
)
def toggle_add_trader_modal(add_clicks, cancel_clicks, confirm_clicks, is_open):
    """Toggle add trader modal"""
    if add_clicks or cancel_clicks or confirm_clicks:
        return not is_open
    return is_open

@app.callback(
    Output('trader-notification', 'children'),
    Input('confirm-add-trader', 'n_clicks'),
    [State('new-trader-name', 'value'),
     State('new-trader-source', 'value'),
     State('new-trader-multiplier', 'value'),
     State('new-trader-confidence', 'value'),
     State('new-trader-leverage', 'value'),
     State('new-trader-paper', 'value')],
    prevent_initial_call=True
)
def add_new_trader(n_clicks, name, source, multiplier, confidence, leverage, paper_only):
    """Add a new trader via API"""
    if not n_clicks or not name:
        return ""

    trader_id = name.lower().replace(' ', '_')

    trader_data = {
        'id': trader_id,
        'name': name,
        'source': source,
        'position_multiplier': multiplier,
        'min_confidence': confidence,
        'max_leverage': leverage,
        'paper_trade_only': paper_only,
        'active': True
    }

    try:
        response = requests.post(f"{API_BASE}/api/traders", json=trader_data, timeout=2)
        if response.status_code == 200:
            return dbc.Toast(
                f"✅ Trader {name} added successfully!",
                header="Success",
                icon="success",
                duration=4000,
                is_open=True,
                style={'backgroundColor': COLORS['success']}
            )
        else:
            return dbc.Toast(
                f"❌ Failed to add trader: {response.json().get('detail', 'Unknown error')}",
                header="Error",
                icon="danger",
                duration=4000,
                is_open=True,
                style={'backgroundColor': COLORS['danger']}
            )
    except Exception as e:
        return dbc.Toast(
            f"❌ API Error: {str(e)}",
            header="Error",
            icon="danger",
            duration=4000,
            is_open=True,
            style={'backgroundColor': COLORS['danger']}
        )

# Pattern-matched callbacks removed - using simple refresh-based approach
# Trader changes trigger container refresh via the interval component

# =====================================================
# RUN SERVER
# =====================================================

if __name__ == '__main__':
    print("🚀 Starting EchoTrade Pro Dashboard...")
    print("📊 Dashboard: http://localhost:8050")
    print(f"🤖 Bot Status: {'Paper Trading Mode' if not HAS_BACKEND else 'Connected to Backend'}")
    app.run(debug=True, host='0.0.0.0', port=8050)
