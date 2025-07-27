import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-for-dev'

    UPLOAD_FOLDER = os.path.join(basedir, 'user_data', 'uploads')
    JSON_FOLDER = os.path.join(basedir, 'user_data', 'settings', 'json')
    MODELS_FOLDER = os.path.join(basedir, 'user_data', 'settings', 'models')
    # ▼▼▼ここから追加▼▼▼
    TUNED_MODELS_FOLDER = os.path.join(basedir, 'user_data', 'settings', 'tuned_models')
    # ▲▲▲ここまで追加▲▲▲

    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)
        os.makedirs(app.config['MODELS_FOLDER'], exist_ok=True)
        # ▼▼▼ここから追加▼▼▼
        os.makedirs(app.config['TUNED_MODELS_FOLDER'], exist_ok=True)
        # ▲▲▲ここまで追加▲▲▲
