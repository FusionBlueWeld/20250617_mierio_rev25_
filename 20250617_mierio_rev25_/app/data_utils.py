import pandas as pd
import numpy as np
import os
from flask import current_app

def load_and_merge_csvs(feature_filepath, target_filepath):
    if not os.path.exists(feature_filepath):
        raise FileNotFoundError(f"Feature CSV file not found: {feature_filepath}")
    if not os.path.exists(target_filepath):
        raise FileNotFoundError(f"Target CSV file not found: {target_filepath}")

    df_feature = pd.read_csv(feature_filepath)
    df_target = pd.read_csv(target_filepath)

    if 'main_id' in df_feature.columns and 'main_id' in df_target.columns:
        df_merged = pd.merge(df_feature, df_target, on='main_id', how='inner')
    else:
        if len(df_feature) != len(df_target):
            raise ValueError('Feature and Target CSV files have different number of rows and no common "main_id".')
        df_merged = pd.concat([df_feature, df_target], axis=1)
    
    return df_merged

def filter_dataframe(df, feature_params):
    df_filtered = df.copy()
    for param_info in feature_params:
        param_name = param_info['name']
        param_type = param_info['type']
        param_value = param_info.get('value')

        if param_type == 'Constant':
            if param_value is None or str(param_value).strip() == '':
                continue

            if param_name not in df_filtered.columns:
                raise KeyError(f"Parameter '{param_name}' not found in data for Constant filter.")

            if pd.api.types.is_numeric_dtype(df_filtered[param_name]):
                try:
                    numeric_value = float(param_value)
                    tolerance = 1e-9
                    df_filtered = df_filtered[np.isclose(df_filtered[param_name], numeric_value, atol=tolerance)]
                except (ValueError, TypeError):
                    return pd.DataFrame(columns=df.columns)
            else:
                df_filtered = df_filtered[df_filtered[param_name].astype(str) == str(param_value)]
                
    return df_filtered

def convert_columns_to_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def get_variable_ranges(df, variables):
    ranges = {}
    for var in variables:
        if var not in df.columns:
            raise KeyError(f"Variable '{var}' not found in DataFrame.")
        
        numeric_series = pd.to_numeric(df[var], errors='coerce')
        
        min_val = numeric_series.min()
        max_val = numeric_series.max()
        
        if pd.isna(min_val) or pd.isna(max_val):
            raise ValueError(f"Variable '{var}' contains no valid numeric data to determine a range.")
            
        ranges[var] = {'min': min_val, 'max': max_val}
        
    return ranges
