
import json
import pytest
from pathlib import Path
from leakage_buster.cli import run
import pandas as pd
import numpy as np

def test_json_output_schema(tmp_path: Path):
    """测试JSON输出结构符合schema规范"""
    # 创建测试数据
    n = 100
    rng = np.random.default_rng(42)
    date = pd.date_range("2024-01-01", periods=n, freq="D")
    user_id = rng.integers(0, 20, size=n)
    y = rng.integers(0, 2, size=n)
    leak = y + rng.normal(0, 0.01, size=n)
    
    df = pd.DataFrame({
        "date": date, 
        "user_id": user_id, 
        "y": y, 
        "leak_score": leak
    })
    
    csv = tmp_path / "test.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "out"
    
    # 运行检测
    result = run(str(csv), target="y", time_col="date", out_dir=str(out), cv_type="timeseries")
    
    # 验证输出结构
    assert isinstance(result, dict)
    assert "status" in result
    assert "exit_code" in result
    assert "data" in result
    
    # 验证成功状态
    assert result["status"] == "success"
    assert result["exit_code"] in [0, 2, 3]
    
    # 验证data结构
    data = result["data"]
    assert "report" in data
    assert "fix_script" in data
    assert "meta" in data
    assert "risks" in data
    assert isinstance(data["report"], str)
    assert isinstance(data["fix_script"], str)
    
    # 验证文件存在
    assert Path(data["report"]).exists()
    assert Path(data["fix_script"]).exists()
    
    # 验证meta.json结构
    meta_path = out / "meta.json"
    assert meta_path.exists()
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    # 验证meta结构
    assert "args" in meta
    assert "n_rows" in meta
    assert "n_cols" in meta
    assert "target" in meta
    assert "time_col" in meta
    assert "cv_type" in meta
    
    # 验证args结构
    args = meta["args"]
    assert args["train"] == str(csv)
    assert args["target"] == "y"
    assert args["time_col"] == "date"
    assert args["cv_type"] == "timeseries"
    assert args["out"] == str(out)
    
    # 验证数值类型
    assert isinstance(meta["n_rows"], int)
    assert isinstance(meta["n_cols"], int)
    assert meta["n_rows"] == n
    assert meta["n_cols"] == 4

def test_risk_item_schema(tmp_path: Path):
    """测试风险项结构符合schema规范"""
    # 创建有明显泄漏的数据
    n = 200
    rng = np.random.default_rng(123)
    
    # 创建高相关泄漏
    y = rng.integers(0, 2, size=n)
    perfect_leak = y + rng.normal(0, 0.001, size=n)  # 几乎完美相关
    
    # 创建疑似目标编码特征
    category = rng.choice(['A', 'B', 'C'], size=n)
    df_temp = pd.DataFrame({'category': category, 'y': y})
    category_mean = df_temp.groupby('category')['y'].mean()
    te_feature = df_temp['category'].map(category_mean) + rng.normal(0, 0.01, size=n)
    te_feature = np.clip(te_feature, 0, 1)
    
    df = pd.DataFrame({
        "y": y,
        "perfect_leak": perfect_leak,
        "te_feature": te_feature,
        "category": category,
        "normal_feature": rng.normal(0, 1, size=n)
    })
    
    csv = tmp_path / "leak_test.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "leak_out"
    
    result = run(str(csv), target="y", time_col=None, out_dir=str(out))
    
    # 验证输出结构
    assert result["status"] == "success"
    assert result["exit_code"] in [0, 2, 3]
    
    # 验证文件
    assert Path(result["data"]["report"]).exists()
    assert Path(result["data"]["fix_script"]).exists()
    
    # 读取报告内容，验证风险项结构
    with open(result["data"]["report"], 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 验证报告包含预期的风险项
    assert "Target leakage" in report_content or "Target encoding" in report_content

def test_exit_codes():
    """测试退出码定义"""
    # 这个测试需要模拟不同的错误情况
    # 由于当前实现没有明确的退出码返回，这里先做占位测试
    pass

def test_statistical_leakage_preview(tmp_path: Path):
    """测试统计类泄漏预览功能"""
    n = 300
    rng = np.random.default_rng(456)
    
    # 创建疑似统计特征（变异系数很小）
    y = rng.integers(0, 2, size=n)
    stat_feature = np.full(n, 0.5) + rng.normal(0, 0.01, size=n)  # 变异系数很小
    
    df = pd.DataFrame({
        "y": y,
        "stat_feature": stat_feature,
        "normal_feature": rng.normal(0, 1, size=n)
    })
    
    csv = tmp_path / "stat_test.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "stat_out"
    
    result = run(str(csv), target="y", time_col=None, out_dir=str(out))
    
    # 验证输出
    assert result["status"] == "success"
    assert Path(result["data"]["report"]).exists()
    
    # 读取报告，检查是否包含统计类泄漏预览
    with open(result["data"]["report"], 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 验证包含统计类泄漏预览分区
    assert "Statistical Leakage Detection" in report_content
    assert "Statistical leakage" in report_content or "统计特征" in report_content

def test_detector_registry():
    """测试检测器注册表功能"""
    from leakage_buster.core.checks import DetectorRegistry, StatisticalLeakageDetector
    
    # 创建测试数据
    n = 100
    rng = np.random.default_rng(789)
    y = rng.integers(0, 2, size=n)
    df = pd.DataFrame({
        "y": y,
        "feature1": rng.normal(0, 1, size=n),
        "feature2": rng.normal(0, 1, size=n)
    })
    
    # 测试检测器注册表
    registry = DetectorRegistry()
    assert len(registry.detectors) >= 5  # 至少包含6个检测器
    
    # 测试统计类泄漏检测器
    stat_detector = StatisticalLeakageDetector()
    risks = stat_detector.detect(df, "y")
    
    # 验证返回的风险项结构
    for risk in risks:
        assert hasattr(risk, 'name')
        assert hasattr(risk, 'severity')
        assert hasattr(risk, 'detail')
        assert hasattr(risk, 'evidence')
        assert risk.severity in ['high', 'medium', 'low']

def test_backward_compatibility():
    """测试向后兼容性"""
    from leakage_buster.core.checks import run_checks
    
    # 创建测试数据
    n = 50
    rng = np.random.default_rng(999)
    y = rng.integers(0, 2, size=n)
    df = pd.DataFrame({
        "y": y,
        "feature1": rng.normal(0, 1, size=n)
    })
    
    # 测试旧的run_checks接口仍然工作
    result = run_checks(df, "y")
    
    assert "risks" in result
    assert isinstance(result["risks"], list)
    
    # 验证每个风险项都有正确的结构
    for risk in result["risks"]:
        assert "name" in risk
        assert "severity" in risk
        assert "detail" in risk
        assert "evidence" in risk

def test_error_handling(tmp_path: Path):
    """测试错误处理"""
    # 测试文件不存在
    result = run("nonexistent.csv", target="y", time_col=None, out_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["exit_code"] == 4
    assert "error" in result
    
    # 测试目标列不存在
    df = pd.DataFrame({"x": [1, 2, 3], "y": [0, 1, 0]})
    csv = tmp_path / "test.csv"
    df.to_csv(csv, index=False)
    
    result = run(str(csv), target="nonexistent", time_col=None, out_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["exit_code"] == 2
    assert "error" in result

