"""
Search Dataset Explorer Dashboard

Interactive Dash application for loading and exploring search results
from DIA-NN, Spectronaut, and other search engines.

Usage:
    python dashboard/search_explorer.py
    
    Or in Python:
    >>> from dashboard.search_explorer import launch_explorer
    >>> launch_explorer(port=8050)
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Optional, Dict, List
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.search import SearchCollection, SearchLoader


class SearchExplorerDashboard:
    """Interactive dashboard for exploring search datasets."""
    
    def __init__(self, port: int = 8050, debug: bool = True):
        """
        Initialize dashboard.
        
        Parameters:
        -----------
        port : int
            Port to run dashboard on (default: 8050)
        debug : bool
            Run in debug mode (default: True)
        """
        self.port = port
        self.debug = debug
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.collection: Optional[SearchCollection] = None
        
        # Color palette
        self.colors = {
            'background': '#f8f9fa',
            'text': '#212529',
            'primary': '#007bff',
            'secondary': '#6c757d',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8',
        }
        
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("🔬 Search Dataset Explorer", 
                       style={'textAlign': 'center', 'color': self.colors['primary']}),
                html.P("Interactive exploration of DIA-NN, Spectronaut, and FragPipe search results",
                      style={'textAlign': 'center', 'color': self.colors['secondary']}),
            ], style={'padding': '20px', 'backgroundColor': 'white', 'marginBottom': '20px'}),
            
            # Main content
            html.Div([
                # Tabs
                dcc.Tabs(id='main-tabs', value='load-tab', children=[
                    dcc.Tab(label='📁 Load Data', value='load-tab'),
                    dcc.Tab(label='📊 Overview', value='overview-tab'),
                    dcc.Tab(label='🔍 Explore', value='explore-tab'),
                    dcc.Tab(label='📈 Visualize', value='visualize-tab'),
                    dcc.Tab(label='🎯 Filter', value='filter-tab'),
                ]),
                
                # Tab content
                html.Div(id='tab-content', style={'padding': '20px'}),
                
            ], style={'backgroundColor': self.colors['background'], 'minHeight': '80vh'}),
            
            # Store components for data
            dcc.Store(id='collection-store'),
            dcc.Store(id='current-level-store'),
            dcc.Store(id='filtered-data-store'),
            
            # Footer
            html.Div([
                html.Hr(),
                html.P("Search Dataset Explorer | Built with Dash + Plotly",
                      style={'textAlign': 'center', 'color': self.colors['secondary']})
            ], style={'padding': '10px'}),
            
        ], style={'fontFamily': 'Arial, sans-serif'})
    
    def _get_load_tab_content(self):
        """Get content for Load Data tab."""
        return html.Div([
            html.H3("Load Search Results"),
            
            html.Div([
                # Search type selection
                html.Div([
                    html.Label("Search Type:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='search-type-dropdown',
                        options=[
                            {'label': 'BPS DIA-NN', 'value': 'bps_diann'},
                            {'label': 'BPS Spectronaut', 'value': 'bps_spectronaut'},
                            {'label': 'FragPipe DIA-NN', 'value': 'fragpipe_diann'},
                            {'label': 'DIA-NN DIA-NN', 'value': 'diann_diann'},
                        ],
                        value='bps_diann',
                        style={'width': '300px'}
                    ),
                ], style={'marginBottom': '20px'}),
                
                # Path input
                html.Div([
                    html.Label("Data Path:", style={'fontWeight': 'bold'}),
                    dcc.Input(
                        id='data-path-input',
                        type='text',
                        placeholder='Enter path to search results folder or zip file...',
                        style={'width': '600px', 'marginRight': '10px'}
                    ),
                    html.Button('Browse', id='browse-btn', n_clicks=0,
                               style={'backgroundColor': self.colors['secondary'], 'color': 'white'}),
                ], style={'marginBottom': '20px'}),
                
                # Levels selection
                html.Div([
                    html.Label("Levels to Load:", style={'fontWeight': 'bold'}),
                    dcc.Checklist(
                        id='levels-checklist',
                        options=[
                            {'label': ' Precursor', 'value': 'precursor'},
                            {'label': ' Protein', 'value': 'protein'},
                            {'label': ' Gene', 'value': 'gene'},
                            {'label': ' Peptide', 'value': 'peptide'},
                        ],
                        value=['precursor', 'protein'],
                        inline=True,
                        style={'marginLeft': '10px'}
                    ),
                ], style={'marginBottom': '20px'}),
                
                # Advanced options
                html.Details([
                    html.Summary("Advanced Options", style={'fontWeight': 'bold', 'cursor': 'pointer'}),
                    html.Div([
                        html.Label("Sections:"),
                        dcc.Checklist(
                            id='sections-checklist',
                            options=[
                                {'label': ' var', 'value': 'var'},
                                {'label': ' obs', 'value': 'obs'},
                                {'label': ' x', 'value': 'x'},
                                {'label': ' layers', 'value': 'layers'},
                            ],
                            value=[],
                            inline=True,
                        ),
                        html.Br(),
                        html.Label("Strict Mode:"),
                        dcc.Checklist(
                            id='strict-checkbox',
                            options=[{'label': ' Require all columns', 'value': 'strict'}],
                            value=[],
                        ),
                        html.Br(),
                        html.Label("Verbose:"),
                        dcc.Checklist(
                            id='verbose-checkbox',
                            options=[{'label': ' Show detailed loading info', 'value': 'verbose'}],
                            value=['verbose'],
                        ),
                    ], style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#f0f0f0'})
                ], style={'marginBottom': '20px'}),
                
                # Load button
                html.Button('🚀 Load Data', id='load-btn', n_clicks=0,
                           style={'backgroundColor': self.colors['success'], 'color': 'white',
                                 'fontSize': '18px', 'padding': '10px 30px', 'border': 'none',
                                 'borderRadius': '5px', 'cursor': 'pointer'}),
                
                # Status/results
                html.Div(id='load-status', style={'marginTop': '20px'}),
                
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px'}),
        ])
    
    def _get_overview_tab_content(self):
        """Get content for Overview tab."""
        return html.Div([
            html.H3("Collection Overview"),
            html.Div(id='overview-content'),
        ])
    
    def _get_explore_tab_content(self):
        """Get content for Explore tab."""
        return html.Div([
            html.H3("Data Explorer"),
            
            # Level and sample selection
            html.Div([
                html.Div([
                    html.Label("Level:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='explore-level-dropdown', style={'width': '200px'}),
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Sample:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='explore-sample-dropdown', style={'width': '300px'}),
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Button('Load', id='explore-load-btn', n_clicks=0,
                           style={'backgroundColor': self.colors['info'], 'color': 'white'}),
            ], style={'marginBottom': '20px'}),
            
            # Data table
            html.Div([
                html.H4("Data Preview"),
                html.Div(id='data-table-container'),
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px'}),
        ])
    
    def _get_visualize_tab_content(self):
        """Get content for Visualize tab."""
        return html.Div([
            html.H3("Data Visualization"),
            
            # Plot controls
            html.Div([
                html.Div([
                    html.Label("Plot Type:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='plot-type-dropdown',
                        options=[
                            {'label': 'Histogram', 'value': 'histogram'},
                            {'label': 'Scatter Plot', 'value': 'scatter'},
                            {'label': 'Box Plot', 'value': 'box'},
                            {'label': 'Violin Plot', 'value': 'violin'},
                            {'label': 'Heatmap', 'value': 'heatmap'},
                            {'label': 'RT Distribution', 'value': 'rtdist'},
                        ],
                        value='histogram',
                        style={'width': '200px'}
                    ),
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("X Variable:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='plot-x-dropdown', style={'width': '200px'}),
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Y Variable:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='plot-y-dropdown', style={'width': '200px'}),
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Color By:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='plot-color-dropdown', style={'width': '200px'}),
                ], style={'display': 'inline-block'}),
            ], style={'marginBottom': '20px'}),
            
            # Plot
            html.Div([
                dcc.Graph(id='main-plot', style={'height': '600px'}),
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px'}),
        ])
    
    def _get_filter_tab_content(self):
        """Get content for Filter tab."""
        return html.Div([
            html.H3("Data Filtering"),
            
            html.Div([
                html.Label("Add filters to subset your data:", style={'fontWeight': 'bold'}),
                
                # Filter builder
                html.Div(id='filter-builder', children=[
                    html.Div([
                        dcc.Dropdown(id='filter-column-dropdown', placeholder='Select column',
                                   style={'width': '200px', 'display': 'inline-block', 'marginRight': '10px'}),
                        dcc.Dropdown(id='filter-operator-dropdown',
                                   options=[
                                       {'label': '>', 'value': '>'},
                                       {'label': '<', 'value': '<'},
                                       {'label': '>=', 'value': '>='},
                                       {'label': '<=', 'value': '<='},
                                       {'label': '==', 'value': '=='},
                                       {'label': '!=', 'value': '!='},
                                       {'label': 'contains', 'value': 'contains'},
                                   ],
                                   value='>',
                                   style={'width': '100px', 'display': 'inline-block', 'marginRight': '10px'}),
                        dcc.Input(id='filter-value-input', type='text', placeholder='Value',
                                style={'width': '150px', 'display': 'inline-block', 'marginRight': '10px'}),
                        html.Button('Add Filter', id='add-filter-btn', n_clicks=0,
                                  style={'backgroundColor': self.colors['info'], 'color': 'white'}),
                    ]),
                ], style={'marginBottom': '20px'}),
                
                # Active filters
                html.Div([
                    html.H4("Active Filters:"),
                    html.Div(id='active-filters-display'),
                ], style={'marginTop': '20px'}),
                
                # Apply button
                html.Button('Apply Filters', id='apply-filters-btn', n_clicks=0,
                           style={'backgroundColor': self.colors['success'], 'color': 'white',
                                 'marginTop': '20px'}),
                
                # Results
                html.Div(id='filter-results', style={'marginTop': '20px'}),
                
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px'}),
        ])
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            Output('tab-content', 'children'),
            Input('main-tabs', 'value')
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'load-tab':
                return self._get_load_tab_content()
            elif active_tab == 'overview-tab':
                return self._get_overview_tab_content()
            elif active_tab == 'explore-tab':
                return self._get_explore_tab_content()
            elif active_tab == 'visualize-tab':
                return self._get_visualize_tab_content()
            elif active_tab == 'filter-tab':
                return self._get_filter_tab_content()
            return html.Div("Tab content")
        
        @self.app.callback(
            [Output('load-status', 'children'),
             Output('collection-store', 'data')],
            Input('load-btn', 'n_clicks'),
            [State('search-type-dropdown', 'value'),
             State('data-path-input', 'value'),
             State('levels-checklist', 'value'),
             State('sections-checklist', 'value'),
             State('strict-checkbox', 'value'),
             State('verbose-checkbox', 'value')]
        )
        def load_data(n_clicks, search_type, data_path, levels, sections, strict, verbose):
            """Load search data into collection."""
            if n_clicks == 0 or not data_path:
                return "", None
            
            try:
                # Parse search_type into container and engine for backward compatibility
                parts = search_type.split('_')
                if len(parts) == 2:
                    container, engine = parts
                else:
                    container = 'bps'
                    engine = 'diann'
                
                # Create collection with new parameters
                self.collection = SearchCollection(container=container, engine=engine)
                
                # Load data
                self.collection.add_searches(
                    path=data_path,
                    levels=levels if levels else None,
                    sections=sections if sections else None,
                    strict='strict' in strict,
                    verbose='verbose' in verbose
                )
                
                # Get summary
                summary = self.collection.summary_df()
                
                status = html.Div([
                    html.H4("✅ Data Loaded Successfully!", style={'color': self.colors['success']}),
                    html.P(f"Loaded {len(self.collection.list_levels())} levels with {len(self.collection.list_samples())} samples"),
                    html.H5("Summary:"),
                    dash_table.DataTable(
                        data=summary.to_dict('records'),
                        columns=[{'name': i, 'id': i} for i in summary.columns],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'},
                    )
                ])
                
                # Store collection info
                collection_data = {
                    'search_type': search_type,
                    'container': container,
                    'engine': engine,
                    'levels': self.collection.list_levels(),
                    'samples': self.collection.list_samples(),
                }
                
                return status, json.dumps(collection_data)
                
            except Exception as e:
                error_msg = html.Div([
                    html.H4("❌ Error Loading Data", style={'color': self.colors['danger']}),
                    html.P(f"Error: {str(e)}"),
                    html.Pre(f"Make sure the path exists and contains valid search results."),
                ])
                return error_msg, None
        
        @self.app.callback(
            Output('overview-content', 'children'),
            Input('collection-store', 'data')
        )
        def update_overview(collection_data):
            """Update overview tab with collection info."""
            if not collection_data or not self.collection:
                return html.Div("No data loaded. Please load data first.", 
                              style={'color': self.colors['warning']})
            
            data = json.loads(collection_data)
            
            overview = html.Div([
                html.Div([
                    html.H4("📊 Collection Statistics"),
                    html.Ul([
                        html.Li(f"Container: {data.get('container', 'N/A')}"),
                        html.Li(f"Engine: {data.get('engine', 'N/A')}"),
                        html.Li(f"Levels: {', '.join(data['levels'])}"),
                        html.Li(f"Total Samples: {len(data['samples'])}"),
                    ]),
                ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px',
                         'marginBottom': '20px'}),
                
                html.Div([
                    html.H4("📝 Samples"),
                    html.Div([
                        html.P(sample) for sample in data['samples'][:20]
                    ] + ([html.P(f"... and {len(data['samples']) - 20} more")] if len(data['samples']) > 20 else [])),
                ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px'}),
            ])
            
            return overview
        
        @self.app.callback(
            [Output('explore-level-dropdown', 'options'),
             Output('explore-level-dropdown', 'value')],
            Input('collection-store', 'data')
        )
        def update_explore_levels(collection_data):
            """Update level dropdown in explore tab."""
            if not collection_data:
                return [], None
            
            data = json.loads(collection_data)
            options = [{'label': level, 'value': level} for level in data['levels']]
            value = data['levels'][0] if data['levels'] else None
            
            return options, value
        
        @self.app.callback(
            [Output('explore-sample-dropdown', 'options'),
             Output('explore-sample-dropdown', 'value')],
            Input('collection-store', 'data')
        )
        def update_explore_samples(collection_data):
            """Update sample dropdown in explore tab."""
            if not collection_data:
                return [], None
            
            data = json.loads(collection_data)
            options = [{'label': 'All Samples', 'value': 'all'}] + \
                     [{'label': sample, 'value': sample} for sample in data['samples']]
            
            return options, 'all'
        
        @self.app.callback(
            Output('data-table-container', 'children'),
            Input('explore-load-btn', 'n_clicks'),
            [State('explore-level-dropdown', 'value'),
             State('explore-sample-dropdown', 'value')]
        )
        def update_data_table(n_clicks, level, sample):
            """Update data table in explore tab."""
            if n_clicks == 0 or not self.collection or not level:
                return html.P("Select level and click Load to view data")
            
            try:
                # Get data
                sample_filter = None if sample == 'all' else sample
                df = self.collection.to_df(level=level, samples=[sample_filter] if sample_filter else None)
                
                # Show first 1000 rows
                df_display = df.head(1000)
                
                table = dash_table.DataTable(
                    data=df_display.to_dict('records'),
                    columns=[{'name': i, 'id': i} for i in df_display.columns],
                    page_size=50,
                    style_table={'overflowX': 'auto', 'maxHeight': '600px', 'overflowY': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={'backgroundColor': self.colors['primary'], 'color': 'white', 'fontWeight': 'bold'},
                    filter_action='native',
                    sort_action='native',
                )
                
                return html.Div([
                    html.P(f"Showing first 1000 of {len(df):,} rows"),
                    table
                ])
                
            except Exception as e:
                return html.Div(f"Error loading data: {str(e)}", style={'color': self.colors['danger']})
    
    def run(self):
        """Run the dashboard."""
        print(f"\n🚀 Starting Search Dataset Explorer...")
        print(f"📊 Dashboard will be available at: http://localhost:{self.port}")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        self.app.run_server(debug=self.debug, port=self.port, host='0.0.0.0')


def launch_explorer(port: int = 8050, debug: bool = True):
    """
    Launch the search dataset explorer dashboard.
    
    Parameters:
    -----------
    port : int
        Port to run dashboard on (default: 8050)
    debug : bool
        Run in debug mode (default: True)
    
    Example:
    --------
    >>> from dashboard.search_explorer import launch_explorer
    >>> launch_explorer(port=8050)
    """
    dashboard = SearchExplorerDashboard(port=port, debug=debug)
    dashboard.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Launch Search Dataset Explorer Dashboard')
    parser.add_argument('--port', type=int, default=8050, help='Port to run dashboard on')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug mode')
    
    args = parser.parse_args()
    
    launch_explorer(port=args.port, debug=not args.no_debug)
