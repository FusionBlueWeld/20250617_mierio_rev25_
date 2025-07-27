from flask import Flask
from config import Config
from .plot_state import PlotState
from .model_manager import ModelManager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    app.plot_state = PlotState()
    app.model_manager = ModelManager(app.config['MODELS_FOLDER'])
    from .main import main_bp
    app.register_blueprint(main_bp)
    from .routes import data_bp
    app.register_blueprint(data_bp)
    from .model_routes import model_bp
    app.register_blueprint(model_bp, url_prefix='/model')
    return app
