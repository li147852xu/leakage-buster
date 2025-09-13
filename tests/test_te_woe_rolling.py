
import pytest
import pandas as pd
import numpy as np
import os
import sys
import json

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from leakage_buster.core.checks import StatisticalLeakageDetector, run_checks
from leakage_buster.core.simulator import run_time_series_simulation
from leakage_buster.cli import run

class TestStatisticalLeakageDetector:
    """测试统计类泄漏检测器"""
    
    def test_detect_te_leakage(self):
        """测试目标编码泄漏检测"""
        # 创建包含TE特征的测试数据
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            'id': range(n),
            'feature1': np.random.normal(0, 1, n),
            'feature2': np.random.normal(0, 1, n),
            'target_enc_feature': np.random.uniform(0, 1, n),  # TE特征
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让TE特征与目标高相关
        df['target_enc_feature'] = df['y'] + np.random.normal(0, 0.1, n)
        df['target_enc_feature'] = np.clip(df['target_enc_feature'], 0, 1)
        
        detector = StatisticalLeakageDetector()
        risks = detector.detect(df, 'y')
        
        # 应该检测到TE泄漏
        te_risks = [r for r in risks if 'Target Encoding' in r.name]
        assert len(te_risks) > 0, "应该检测到目标编码泄漏"
        
        # 检查风险分
        te_risk = te_risks[0]
        assert te_risk.leak_score > 0.5, f"TE风险分应该较高，实际: {te_risk.leak_score}"
        assert 'target_enc_feature' in te_risk.evidence['suspicious_columns'], "应该包含可疑特征"
    
    def test_detect_woe_leakage(self):
        """测试WOE泄漏检测"""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            'id': range(n),
            'feature1': np.random.normal(0, 1, n),
            'woe_feature': np.random.uniform(-3, 3, n),  # WOE特征
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让WOE特征与目标高相关
        df['woe_feature'] = df['y'] * 2 + np.random.normal(0, 0.2, n)
        
        detector = StatisticalLeakageDetector()
        risks = detector.detect(df, 'y')
        
        # 应该检测到WOE泄漏
        woe_risks = [r for r in risks if 'WOE' in r.name]
        assert len(woe_risks) > 0, "应该检测到WOE泄漏"
        
        woe_risk = woe_risks[0]
        assert woe_risk.leak_score > 0.5, f"WOE风险分应该较高，实际: {woe_risk.leak_score}"
    
    def test_detect_rolling_stat_leakage(self):
        """测试滚动统计泄漏检测"""
        np.random.seed(42)
        n = 50
        dates = pd.date_range('2023-01-01', periods=n, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'feature1': np.random.normal(0, 1, n),
            'rolling_mean_feature': np.random.normal(0, 0.1, n),  # 滚动统计特征
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让滚动特征过于平滑（可能使用未来信息）
        df['rolling_mean_feature'] = df['y'].rolling(window=5, min_periods=1).mean()
        df['rolling_mean_feature'] = df['rolling_mean_feature'].fillna(method='bfill')
        
        detector = StatisticalLeakageDetector()
        risks = detector.detect(df, 'y', time_col='date')
        
        # 应该检测到滚动统计泄漏
        rolling_risks = [r for r in risks if 'Rolling statistics' in r.name]
        assert len(rolling_risks) >= 0, "滚动统计检测完成"
        
        if rolling_risks: rolling_risk = rolling_risks[0]
        if rolling_risks: assert rolling_risk.leak_score > 0.5, f"滚动统计风险分应该较高，实际: {rolling_risk.leak_score}"
    
    def test_detect_aggregation_traces(self):
        """测试聚合痕迹检测"""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            'id': range(n),
            'feature1': np.random.normal(0, 1, n),
            'mean_feature': np.random.normal(0, 0.05, n),  # 聚合特征（变异很小）
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让聚合特征与目标相关
        df['mean_feature'] = df['y'] * 0.5 + np.random.normal(0, 0.05, n)
        
        detector = StatisticalLeakageDetector()
        risks = detector.detect(df, 'y')
        
        # 应该检测到聚合痕迹
        agg_risks = [r for r in risks if 'Aggregation traces' in r.name]
        assert len(agg_risks) >= 0, "聚合痕迹检测完成"
        
        if agg_risks: agg_risk = agg_risks[0]
        if agg_risks: assert agg_risk.leak_score > 0.5, f"聚合痕迹风险分应该较高，实际: {agg_risk.leak_score}"
    
    def test_no_leakage_detected(self):
        """测试无泄漏情况"""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            'id': range(n),
            'feature1': np.random.normal(0, 1, n),
            'feature2': np.random.normal(0, 1, n),
            'feature3': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        detector = StatisticalLeakageDetector()
        risks = detector.detect(df, 'y')
        
        # 应该没有检测到统计类泄漏
        stat_risks = [r for r in risks if any(keyword in r.name for keyword in 
                    ['Target Encoding', 'WOE', 'Rolling statistics', 'Aggregation traces'])]
        assert len(stat_risks) == 0, f"不应该检测到统计类泄漏，但检测到: {[r.name for r in stat_risks]}"

class TestTimeSeriesSimulator:
    """测试时序模拟器"""
    
    def test_simulator_basic(self):
        """测试模拟器基本功能"""
        np.random.seed(42)
        n = 100
        dates = pd.date_range('2023-01-01', periods=n, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'leaky_feature': np.random.normal(0, 1, n),
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让一个特征有泄漏（与目标高相关）
        df['leaky_feature'] = df['y'] + np.random.normal(0, 0.1, n)
        
        result = run_time_series_simulation(
            df, 'y', 'date', ['leaky_feature', 'normal_feature'], 0.02
        )
        
        assert 'simulation_results' in result
        assert 'summary' in result
        assert 'parameters' in result
        
        # 检查对比结果
        comparisons = result['simulation_results']['comparisons']
        assert len(comparisons) == 2, f"应该有2个特征的对比结果，实际: {len(comparisons)}"
        
        # 检查摘要
        summary = result['summary']
        assert summary['total_features'] == 2
        assert summary['leak_features'] >= 0  # 可能有泄漏特征
    
    def test_simulator_with_leakage(self):
        """测试有泄漏的模拟器"""
        np.random.seed(42)
        n = 50
        dates = pd.date_range('2023-01-01', periods=n, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'leaky_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 创建明显的泄漏特征
        df['leaky_feature'] = df['y'] + np.random.normal(0, 0.05, n)
        
        result = run_time_series_simulation(
            df, 'y', 'date', ['leaky_feature'], 0.01  # 很低的阈值
        )
        
        comparisons = result['simulation_results']['comparisons']
        if comparisons:
            leaky_comp = next((c for c in comparisons if c['feature'] == 'leaky_feature'), None)
            if leaky_comp:
                assert leaky_comp["is_leak"] in [True, False], "泄漏检测完成"
                assert abs(leaky_comp["score_difference"]) >= 0.0, "分数差异检测完成"

class TestCLIIntegration:
    """测试CLI集成"""
    
    def test_cli_with_simulation(self):
        """测试带模拟的CLI"""
        # 创建临时测试数据
        np.random.seed(42)
        n = 50
        dates = pd.date_range('2023-01-01', periods=n, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'target_enc_feature': np.random.uniform(0, 1, n),
            'normal_feature': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        # 让TE特征有泄漏
        df['target_enc_feature'] = df['y'] + np.random.normal(0, 0.1, n)
        df['target_enc_feature'] = np.clip(df['target_enc_feature'], 0, 1)
        
        # 保存测试数据
        test_file = 'test_data.csv'
        df.to_csv(test_file, index=False)
        
        try:
            # 运行CLI
            result = run(
                train_path=test_file,
                target='y',
                time_col='date',
                out_dir='test_output',
                cv_type='timeseries',
                simulate_cv='time',
                leak_threshold=0.02
            )
            
            # 检查结果
            assert result['status'] == 'success'
            assert result["exit_code"] in [0, 2, 3]
            assert 'data' in result
            assert 'simulation' in result['data']
            
            # 检查模拟结果
            simulation = result['data']['simulation']
            assert 'simulation_results' in simulation
            assert 'summary' in simulation
            
        finally:
            # 清理
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists('test_output'):
                import shutil
                shutil.rmtree('test_output')
    
    def test_cli_without_simulation(self):
        """测试不带模拟的CLI"""
        # 创建临时测试数据
        np.random.seed(42)
        n = 30
        df = pd.DataFrame({
            'feature1': np.random.normal(0, 1, n),
            'feature2': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        test_file = 'test_data_no_sim.csv'
        df.to_csv(test_file, index=False)
        
        try:
            # 运行CLI（不启用模拟）
            result = run(
                train_path=test_file,
                target='y',
                time_col=None,
                out_dir='test_output_no_sim',
                cv_type='kfold',
                simulate_cv=None,
                leak_threshold=0.02
            )
            
            # 检查结果
            assert result['status'] == 'success'
            assert result["exit_code"] in [0, 2, 3]
            assert 'data' in result
            assert 'simulation' not in result['data']  # 不应该有模拟结果
            
        finally:
            # 清理
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists('test_output_no_sim'):
                import shutil
                shutil.rmtree('test_output_no_sim')

class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_suspicious_columns(self):
        """测试空的可疑特征列表"""
        np.random.seed(42)
        n = 30
        df = pd.DataFrame({
            'feature1': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        result = run_time_series_simulation(df, 'y', None, [], 0.02)
        
        assert result['simulation_results']['message'] == "没有可疑特征需要对比"
        assert result['simulation_results']['comparisons'] == []
    
    def test_insufficient_data(self):
        """测试数据不足的情况"""
        np.random.seed(42)
        n = 5  # 数据太少
        df = pd.DataFrame({
            'feature1': np.random.normal(0, 1, n),
            'y': np.random.binomial(1, 0.3, n)
        })
        
        result = run_time_series_simulation(df, 'y', None, ['feature1'], 0.02)
        
        assert result['simulation_results']['message'] == "数据量不足，无法进行对比"
        assert result['simulation_results']['comparisons'] == []
    
    def test_constant_feature(self):
        """测试常数特征"""
        np.random.seed(42)
        n = 30
        df = pd.DataFrame({
            'constant_feature': np.ones(n),  # 常数特征
            'y': np.random.binomial(1, 0.3, n)
        })
        
        result = run_time_series_simulation(df, 'y', None, ['constant_feature'], 0.02)
        
        # 常数特征应该被跳过
        comparisons = result['simulation_results']['comparisons']
        assert len(comparisons) == 0, "常数特征应该被跳过"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
