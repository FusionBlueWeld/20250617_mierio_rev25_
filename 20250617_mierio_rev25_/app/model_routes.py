import os
import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
import pandas as pd
import numpy as np
import itertools
from app.model_evaluator import calculate_targets
from app.data_utils import load_and_merge_csvs
from . import surrogate_model

model_bp = Blueprint('model_bp', __name__)

@model_bp.route('/save_model_config', methods=['POST'])
def save_model_config():
    data = request.get_json()
    model_name = data.get('modelName', '')
    fitting_config_from_frontend = data.get('fittingConfig')
    fitting_method = data.get('fittingMethod')
    functions = data.get('functions')

    if not fitting_config_from_frontend or not functions:
        return jsonify({'error': 'No model configuration data received.'}), 400

    feature_filepath = session.get('feature_filepath')
    target_filepath = session.get('target_filepath')

    if not feature_filepath or not target_filepath:
        return jsonify({'error': 'Feature or Target CSV files not loaded. Cannot save configuration.'}), 400

    fitting_config_inverted = {}
    for feature_name, target_func_map in fitting_config_from_frontend.items():
        for target_name, func_name in target_func_map.items():
            if target_name.lower() == 'main_id' or feature_name.lower() == 'main_id':
                continue
            if target_name not in fitting_config_inverted:
                fitting_config_inverted[target_name] = {}
            fitting_config_inverted[target_name][feature_name] = func_name

    save_data = {
        'timestamp': datetime.now().isoformat(),
        'model_name': model_name,
        'feature_csv_path': os.path.abspath(feature_filepath),
        'target_csv_path': os.path.abspath(target_filepath),
        'fitting_method': fitting_method,
        'fitting_config': fitting_config_inverted,
        'functions': functions,
    }

    timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
    base_filename = f"LAW_MODEL_{timestamp_str}"
    json_filename = f"{base_filename}.json"
    json_filepath = os.path.join(current_app.config['JSON_FOLDER'], json_filename)

    try:
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)

        try:
            _train_and_save_surrogate_model(save_data, base_filename)
            message = f'Model config and surrogate model saved successfully: {json_filename}'
            return jsonify({'message': message, 'filepath': json_filepath}), 200
        except Exception as e:
            message = f'Model config saved as {json_filename}, but failed to train surrogate model: {str(e)}'
            return jsonify({'error': message}), 500

    except Exception as e:
        return jsonify({'error': f'Failed to save model configuration: {str(e)}'}), 500


def _train_and_save_surrogate_model(model_config, base_filename, resolution=10):
    feature_filepath = session.get('feature_filepath')
    target_filepath = session.get('target_filepath')
    
    df_merged = load_and_merge_csvs(feature_filepath, target_filepath)
    
    feature_headers = session.get('feature_headers', [])
    target_headers = session.get('target_headers', [])
    
    feature_vars = [h for h in feature_headers if h.lower() != 'main_id']
    target_vars = [h for h in target_headers if h.lower() != 'main_id']

    coords = {}
    for var in feature_vars:
        min_val, max_val = df_merged[var].min(), df_merged[var].max()
        if pd.isna(min_val) or pd.isna(max_val):
            raise ValueError(f"Feature '{var}' contains NaN values or is empty.")
        if min_val == max_val:
            coords[var] = np.array([min_val])
        else:
            coords[var] = np.linspace(min_val, max_val, resolution)
    
    grid_points = list(itertools.product(*coords.values()))
    
    all_results = []
    for i, point in enumerate(grid_points):
        feature_values_for_calc = dict(zip(feature_vars, point))
        
        for key, value in feature_values_for_calc.items():
            try:
                feature_values_for_calc[key] = float(value)
            except (ValueError, TypeError):
                pass
        
        calculated_targets = calculate_targets(model_config, feature_values_for_calc)
        
        result_row = {**feature_values_for_calc, **calculated_targets}
        all_results.append(result_row)

    results_df = pd.DataFrame(all_results)

    models_folder = current_app.config['MODELS_FOLDER']
    model_save_path = os.path.join(models_folder, f"{base_filename}.keras")
    scaler_save_path = os.path.join(models_folder, f"{base_filename}_scaler.joblib")

    surrogate_model.train_and_save_model(
        df=results_df,
        feature_vars=feature_vars,
        target_vars=target_vars,
        model_path=model_save_path,
        scaler_path=scaler_save_path
    )


