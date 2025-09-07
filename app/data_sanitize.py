from __future__ import annotations
from datetime import date, datetime
import json
import numpy as np
import pandas as pd
import uuid

_JSON_SCALARS = (int, float, bool, str, type(None))

def _clean_scalar(v):
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)

    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime().isoformat()
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()

    if isinstance(v, uuid.UUID):
        return str(v)

    if isinstance(v, _JSON_SCALARS):
        return v

    try:
        return str(v)
    except Exception:
        return None

def clean_jsonable(obj):
    if isinstance(obj, pd.DataFrame):
        return [clean_jsonable(r) for r in obj.to_dict(orient="records")]
    if isinstance(obj, pd.Series):
        return {k: _clean_scalar(v) for k, v in obj.to_dict().items()}
    if isinstance(obj, dict):
        return {str(k): clean_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_jsonable(v) for v in obj]
    return _clean_scalar(obj)

def assert_jsonable(obj):
    try:
        json.dumps(obj, ensure_ascii=False, allow_nan=False)
    except Exception as e:
        raise RuntimeError(f"Payload not JSON-serializable: {e}\nFirst part: {str(obj)[:500]}")
