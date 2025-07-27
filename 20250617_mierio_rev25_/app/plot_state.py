import threading
import pandas as pd

class PlotState:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.df_merged: pd.DataFrame = None
            self.loaded_model_config: dict = None
            self.transient_data: dict = {}
            
            self.loaded_model = None
            self.loaded_scaler = None
            self.overlap_contour_data: dict = None

    def set_value(self, key: str, value):
        with self._lock:
            setattr(self, key, value)

    def get_value(self, key: str, default=None):
        with self._lock:
            return getattr(self, key, default)