@model_bp.route('/load_model_config', methods=['POST'])
def load_model_config():
    def parse_params(params_str):
        params = {}
        if not params_str:
            return params
        for part in params_str.split(','):
            if '=' in part:
                key_value = part.split('=', 1)
                params[key_value[0].strip()] = key_value[1].strip()
        return params

    data = request.get_json()
    json_filename = data.get('filename')

    if not json_filename:
        return jsonify({'error': 'No JSON file name provided.'}), 400

    json_filepath = os.path.join(current_app.config['JSON_FOLDER'], json_filename)

    if not os.path.exists(json_filepath):
        return jsonify({'error': f'JSON file not found: {json_filepath}'}), 404
    
    current_feature_filepath = session.get('feature_filepath')
    current_target_filepath = session.get('target_filepath')

    if not current_feature_filepath or not current_target_filepath:
        return jsonify({'error': 'Feature or Target CSV files are not currently loaded. Please load them first.'}), 400

    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        session['loaded_model_config'] = loaded_data

        loaded_feature_csv_path = loaded_data.get('feature_csv_path')
        loaded_target_csv_path = loaded_data.get('target_csv_path')

        if not (os.path.normpath(loaded_feature_csv_path) == os.path.normpath(current_feature_filepath) and \
                os.path.normpath(loaded_target_csv_path) == os.path.normpath(current_target_filepath)):
            return jsonify({'error': 'The configuration file was saved with different CSV files. Please load the matching CSVs first.'}), 400
        
        base_filename, _ = os.path.splitext(json_filename)
        models_folder = current_app.config['MODELS_FOLDER']
        model_path = os.path.join(models_folder, f"{base_filename}.keras")
        scaler_path = os.path.join(models_folder, f"{base_filename}_scaler.joblib")

        plot_state = current_app.plot_state
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                model, scaler = surrogate_model.load_model_and_scaler(model_path, scaler_path)
                plot_state.set_value('loaded_model', model)
                plot_state.set_value('loaded_scaler', scaler)
            except Exception as e:
                plot_state.set_value('loaded_model', None)
                plot_state.set_value('loaded_scaler', None)
        else:
            plot_state.set_value('loaded_model', None)
            plot_state.set_value('loaded_scaler', None)
        
        plot_state.set_value('overlap_contour_data', None)

        fitting_config_from_file = loaded_data.get('fitting_config', {})
        fitting_config_for_frontend = {}

        feature_headers_session = session.get('feature_headers', [])
        target_headers_session = session.get('target_headers', [])

        for f_header in feature_headers_session:
            if f_header.lower() == 'main_id': continue
            fitting_config_for_frontend[f_header] = {}
            for t_header in target_headers_session:
                if t_header.lower() == 'main_id': continue
                if t_header in fitting_config_from_file and f_header in fitting_config_from_file[t_header]:
                    fitting_config_for_frontend[f_header][t_header] = fitting_config_from_file[t_header][f_header]
                else:
                    fitting_config_for_frontend[f_header][t_header] = ""

        return jsonify({
            'message': 'Configuration loaded successfully.',
            'model_name': loaded_data.get('model_name', ''),
            'fitting_config': fitting_config_for_frontend,
            'fitting_method': loaded_data.get('fitting_method'),
            'functions': loaded_data.get('functions')
        }), 200

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format in the selected file.'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to load model configuration: {str(e)}'}), 500

@model_bp.route('/run_calculation_demo', methods=['POST'])
def run_calculation_demo():
    if 'loaded_model_config' not in session:
        return jsonify({'error': 'Model configuration not loaded in session.'}), 400

    loaded_data = session['loaded_model_config']

    try:
        plot_params = current_app.plot_state.get_params()

        if not plot_params.get('x_points') or not plot_params.get('y_points'):
            return jsonify({'error': 'Plot parameters (interpolation points) are not set yet. Please apply settings in the VIEW tab first.'}), 400

        x_col = plot_params['x_col']
        y_col = plot_params['y_col']
        z_col = plot_params['z_col']
        x_points = plot_params['x_points']
        y_points = plot_params['y_points']
        constant_params = plot_params.get('constant_params', {})
        
        calculation_grid_results = []

        for y_val in y_points:
            for x_val in x_points:
                feature_values_for_calc = {}
                feature_values_for_calc.update(constant_params)
                feature_values_for_calc[x_col] = x_val
                feature_values_for_calc[y_col] = y_val

                for key, value in feature_values_for_calc.items():
                    try:
                        feature_values_for_calc[key] = float(value)
                    except (ValueError, TypeError):
                        pass
                
                calculated_targets = calculate_targets(loaded_data, feature_values_for_calc)
                result_row = {**feature_values_for_calc, **calculated_targets}
                calculation_grid_results.append(result_row)
        
        current_app.plot_state.update_grid_results(calculation_grid_results)

        return jsonify({
            'message': f'Grid calculation completed successfully. {len(calculation_grid_results)} points calculated and stored in memory.',
            'num_points': len(calculation_grid_results)
        }), 200

    except Exception as e:
        return jsonify({'error': f'An error occurred during the calculation demo: {str(e)}'}), 500
