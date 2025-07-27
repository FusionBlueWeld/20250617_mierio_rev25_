import plotly.utils
import plotly.graph_objects as go
import json
from plotly.utils import PlotlyJSONEncoder
import pandas as pd
import numpy as np
import itertools
from flask import current_app, session
from . import surrogate_model

def generate_scatter_plot(df_filtered, x_col, y_col, z_col):
    if df_filtered.empty:
        return None, None

    z_min = df_filtered[z_col].min()
    z_max = df_filtered[z_col].max()

    scatter_data = go.Scattergl(
        x=df_filtered[x_col],
        y=df_filtered[y_col],
        mode='markers',
        marker=dict(
            size=10,
            color=df_filtered[z_col],
            colorscale='Jet',
            colorbar=dict(title=z_col),
            cmin=z_min,
            cmax=z_max,
            showscale=True
        ),
        hoverinfo='x+y+z',
        hovertemplate=f'<b>{x_col}:</b> %{{x}}<br><b>{y_col}:</b> %{{y}}<br><b>{z_col}:</b> %{{marker.color}}<extra></extra>'
    )

    layout = go.Layout(
        title=f'Scatter Plot: {z_col} vs {x_col} and {y_col}',
        xaxis=dict(title=x_col, automargin=True),
        yaxis=dict(title=y_col, automargin=True),
        hovermode='closest',
        margin=dict(t=50, b=50, l=50, r=50),
        uirevision='true'
    )
    
    return json.dumps([scatter_data], cls=plotly.utils.PlotlyJSONEncoder), \
           json.dumps(layout, cls=plotly.utils.PlotlyJSONEncoder)

def generate_contour_plot(grid_results, x_col, y_col, z_col):
    if not grid_results:
        return None

    try:
        x_coords = grid_results['x_grid']
        y_coords = grid_results['y_grid']
        z_matrix = grid_results['z_grid']
    except KeyError as e:
        current_app.logger.error(f"grid_results dictionary is missing a key: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to extract data from grid_results: {e}")
        return None

    contour_trace = go.Contour(
        x=x_coords,
        y=y_coords,
        z=z_matrix,
        colorscale='jet',
        showscale=False,
        connectgaps=True,
        contours_coloring='fill', 
        line_smoothing=0.85,
        opacity=0.5,
        name='Overlap Contour',
        zorder=0 
    )

    return json.dumps(contour_trace, cls=PlotlyJSONEncoder)


def generate_grid_with_surrogate(model_path, scaler_path, x_col, y_col, z_col, constants, resolution=50):
    current_app.logger.info("--- Generating grid data with surrogate model ---")
    
    model, scaler = surrogate_model.load_model_and_scaler(model_path, scaler_path)
    if model is None or scaler is None:
        raise FileNotFoundError("Failed to load model or scaler.")

    current_app.logger.debug("Model and scaler loaded successfully.")

    feature_names = scaler.feature_names_in_
    min_vals, max_vals = scaler.data_min_, scaler.data_max_
    
    try:
        x_min, x_max = min_vals[list(feature_names).index(x_col)], max_vals[list(feature_names).index(x_col)]
        y_min, y_max = min_vals[list(feature_names).index(y_col)], max_vals[list(feature_names).index(y_col)]
    except ValueError as e:
        raise KeyError(f"Axis '{e.args[0].replace('is not in list', '')}' not found in the features the model was trained on.")

    x_points = np.linspace(x_min, x_max, resolution)
    y_points = np.linspace(y_min, y_max, resolution)

    grid_points = list(itertools.product(x_points, y_points))
    input_df = pd.DataFrame(grid_points, columns=[x_col, y_col])

    for const_name, const_value in constants.items():
        input_df[const_name] = float(const_value)
        
    input_df = input_df[feature_names]

    current_app.logger.debug(f"DataFrame shape for prediction: {input_df.shape}")
    current_app.logger.debug(f"DataFrame columns for prediction (should be ordered): {input_df.columns.tolist()}")
    current_app.logger.debug(f"First 5 rows of prediction input:\n{input_df.head().to_string()}")

    predictions = surrogate_model.predict_with_loaded_model(model, scaler, input_df)
    
    target_headers = [h for h in session.get('target_headers', []) if h.lower() != 'main_id']
    if not target_headers:
         raise ValueError("Target headers not found in session. Please re-upload the target CSV.")

    predictions_df = pd.DataFrame(predictions, columns=target_headers)

    z_values = predictions_df[z_col].values
    
    z_grid = z_values.reshape((resolution, resolution)).T
    
    grid_results = {
        'x_grid': x_points,
        'y_grid': y_points,
        'z_grid': z_grid,
    }

    current_app.logger.debug(f"Returning grid_results with shapes: x_grid={len(grid_results['x_grid'])}, y_grid={len(grid_results['y_grid'])}, z_grid shape={grid_results['z_grid'].shape}")

    current_app.logger.info("--- Grid data generation finished ---")
    return grid_results

def calculate_overlap_grid(model, scaler, x_col, y_col, z_col, constants, resolution=10):
    if model is None or scaler is None:
        current_app.logger.warning("calculate_overlap_grid called but model or scaler is None.")
        return None

    current_app.logger.info("--- Calculating overlap grid data ---")

    feature_names = scaler.feature_names_in_
    min_vals, max_vals = scaler.data_min_, scaler.data_max_
    
    try:
        x_min, x_max = min_vals[list(feature_names).index(x_col)], max_vals[list(feature_names).index(x_col)]
        y_min, y_max = min_vals[list(feature_names).index(y_col)], max_vals[list(feature_names).index(y_col)]
    except ValueError as e:
        raise KeyError(f"Axis '{e.args[0].replace(' is not in list', '')}' not found in the features the model was trained on.")

    x_points = np.linspace(x_min, x_max, resolution)
    y_points = np.linspace(y_min, y_max, resolution)

    grid_points = list(itertools.product(x_points, y_points))
    input_df = pd.DataFrame(grid_points, columns=[x_col, y_col])
    
    for const_name, const_value in constants.items():
        input_df[const_name] = float(const_value)
        
    input_df = input_df[feature_names]

    predictions = surrogate_model.predict_with_loaded_model(model, scaler, input_df)
    
    target_headers = [h for h in session.get('target_headers', []) if h.lower() != 'main_id']
    if not target_headers:
         raise ValueError("Target headers not found in session. Please re-upload the target CSV.")

    predictions_df = pd.DataFrame(predictions, columns=target_headers)

    z_values = predictions_df[z_col].values
    
    z_grid = z_values.reshape((resolution, resolution)).T
    
    grid_results = {
        'x_grid': x_points.tolist(),
        'y_grid': y_points.tolist(),
        'z_grid': z_grid.tolist(),
    }
    
    current_app.logger.info("--- Overlap grid data calculation finished ---")
    return grid_results
