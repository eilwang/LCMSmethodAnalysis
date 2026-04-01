import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import numpy as np
import threading
from typing import Optional
import textwrap

linestyles = ['-', '--', '-.', ':']
palette = [f"rgba({r},{g},{b},1)" for r, g, b in [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
    (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
    (188, 189, 34), (23, 190, 207)
]]

def launch_dash_app(lccollection, twin_axes=False, markers=False, figsize=(12, 6), x_shift=0, port=8050, width=None, height=None):
    app = dash.Dash(__name__)

    use_adjusted = hasattr(lccollection, 'adjusted_methods') and lccollection.adjusted_methods and any(lccollection.adjusted_methods.values())
    methods_dict = lccollection.adjusted_methods if use_adjusted else lccollection.methods
    all_method_names = list(methods_dict.keys())
    all_sample_names = set()
    for m in all_method_names:
        if isinstance(methods_dict[m], dict):
            all_sample_names.update(methods_dict[m].keys())
    all_sample_names = sorted(list(all_sample_names))
    methods = {}
    for m in all_method_names:
        if isinstance(methods_dict[m], dict):
            methods[m] = methods_dict[m]
        else:
            methods[m] = methods_dict[m]
    first_gradient = None
    for m in all_method_names:
        if isinstance(methods_dict[m], dict):
            for s in methods_dict[m]:
                first_gradient = methods_dict[m][s].gradient
                break
        else:
            first_gradient = methods_dict[m].gradient
            break
        if first_gradient is not None:
            break
    available_columns = list(first_gradient.columns) if first_gradient is not None else []


    # UI: Multi-select for methods, samples, x/y columns, add-pair, toggle-pair, plot
    # Provide better defaults for usability
    default_method = all_method_names[0] if all_method_names else None
    default_sample = all_sample_names[0] if all_sample_names else None
    default_x = available_columns[0] if available_columns else None
    default_y = available_columns[1] if available_columns and len(available_columns) > 1 else None

    app.layout = html.Div([
        html.H2("LCMS Gradient Plotter"),
        html.Div([
            html.Label("Select Methods:"),
            dcc.Dropdown(
                id='method-multiselect',
                options=[{'label': m, 'value': m} for m in all_method_names],
                value=[default_method] if default_method else [],
                multi=True
            ),
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        html.Div([
            html.Label("Select Samples:"),
            dcc.Dropdown(
                id='sample-multiselect',
                options=[{'label': s, 'value': s} for s in all_sample_names],
                value=[default_sample] if default_sample else [],
                multi=True
            ),
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '2%'}),
        html.Div([
            html.Label("Select X column:"),
            dcc.Dropdown(
                id='x-col-dropdown',
                options=[{'label': c, 'value': c} for c in available_columns],
                value=default_x
            ),
            html.Label("Select Y column:"),
            dcc.Dropdown(
                id='y-col-dropdown',
                options=[{'label': c, 'value': c} for c in available_columns],
                value=default_y
            ),
            html.Button('Add X/Y Pair', id='add-pair-btn', n_clicks=0, style={'marginTop': '10px'}),
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '2%'}),
        html.Hr(),
        html.Div([
            html.Label("X/Y Pairs to Plot:"),
            html.Div(id='pair-list-div'),
            dcc.Store(id='xy-pairs-store', data=[(default_x, default_y)] if default_x and default_y else []),
            dcc.Checklist(id='pair-toggle-checklist', options=[{'label': f"{default_x} vs {default_y}", 'value': f"{default_x} vs {default_y}"}] if default_x and default_y else [], value=[f"{default_x} vs {default_y}"] if default_x and default_y else [], labelStyle={'display': 'block'}),
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        html.Div([
            dcc.Checklist(
                id='twinaxes-toggle',
                options=[{'label': 'Use Twin Axes (if 2 y)', 'value': 'twin'}],
                value=[]
            ),
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '2%'}),
        html.Hr(),
        dcc.Graph(id='gradient-plot'),
    ])

    from dash.dependencies import State
    from dash import html as htmlc

    from dash.dependencies import ALL
    @app.callback(
        [Output('xy-pairs-store', 'data'), Output('pair-list-div', 'children'), Output('pair-toggle-checklist', 'options'), Output('pair-toggle-checklist', 'value')],
        [Input('add-pair-btn', 'n_clicks'), Input({'type': 'delete-pair-btn', 'index': ALL}, 'n_clicks')],
        [State('x-col-dropdown', 'value'), State('y-col-dropdown', 'value'), State('xy-pairs-store', 'data'), State('pair-toggle-checklist', 'value')]
    )
    def add_or_delete_pair(n_clicks_add, n_clicks_delete, x_col, y_col, pairs, toggled_pairs):
        ctx = dash.callback_context
        if n_clicks_delete is None:
            n_clicks_delete = []
        if pairs is None:
            pairs = []
        if toggled_pairs is None:
            toggled_pairs = []
        # Handle add
        if ctx.triggered and ctx.triggered[0]['prop_id'].startswith('add-pair-btn'):
            if n_clicks_add > 0 and x_col and y_col and x_col != y_col:
                pair = (x_col, y_col)
                if pair not in pairs:
                    pairs.append(pair)
                    toggled_pairs.append(f"{x_col} vs {y_col}")
        # Handle delete
        elif ctx.triggered and 'delete-pair-btn' in ctx.triggered[0]['prop_id']:
            if n_clicks_delete:
                for i, n in enumerate(n_clicks_delete):
                    if n:
                        if i < len(pairs):
                            pair = pairs[i]
                            pair_label = f"{pair[0]} vs {pair[1]}"
                            pairs.pop(i)
                            if pair_label in toggled_pairs:
                                toggled_pairs.remove(pair_label)
                        break
        # Build pair list with delete buttons
        pair_list = []
        for i, (x, y) in enumerate(pairs):
            pair_label = f"{x} vs {y}"
            pair_list.append(htmlc.Li([
                pair_label,
                htmlc.Button('Delete', id={'type': 'delete-pair-btn', 'index': i}, n_clicks=0, style={'marginLeft': '10px'})
            ]))
        pair_list_div = htmlc.Ul(pair_list) if pair_list else "No pairs selected."
        checklist_options = [{'label': f"{x} vs {y}", 'value': f"{x} vs {y}"} for x, y in pairs]
        return pairs, pair_list_div, checklist_options, toggled_pairs

    @app.callback(
        Output('gradient-plot', 'figure'),
        [
            Input('method-multiselect', 'value'),
            Input('sample-multiselect', 'value'),
            Input('xy-pairs-store', 'data'),
            Input('pair-toggle-checklist', 'value'),
            Input('twinaxes-toggle', 'value')
        ]
    )
    def update_figure(selected_methods, selected_samples, xy_pairs, toggled_pairs, twinaxes_toggle):
        use_twin = 'twin' in twinaxes_toggle if twinaxes_toggle else False
        fig = go.Figure()
        # Only plot if at least one method, one sample, and one x/y pair are selected and toggled
        if not xy_pairs or not toggled_pairs or not selected_methods or not selected_samples:
            return dash.no_update
        # Only plot pairs that are toggled on
        col_pairs = [pair for pair in xy_pairs if f"{pair[0]} vs {pair[1]}" in toggled_pairs]
        x_cols = [x for x, y in col_pairs]
        y_cols = [y for x, y in col_pairs]

        traces = []
        for i, (method_name, method) in enumerate(methods.items()):
            if isinstance(method, dict):
                for s, m in method.items():
                    for pair_idx, (x_col, y_col) in enumerate(col_pairs):
                        if x_col not in m.gradient.columns or y_col not in m.gradient.columns:
                            continue
                        name = f"{s} - {method_name} - {x_col} vs {y_col}"
                        if selected_methods and method_name not in selected_methods:
                            continue
                        if selected_samples and s not in selected_samples:
                            continue
                        trace = go.Scatter(
                            x=m.gradient[x_col] + x_shift,
                            y=m.gradient[y_col],
                            mode='lines+markers' if markers else 'lines',
                            line=dict(
                                color=palette[i % len(palette)],
                                width=2,
                                dash=linestyles[pair_idx % len(linestyles)]
                            ),
                            name=name,
                            visible=True
                        )
                        traces.append(trace)
            else:
                for pair_idx, (x_col, y_col) in enumerate(col_pairs):
                    if x_col not in method.gradient.columns or y_col not in method.gradient.columns:
                        continue
                    name = f"{method_name} - {x_col} vs {y_col}"
                    if selected_methods and method_name not in selected_methods:
                        continue
                    trace = go.Scatter(
                        x=method.gradient[x_col] + x_shift,
                        y=method.gradient[y_col],
                        mode='lines+markers' if markers else 'lines',
                        line=dict(
                            color=palette[i % len(palette)],
                            width=2,
                            dash=linestyles[pair_idx % len(linestyles)]
                        ),
                        name=name,
                        visible=True
                    )
                    traces.append(trace)

        # Twin axes logic: if enabled and exactly 2 y_cols, assign y2 to traces with y2
        secondary_y_idxs = set()
        if use_twin and len(y_cols) == 2:
            y1, y2 = y_cols
            for idx, trace in enumerate(traces):
                if y2 in trace.name:
                    secondary_y_idxs.add(idx)
        for idx, trace in enumerate(traces):
            trace_dict = trace.to_plotly_json()
            if use_twin and idx in secondary_y_idxs:
                trace_dict['yaxis'] = 'y2'
            fig.add_trace(go.Scatter(**trace_dict))

        layout_args = dict(
            xaxis_title=x_cols[0] if len(x_cols) == 1 else "X Value",
            yaxis_title=y_cols[0] if len(y_cols) == 1 else "Value",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.15,
                title_text="",
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="black",
                borderwidth=1
            ),
            margin=dict(r=300, t=60, b=60, l=60),
            hovermode="x unified",
            width=width if width else figsize[0] * 80,
            height=height if height else figsize[1] * 80
        )
        if use_twin and len(y_cols) == 2:
            layout_args['yaxis'] = dict(
                title=y_cols[0],
                showgrid=True
            )
            layout_args['yaxis2'] = dict(
                title=y_cols[1],
                overlaying='y',
                side='right',
                showgrid=False
            )
        fig.update_layout(**layout_args)
        max_len = 35
        for trace in fig.data:
            if len(trace.name) > max_len:
                trace.name = '<br>'.join(textwrap.wrap(trace.name, width=max_len))
        return fig

    @app.callback(
        Output('gradient-plot', 'figure'),
        [Input('gradient-plot', 'id')]
    )
    def update_figure(_):
        fig = go.Figure()
        if available_columns:
            x_col = available_columns[0]
            y_col = available_columns[1] if len(available_columns) > 1 else available_columns[0]
            for i, (method_name, method) in enumerate(methods.items()):
                if hasattr(method, 'gradient'):
                    m = method
                    if x_col in m.gradient.columns and y_col in m.gradient.columns:
                        fig.add_trace(go.Scatter(
                            x=m.gradient[x_col] + x_shift,
                            y=m.gradient[y_col],
                            mode='lines',
                            name=method_name,
                            line=dict(color=palette[i % len(palette)], dash=linestyles[i % len(linestyles)])
                        ))
                elif isinstance(method, dict):
                    for s, m in method.items():
                        if x_col in m.gradient.columns and y_col in m.gradient.columns:
                            fig.add_trace(go.Scatter(
                                x=m.gradient[x_col] + x_shift,
                                y=m.gradient[y_col],
                                mode='lines',
                                name=f"{s} - {method_name}",
                                line=dict(color=palette[i % len(palette)], dash=linestyles[i % len(linestyles)])
                            ))
        fig.update_layout(
            xaxis_title=x_col if available_columns else "X",
            yaxis_title=y_col if available_columns else "Y",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.15, font=dict(size=11)),
            margin=dict(r=300, t=60, b=60, l=60),
            hovermode="x unified",
            width=width if width else figsize[0] * 80,
            height=height if height else figsize[1] * 80
        )
        return fig

    def run_dash():
        app.run(debug=False, port=port)

    threading.Thread(target=run_dash, daemon=True).start()
    print(f"Dash app running at http://127.0.0.1:{port}")

class DashPlots:
    @staticmethod
    def plot_gradients_dash(
        lccollection=None,
        twin_axes: bool = False,
        markers: bool = False,
        figsize=(12, 6),
        x_shift=0,
        port: int = 8050,
        width: Optional[int] = None,
        height: Optional[int] = None
    ):
        """
        Launch a Dash app for interactive gradient plotting with toggles.
        """
        launch_dash_app(
            lccollection=lccollection,
            twin_axes=twin_axes,
            markers=markers,
            figsize=figsize,
            x_shift=x_shift,
            port=port,
            width=width,
            height=height
        )
