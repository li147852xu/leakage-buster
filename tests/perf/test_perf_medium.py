
import pytest
import pandas as pd
import numpy as np
import time
import os
import sys
import tempfile
from pathlib import Path

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from leakage_buster.api import audit
from leakage_buster.core.loader import load_data, estimate_memory_usage
from leakage_buster.core.parallel import ParallelProcessor

@pytest.mark.perf
class TestPerformanceMedium:
    """中等规模性能测试"""
    
    @pytest.fixture
    def medium_dataset(self):
        """创建中等规模数据集（10-20万行，200+列）"""
        n_rows = 150000  # 15万行
        n_cols = 250     # 250列
        
        # 创建基础数据
        data = {}
        
        # 数值列
        for i in range(100):
            data[f'num_{i}'] = np.random.normal(0, 1, n_rows)
        
        # 类别列
        for i in range(50):
            data[f'cat_{i}'] = np.random.choice([f'cat_{j}' for j in range(10)], n_rows)
        
        # 时间列
        data['date'] = pd.date_range('2020-01-01', periods=n_rows, freq='1H')
        
        # 目标列
        data['target'] = np.random.binomial(1, 0.3, n_rows)
        
        # 一些泄漏列
        data['leak_1'] = data['target'] + np.random.normal(0, 0.01, n_rows)
        data['leak_2'] = data['target'] * 100 + np.random.normal(0, 0.1, n_rows)
        
        # 更多随机列
        for i in range(100, n_cols - 5):  # 减去已创建的列
            data[f'random_{i}'] = np.random.normal(0, 1, n_rows)
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def temp_csv(self, medium_dataset):
        """创建临时CSV文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            medium_dataset.to_csv(f, index=False)
            return f.name
    
    def test_memory_estimation(self, temp_csv):
        """测试内存估算"""
        memory_info = estimate_memory_usage(temp_csv, sample_rows=1000)
        
        assert memory_info['total_rows'] == 150000
        assert memory_info['columns'] == 250
        assert memory_info['estimated_memory_mb'] > 0
        
        print(f"Estimated memory usage: {memory_info['estimated_memory_mb']:.2f} MB")
    
    def test_pandas_loading_performance(self, temp_csv):
        """测试pandas加载性能"""
        start_time = time.time()
        
        df = load_data(temp_csv, engine='pandas', memory_cap_mb=4096)
        
        load_time = time.time() - start_time
        
        assert len(df) == 150000
        assert len(df.columns) == 250
        assert load_time < 30  # 30秒内完成加载
        
        print(f"Pandas loading time: {load_time:.2f} seconds")
    
    def test_audit_performance_pandas(self, temp_csv):
        """测试pandas引擎审计性能"""
        start_time = time.time()
        
        audit_result = audit(
            pd.read_csv(temp_csv), 
            target='target', 
            time_col='date',
            cv_type='timeseries'
        )
        
        audit_time = time.time() - start_time
        
        assert audit_result.risk_count >= 0
        assert audit_time < 120  # 2分钟内完成审计
        
        print(f"Pandas audit time: {audit_time:.2f} seconds")
        print(f"Risks detected: {audit_result.risk_count}")
    
    def test_parallel_processing(self, medium_dataset):
        """测试并行处理性能"""
        # 创建测试函数
        def process_chunk(chunk):
            return chunk['target'].sum()
        
        # 分块数据
        chunk_size = 10000
        chunks = [medium_dataset.iloc[i:i+chunk_size] for i in range(0, len(medium_dataset), chunk_size)]
        
        # 测试并行处理
        processor = ParallelProcessor(n_jobs=4, backend='threading')
        
        start_time = time.time()
        results = processor.parallel_apply(process_chunk, chunks)
        parallel_time = time.time() - start_time
        
        # 测试串行处理
        start_time = time.time()
        serial_results = [process_chunk(chunk) for chunk in chunks]
        serial_time = time.time() - start_time
        
        assert len(results) == len(serial_results)
        assert sum(results) == sum(serial_results)
        
        print(f"Parallel time: {parallel_time:.2f} seconds")
        print(f"Serial time: {serial_time:.2f} seconds")
        print(f"Speedup: {serial_time / parallel_time:.2f}x")
    
    def test_memory_optimization(self, temp_csv):
        """测试内存优化"""
        # 加载原始数据
        df_original = pd.read_csv(temp_csv)
        original_memory = df_original.memory_usage(deep=True).sum() / (1024 * 1024)
        
        # 加载优化数据
        df_optimized = load_data(temp_csv, engine='pandas', memory_cap_mb=4096)
        optimized_memory = df_optimized.memory_usage(deep=True).sum() / (1024 * 1024)
        
        assert len(df_original) == len(df_optimized)
        assert len(df_original.columns) == len(df_optimized.columns)
        
        print(f"Original memory: {original_memory:.2f} MB")
        print(f"Optimized memory: {optimized_memory:.2f} MB")
        print(f"Memory reduction: {(1 - optimized_memory / original_memory) * 100:.1f}%")
    
    def test_large_dataset_handling(self, temp_csv):
        """测试大数据集处理"""
        # 测试内存限制
        start_time = time.time()
        
        df = load_data(temp_csv, engine='pandas', memory_cap_mb=2048, sample_ratio=0.5)
        
        load_time = time.time() - start_time
        
        assert len(df) == 75000  # 50%采样
        assert load_time < 60  # 1分钟内完成
        
        print(f"Sampled dataset size: {len(df)} rows")
        print(f"Load time with sampling: {load_time:.2f} seconds")
    
    def test_system_info(self):
        """测试系统信息"""
        processor = ParallelProcessor(n_jobs=4)
        info = processor.get_system_info()
        
        assert info['cpu_count'] > 0
        assert info['n_jobs'] > 0
        assert info['memory_usage_percent'] >= 0
        
        print(f"System info: {info}")
    
    def teardown_method(self):
        """清理临时文件"""
        # 清理可能的临时文件
        for file in Path('.').glob('temp_*.csv'):
            try:
                file.unlink()
            except:
                pass

@pytest.mark.perf
class TestPerformanceLarge:
    """大规模性能测试（可选）"""
    
    @pytest.mark.slow
    def test_very_large_dataset(self):
        """测试超大数据集（标记为慢测试）"""
        # 这里可以添加超大数据集的测试
        # 例如：100万行，500列
        pass

if __name__ == '__main__':
    # 运行性能测试
    pytest.main([__file__, '-v', '-k', 'perf', '-s'])
