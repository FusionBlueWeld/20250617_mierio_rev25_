import os
from flask import Blueprint, request, jsonify, session, current_app
import pandas as pd
import numpy as np
from app import plot_utils
from app.data_utils import load_and_merge_csvs, filter_dataframe, convert_columns_to_numeric
from werkzeug.utils import secure_filename
# ▼▼▼ここから修正▼▼▼
from app import surrogate_model
# ▲▲▲ここまで修正▲▲▲

data_bp = Blueprint('data_bp', __name__)

@data_bp.route('/upload_asset_folder', methods=['POST'])
def upload_asset_folder():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No file part in the request.'}), 400

        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': 'No files selected for uploading.'}), 400

        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        session.pop('feature_filepath', None)
        session.pop('feature_headers', None)
        session.pop('target_filepath', None)
        session.pop('target_headers', None)

        saved_files = {}
        feature_file, target_file = None, None

        for file in files:
            if file.filename and '/' not in file.filename and '\\' not in file.filename:
                if file.filename.lower() == 'feature.csv':
                    feature_file = file
                elif file.filename.lower() == 'target.csv':
                    target_file = file
        
        if not feature_file or not target_file:
            return jsonify({'error': '選択したフォルダの直下に Feature.csv と Target.csv が見つかりません。'}), 400

        try:
            filename = secure_filename(feature_file.filename)
            filepath = os.path.join(upload_folder, filename)
            feature_file.save(filepath)
            df = pd.read_csv(filepath)
            df.columns = df.columns.str.strip()
            headers = [h for h in df.columns.tolist() if h.lower() != 'main_id']
            session['feature_filepath'] = filepath
            session['feature_headers'] = headers
            saved_files['feature'] = {'headers': headers}
        except Exception as e:
            current_app.logger.error(f"Failed to process Feature.csv: {e}")
            return jsonify({'error': f'Feature.csvの読み込みまたは処理に失敗しました: {str(e)}'}), 500

        try:
            filename = secure_filename(target_file.filename)
            filepath = os.path.join(upload_folder, filename)
            target_file.save(filepath)
            df = pd.read_csv(filepath)
            df.columns = df.columns.str.strip()
            headers = [h for h in df.columns.tolist() if h.lower() != 'main_id']
            session['target_filepath'] = filepath
            session['target_headers'] = headers
            saved_files['target'] = {'headers': headers}
        except Exception as e:
            current_app.logger.error(f"Failed to process Target.csv: {e}")
            return jsonify({'error': f'Target.csvの読み込みまたは処理に失敗しました: {str(e)}'}), 500
        
        return jsonify({
            'message': 'Asset folder processed successfully.',
            'headers': {
                'feature': saved_files['feature']['headers'],
                'target': saved_files['target']['headers']
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred in upload_asset_folder: {e}", exc_info=True)
        return jsonify({'error': f'サーバーで予期せぬエラーが発生しました: {str(e)}'}), 500


@data_bp.route('/upload_csv', methods=['POST'])
def upload_csv():
    file_type = request.form.get('file_type')
    if not file_type:
        return jsonify({'error': 'Invalid file type specified.'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(filepath)
                df.columns = df.columns.str.strip()
                
                headers = df.columns.tolist()
                filtered_headers = [h for h in headers if h.lower() != 'main_id']

                session[f'{file_type}_filepath'] = filepath
                session[f'{file_type}_headers'] = filtered_headers
                
                return jsonify({
                    'filename': filename,
                    'headers': filtered_headers,
                    'filepath': filepath,
                    'file_type': file_type
                }), 200
            except Exception as e:
                session.pop(f'{file_type}_filepath', None)
                session.pop(f'{file_type}_headers', None)
                return jsonify({'error': f'Failed to read CSV or extract headers: {str(e)}'}), 500
        
        else:
            session[f'{file_type}_filepath'] = filepath
            return jsonify({
                'filename': filename,
                'filepath': filepath,
                'file_type': file_type
            }), 200

    return jsonify({'error': 'Invalid file type or processing error'}), 400


@data_bp.route('/get_plot_data', methods=['POST'])
def get_plot_data():
    data = request.get_json()
    feature_params = data.get('featureParams', [])
    target_param = data.get('targetParam')

    feature_filepath = session.get('feature_filepath')
    target_filepath = session.get('target_filepath')

    if not feature_filepath or not target_filepath:
        return jsonify({'error': 'Asset folder not uploaded yet.'}), 400

    try:
        df_merged = load_and_merge_csvs(feature_filepath, target_filepath)
        df_merged.columns = df_merged.columns.str.strip()

        feature_headers = session.get('feature_headers', [])
        target_headers = session.get('target_headers', [])
        all_vars = list(set(feature_headers + target_headers))
        df_merged = convert_columns_to_numeric(df_merged, all_vars)
        
        current_app.plot_state.set_value('df_merged', df_merged)

        df_filtered = filter_dataframe(df_merged, feature_params)
        
        x_col = next((p['name'] for p in feature_params if p['type'] == 'X_axis'), None)
        y_col = next((p['name'] for p in feature_params if p['type'] == 'Y_axis'), None)
        z_col = target_param

        if not x_col or not y_col or not z_col:
            current_app.plot_state.set_value('overlap_contour_data', None)
            return jsonify({'error': 'Please select X-axis, Y-axis, and Target parameter.'}), 400
        
        if df_filtered.empty:
            return jsonify({'error': 'No data matches the selected constant filters.'}), 400

        df_final = df_filtered.dropna(subset=[x_col, y_col, z_col])
        current_app.plot_state.set_value('df_filtered', df_final)

        if df_final.empty:
            return jsonify({'error': 'No valid numerical data after filtering and type conversion.'}), 400

        graph_json, layout_json = plot_utils.generate_scatter_plot(df_final, x_col, y_col, z_col)
        
        plot_state = current_app.plot_state
        if plot_state.get_value('loaded_model') is not None:
            try:
                model = plot_state.get_value('loaded_model')
                scaler = plot_state.get_value('loaded_scaler')
                constants = {p['name']: float(p['value']) for p in feature_params if p['type'] == 'Constant'}

                grid_results = plot_utils.calculate_overlap_grid(
                    model=model,
                    scaler=scaler,
                    x_col=x_col,
                    y_col=y_col,
                    z_col=z_col,
                    constants=constants,
                    resolution=10
                )
                
                if grid_results:
                    standardized_grid = {
                        'X': grid_results['x_grid'],
                        'Y': grid_results['y_grid'],
                        'Z': grid_results['z_grid']
                    }
                    plot_state.set_value('overlap_contour_data', standardized_grid)
                else:
                    plot_state.set_value('overlap_contour_data', None)

            except Exception as e:
                current_app.logger.error(f"Failed to calculate overlap data: {e}", exc_info=True)
                plot_state.set_value('overlap_contour_data', None)
        else:
            plot_state.set_value('overlap_contour_data', None)

        return jsonify({'graph_json': graph_json, 'layout_json': layout_json}), 200

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        return jsonify({'error': f'Missing column in CSV: {str(e)}. Please check your CSV headers.'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error in get_plot_data: {e}", exc_info=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


# ▼▼▼ここから修正▼▼▼
@data_bp.route('/finetune_grid', methods=['POST'])
def finetune_grid():
    """
    既存のモデルを、現在表示されているプロットデータで追加学習（ファインチューニング）し、
    新しいモデルとして保存する。
    """
    try:
        # 1. フロントエンドからベースとなるモデルのファイル名を取得
        data = request.get_json()
        base_model_json_filename = data.get('baseModelFilename')
        if not base_model_json_filename:
            return jsonify({'error': 'ベースとなるモデルが指定されていません。'}), 400

        # 2. ファインチューニング用のデータをサーバーの状態から取得
        plot_state = current_app.plot_state
        plot_df = plot_state.get_value('df_filtered')
        if plot_df is None or plot_df.empty:
            return jsonify({'error': 'ファインチューニングに使用するデータが見つかりません。'}), 400

        # 3. 特徴量とターゲットの情報をセッションから取得
        feature_vars = session.get('feature_headers')
        target_vars = session.get('target_headers')
        if not feature_vars or not target_vars:
            return jsonify({'error': '特徴量またはターゲットの情報がセッションに見つかりません。'}), 400

        # 4. 必要なファイルパスを構築
        base_name, _ = os.path.splitext(base_model_json_filename)
        
        # オリジナルのモデルとスケーラーのパス
        original_model_path = os.path.join(current_app.config['MODELS_FOLDER'], f"{base_name}.keras")
        original_scaler_path = os.path.join(current_app.config['MODELS_FOLDER'], f"{base_name}_scaler.joblib")
        
        # ファインチューニング済みモデルの新しい保存先パス
        tuned_model_path = os.path.join(current_app.config['TUNED_MODELS_FOLDER'], f"{base_name}.keras")

        # 5. オリジナルモデルの存在確認
        if not os.path.exists(original_model_path) or not os.path.exists(original_scaler_path):
            return jsonify({'error': f'ベースモデル({base_name}.keras)またはスケーラーが見つかりません。'}), 404
        
        # 6. モデルの再学習（ファインチューニング）を実行
        surrogate_model.train_and_save_model(
            df=plot_df,
            feature_vars=feature_vars,
            target_vars=target_vars,
            model_path=tuned_model_path,       # 新しいモデルの保存先
            scaler_path=original_scaler_path,  # オリジナルのスケーラーを読み込む
            base_model_path=original_model_path # ベースとして使うオリジナルモデル
        )

        # 7. 成功メッセージを返す
        return jsonify({
            'message': f'モデルのファインチューニングが完了しました。',
            'new_model_name': f'{base_name}.keras',
            'saved_location': 'tuned_models folder'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in finetune_grid: {e}", exc_info=True)
        return jsonify({'error': f'ファインチューニング中に予期せぬエラーが発生しました: {str(e)}'}), 500
# ▲▲▲ここまで修正▲▲▲


@data_bp.route('/get_model_table_headers', methods=['GET'])
def get_model_table_headers():
    feature_headers = session.get('feature_headers', [])
    target_headers = session.get('target_headers', [])
    filtered_feature_headers = [h for h in feature_headers if h.lower() != 'main_id']
    filtered_target_headers = [h for h in target_headers if h.lower() != 'main_id']
    if not filtered_feature_headers or not filtered_target_headers:
        return jsonify({'error': 'Feature or Target CSV headers not available. Please upload files.'}), 400
    return jsonify({
        'feature_headers': filtered_feature_headers,
        'target_headers': filtered_target_headers
    }), 200

@data_bp.route('/get_calculated_contour', methods=['POST'])
def get_calculated_contour():
    data = request.get_json()
    json_filename = data.get('json_filename')
    feature_params = data.get('featureParams', [])
    target_param = data.get('targetParam')

    if not json_filename:
        return jsonify({'error': 'No model file specified.'}), 400
    if not feature_params or not target_param:
        return jsonify({'error': 'Axis or Target parameters not provided.'}), 400

    try:
        base_filename, _ = os.path.splitext(json_filename)
        model_path = os.path.join(current_app.config['MODELS_FOLDER'], f"{base_filename}.keras")
        scaler_path = os.path.join(current_app.config['MODELS_FOLDER'], f"{base_filename}_scaler.joblib")

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return jsonify({'error': f'Model (.keras) or scaler (.joblib) file not found for {base_filename}.'}), 404

        x_col = next((p['name'] for p in feature_params if p['type'] == 'X_axis'), None)
        y_col = next((p['name'] for p in feature_params if p['type'] == 'Y_axis'), None)
        z_col = target_param
        constants = {p['name']: float(p['value']) for p in feature_params if p['type'] == 'Constant'}

        if not x_col or not y_col:
            return jsonify({'error': 'X-axis or Y-axis not defined.'}), 400

        grid_results = plot_utils.generate_grid_with_surrogate(
            model_path=model_path,
            scaler_path=scaler_path,
            x_col=x_col,
            y_col=y_col,
            z_col=z_col,
            constants=constants,
            resolution=50
        )

        if not grid_results:
            return jsonify({'error': 'Failed to generate grid data with surrogate model.'}), 500

        contour_json = plot_utils.generate_contour_plot(grid_results, x_col, y_col, z_col)
        
        if not contour_json:
            return jsonify({'error': 'Failed to generate contour plot data from the grid.'}), 500
            
        return jsonify({'contour_json': contour_json}), 200

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except KeyError as e:
        return jsonify({'error': f'Column not found during data processing: {str(e)}. The model may be incompatible.'}), 400
    except Exception as e:
        current_app.logger.error(f"Error in get_calculated_contour: {e}", exc_info=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@data_bp.route('/get_overlap_data', methods=['GET'])
def get_overlap_data():
    plot_state = current_app.plot_state
    overlap_data = plot_state.get_value('overlap_contour_data')

    if overlap_data is None:
        return jsonify({'data': None, 'message': 'Overlap data not yet calculated.'})

    try:
        x_data = overlap_data['X']
        y_data = overlap_data['Y']
        z_data = overlap_data['Z']

        json_safe_data = {
            'X': x_data.tolist() if isinstance(x_data, np.ndarray) else x_data,
            'Y': y_data.tolist() if isinstance(y_data, np.ndarray) else y_data,
            'Z': z_data.tolist() if isinstance(z_data, np.ndarray) else z_data,
        }
        return jsonify({'data': json_safe_data})

    except Exception as e:
        current_app.logger.error(f"Error processing overlap data for jsonify: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process stored overlap data.'}), 500
