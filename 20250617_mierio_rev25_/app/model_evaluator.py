import numexpr
import re
import numpy as np

def parse_params(params_str):
    params = {}
    if not params_str:
        return params
    for part in params_str.split(','):
        if '=' in part:
            key_value = part.split('=', 1)
            params[key_value[0].strip()] = key_value[1].strip()
    return params

def generate_equation_string(target_name, fitting_config, functions_map, fitting_method):
    operator = ' * ' if fitting_method == '乗積' else ' + '
    feature_map = fitting_config.get(target_name, {})
    if not feature_map:
        return None
    
    substituted_parts = []
    sorted_features = sorted(feature_map.items())

    for feature, func_name in sorted_features:
        if feature.lower() == 'main_id':
            continue
        
        func_definition = functions_map.get(func_name)
        if func_definition:
            equation = func_definition.get('equation', 'x')
            params_str = func_definition.get('parameters', '')
            params_dict = parse_params(params_str)
            
            sub_eq = f"({equation})"
            
            # パラメータを値に置換
            sorted_keys = sorted(params_dict.keys(), key=len, reverse=True)
            for param_name in sorted_keys:
                param_val = params_dict[param_name]
                sub_eq = re.sub(r'\b' + re.escape(param_name) + r'\b', str(param_val), sub_eq)
            
            # 変数 'x' を特徴量名に置換
            sub_eq = re.sub(r'\bx\b', feature, sub_eq)
            substituted_parts.append(sub_eq)
        else:
            substituted_parts.append(feature)
            
    if not substituted_parts:
        return None
        
    return operator.join(substituted_parts)

def calculate_targets(model_config, feature_values):
    fitting_config = model_config.get('fitting_config', {})
    functions_list = model_config.get('functions', [])
    fitting_method = model_config.get('fitting_method', '線形結合')
    functions_map = {func['name']: func for func in functions_list}
    
    results = {}
    local_dict = feature_values.copy()
    
    # numexprで使用可能な数学関数を追加
    local_dict.update({
        'exp': np.exp,
        'log': np.log,
        'sin': np.sin,
        'cos': np.cos,
        'tan': np.tan,
        'pi': np.pi
    })

    for target_name in fitting_config.keys():
        equation_str = generate_equation_string(target_name, fitting_config, functions_map, fitting_method)
        if equation_str:
            try:
                # numexprで数式を高速に評価
                calculated_value = numexpr.evaluate(equation_str, local_dict=local_dict, global_dict={})
                results[target_name] = calculated_value.item() if hasattr(calculated_value, 'item') else calculated_value
            except Exception as e:
                raise ValueError(f"Failed to evaluate expression for '{target_name}': {equation_str}. Error: {e}")
                
    return results
