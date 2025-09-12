
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

def test_target_encoding_leakage(tmp_path: Path):
    """测试目标编码泄漏检测"""
    n = 300
    rng = np.random.default_rng(123)
    
    # 创建带有目标编码泄漏的数据
    date = pd.date_range("2024-01-01", periods=n, freq="H")
    user_id = rng.integers(0, 50, size=n)
    category = rng.choice(['A', 'B', 'C', 'D'], size=n)
    y = rng.integers(0, 2, size=n)
    
    # 创建疑似目标编码特征（与目标高相关，值域在[0,1]）
    df_temp = pd.DataFrame({'category': category, 'y': y})
    category_mean = df_temp.groupby('category')['y'].mean()
    te_feature = df_temp['category'].map(category_mean) + rng.normal(0, 0.05, size=n)
    te_feature = np.clip(te_feature, 0, 1)  # 限制在[0,1]范围内
    
    # 创建疑似全量统计特征（变异系数很小）
    global_mean = np.mean(y)
    window_feature = np.full(n, global_mean) + rng.normal(0, 0.02, size=n)
    
    df = pd.DataFrame({
        "date": date,
        "user_id": user_id, 
        "category": category,
        "y": y,
        "te_suspicious": te_feature,  # 疑似目标编码
        "window_suspicious": window_feature,  # 疑似全量统计
        "normal_feature": rng.normal(0, 1, size=n)
    })
    
    csv = tmp_path / "te_train.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "te_out"
    
    res = run(str(csv), target="y", time_col="date", out_dir=str(out), cv_type="timeseries")
    
    # 检查文件是否生成
    assert (out / "report.html").exists()
    assert (out / "fix_transforms.py").exists()
    
    # 读取生成的修复脚本，检查是否包含相关建议
    fix_content = (out / "fix_transforms.py").read_text(encoding="utf-8")
    assert "te_suspicious" in fix_content or "目标编码" in fix_content
    assert "window_suspicious" in fix_content or "全量统计" in fix_content

def test_cv_strategy_mismatch(tmp_path: Path):
    """测试CV策略不匹配检测"""
    n = 200
    rng = np.random.default_rng(456)
    
    # 创建有明显时间结构的数据
    date = pd.date_range("2024-01-01", periods=n, freq="D")
    # 创建时间相关的目标（早期更多0，后期更多1）
    time_trend = np.linspace(0, 1, n)
    y = rng.binomial(1, time_trend)
    
    user_id = rng.integers(0, 10, size=n)  # 高重复，适合GroupKFold
    feature1 = rng.normal(0, 1, size=n)
    
    df = pd.DataFrame({
        "date": date,
        "user_id": user_id,
        "y": y,
        "feature1": feature1
    })
    
    csv = tmp_path / "cv_train.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "cv_out"
    
    # 故意使用不匹配的CV策略（时间数据用KFold）
    res = run(str(csv), target="y", time_col="date", out_dir=str(out), cv_type="kfold")
    
    # 检查文件是否生成
    assert (out / "report.html").exists()
    assert (out / "fix_transforms.py").exists()
    
    # 读取报告，应该检测到CV策略不匹配
    report_content = (out / "report.html").read_text(encoding="utf-8")
    assert "CV strategy" in report_content or "策略" in report_content

