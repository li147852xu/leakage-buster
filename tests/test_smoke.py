
from pathlib import Path
from leakage_buster.cli import run
import pandas as pd
import numpy as np

def test_smoke(tmp_path: Path):
    n = 200
    rng = np.random.default_rng(42)
    date = pd.date_range("2024-01-01", periods=n, freq="D")
    user_id = rng.integers(0, 20, size=n)
    y = rng.integers(0, 2, size=n)
    leak = y + rng.normal(0, 0.01, size=n)
    df = pd.DataFrame({"date": date, "user_id": user_id, "y": y, "leak_score": leak})
    csv = tmp_path / "train.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "out"
    res = run(str(csv), target="y", time_col="date", out_dir=str(out))
    assert (out / "report.html").exists()
    assert (out / "fix_transforms.py").exists()

