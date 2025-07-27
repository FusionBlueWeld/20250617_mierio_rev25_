import os
import json
from flask import current_app

class ModelManager:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def get_model_list(self):
        try:
            files = [f for f in os.listdir(self.model_dir) if f.endswith('.json') and os.path.isfile(os.path.join(self.model_dir, f))]
            return sorted(files, reverse=True)
        except FileNotFoundError:
            current_app.logger.error(f"Model directory not found: {self.model_dir}")
            return []

    def load_model_config(self, filename):
        filepath = os.path.join(self.model_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            current_app.logger.error(f"Failed to load model config {filename}: {e}")
            return None
