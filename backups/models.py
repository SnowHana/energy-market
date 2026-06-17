import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import lightgbm as lgb
from backups.config import LGBM_PARAMS


def base_predict(df: pd.DataFrame) -> pd.Series:
    return df["price_lag_168"]


def train_lgbm(X_train: pd.DataFrame, y_train: pd.Series) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**LGBM_PARAMS)
    model.fit(X_train, y_train)
    return model


def predict_lgbm(model: lgb.LGBMRegressor, X: pd.DataFrame) -> pd.Series:
    preds = model.predict(X)
    return pd.Series(preds, index=X.index)
