import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import joblib
from functools import lru_cache
import os

def _create_model(input_dim, output_dim):
    """
    新しいKerasモデルを定義して返す。
    """
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=(input_dim,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(output_dim)
    ])
    return model

def train_and_save_model(df, feature_vars, target_vars, model_path, scaler_path, base_model_path=None, epochs=50, batch_size=32):
    """
    モデルの新規学習またはファインチューニングを行い、保存する。

    Args:
        df (pd.DataFrame): 学習に使用するデータ。
        feature_vars (list): 特徴量の列名リスト。
        target_vars (list): ターゲットの列名リスト。
        model_path (str): 学習済みモデルの保存先パス (.keras)。
        scaler_path (str): スケーラーの保存先パス (.joblib)。
        base_model_path (str, optional): ファインチューニングのベースとなる既存モデルのパス。
                                         Noneの場合は新規学習を行う。デフォルトはNone。
        epochs (int, optional): 学習のエポック数。
        batch_size (int, optional): 学習のバッチサイズ。
    """
    X = df[feature_vars]
    y = df[target_vars]

    if base_model_path and os.path.exists(base_model_path):
        # --- ファインチューニング（追加学習）の場合 ---
        print(f"Loading base model from {base_model_path} for fine-tuning...")
        
        # 既存のモデルとスケーラーをロード
        model, scaler = load_model_and_scaler(base_model_path, scaler_path)
        if model is None or scaler is None:
            raise ValueError(f"Failed to load base model or scaler from the provided paths.")
        
        # 既存のスケーラーを使って新しいデータを変換
        X_scaled = scaler.transform(X)
        
        # モデルの学習率を少し下げてファインチューニングすることが一般的
        # Adamオプティマイザの学習率を再設定
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001), loss='mean_squared_error')
        print("Continuing training on new data (fine-tuning)...")

    else:
        # --- 新規学習の場合 ---
        print("Creating and training a new model...")
        
        # 新しいスケーラーを作成し、学習データにフィットさせる
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 新しいスケーラーを保存
        joblib.dump(scaler, scaler_path)
        
        # 新しいモデルを作成
        input_dim = len(feature_vars)
        output_dim = len(target_vars)
        model = _create_model(input_dim, output_dim)
        
        model.compile(optimizer='adam', loss='mean_squared_error')
    
    # モデルのサマリーを表示
    model.summary()
    
    # モデルの学習を実行
    model.fit(
        X_scaled,
        y,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.2,
        verbose=1
    )
    
    # 学習後のモデルを指定されたパスに保存
    model.save(model_path)
    print(f"Model saved to {model_path}")


@lru_cache(maxsize=32)
def load_model_and_scaler(model_path, scaler_path):
    """
    キャッシュ機能付きでモデルとスケーラーをロードする。
    """
    try:
        print(f"Loading model from: {model_path}")
        model = tf.keras.models.load_model(model_path)
        print(f"Loading scaler from: {scaler_path}")
        scaler = joblib.load(scaler_path)
        return model, scaler
    except Exception as e:
        print(f"Error loading model or scaler: {e}")
        return None, None

def predict_with_loaded_model(model, scaler, input_df):
    """
    ロード済みのモデルとスケーラーを使って予測を行う。
    """
    input_scaled = scaler.transform(input_df)
    predictions = model.predict(input_scaled)
    return predictions
