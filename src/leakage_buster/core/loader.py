
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Union, Dict, Any, Tuple
import psutil
import gc
import warnings
from pathlib import Path

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

class DataLoader:
    """数据加载器，支持pandas和polars引擎"""
    
    def __init__(self, engine: str = "pandas", memory_cap_mb: int = 4096, 
                 chunk_size: int = 10000, sample_ratio: Optional[float] = None):
        self.engine = engine
        self.memory_cap_mb = memory_cap_mb
        self.chunk_size = chunk_size
        self.sample_ratio = sample_ratio
        
        if engine == "polars" and not POLARS_AVAILABLE:
            warnings.warn("Polars not available, falling back to pandas")
            self.engine = "pandas"
    
    def load_data(self, file_path: str, **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
        """加载数据文件"""
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        
        # 检查文件大小
        if file_size_mb > self.memory_cap_mb * 0.8:  # 留20%缓冲
            return self._load_large_file(file_path, **kwargs)
        else:
            return self._load_small_file(file_path, **kwargs)
    
    def _load_small_file(self, file_path: str, **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
        """加载小文件"""
        if self.engine == "polars":
            return pl.read_csv(file_path, **kwargs)
        else:
            return pd.read_csv(file_path, **kwargs)
    
    def _load_large_file(self, file_path: str, **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
        """加载大文件，使用分块或采样策略"""
        if self.sample_ratio and self.sample_ratio < 1.0:
            return self._load_sampled(file_path, **kwargs)
        else:
            return self._load_chunked(file_path, **kwargs)
    
    def _load_sampled(self, file_path: str, **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
        """采样加载"""
        if self.engine == "polars":
            # Polars采样
            df = pl.read_csv(file_path, **kwargs)
            n_rows = len(df)
            sample_size = int(n_rows * self.sample_ratio)
            return df.sample(sample_size, seed=42)
        else:
            # Pandas采样
            df = pd.read_csv(file_path, **kwargs)
            return df.sample(frac=self.sample_ratio, random_state=42)
    
    def _load_chunked(self, file_path: str, **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
        """分块加载"""
        if self.engine == "polars":
            # Polars分块读取
            return pl.scan_csv(file_path, **kwargs).collect()
        else:
            # Pandas分块读取
            chunks = []
            for chunk in pd.read_csv(file_path, chunksize=self.chunk_size, **kwargs):
                chunks.append(chunk)
                if self._check_memory_usage():
                    break
            return pd.concat(chunks, ignore_index=True)
    
    def _check_memory_usage(self) -> bool:
        """检查内存使用情况"""
        memory_usage = psutil.virtual_memory().percent
        return memory_usage > 80  # 内存使用超过80%时停止
    
    def optimize_dataframe(self, df: Union[pd.DataFrame, pl.DataFrame]) -> Union[pd.DataFrame, pl.DataFrame]:
        """优化数据框内存使用"""
        if self.engine == "polars":
            return self._optimize_polars(df)
        else:
            return self._optimize_pandas(df)
    
    def _optimize_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化pandas数据框"""
        # 转换数值类型
        for col in df.select_dtypes(include=['int64']).columns:
            if df[col].min() >= 0:
                if df[col].max() < 255:
                    df[col] = df[col].astype('uint8')
                elif df[col].max() < 65535:
                    df[col] = df[col].astype('uint16')
                elif df[col].max() < 4294967295:
                    df[col] = df[col].astype('uint32')
            else:
                if df[col].min() > -128 and df[col].max() < 127:
                    df[col] = df[col].astype('int8')
                elif df[col].min() > -32768 and df[col].max() < 32767:
                    df[col] = df[col].astype('int16')
                elif df[col].min() > -2147483648 and df[col].max() < 2147483647:
                    df[col] = df[col].astype('int32')
        
        # 转换浮点类型
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # 转换对象类型
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    df[col] = df[col].astype('category')
        
        return df
    
    def _optimize_polars(self, df: pl.DataFrame) -> pl.DataFrame:
        """优化polars数据框"""
        # Polars通常已经优化了内存使用
        return df
    
    def get_memory_usage(self, df: Union[pd.DataFrame, pl.DataFrame]) -> Dict[str, Any]:
        """获取数据框内存使用情况"""
        if self.engine == "polars":
            return {
                "memory_usage_mb": df.estimated_size() / (1024 * 1024),
                "rows": df.height,
                "columns": df.width
            }
        else:
            return {
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "rows": len(df),
                "columns": len(df.columns)
            }

def load_data(file_path: str, engine: str = "pandas", memory_cap_mb: int = 4096,
              chunk_size: int = 10000, sample_ratio: Optional[float] = None,
              **kwargs) -> Union[pd.DataFrame, pl.DataFrame]:
    """加载数据的便捷函数"""
    loader = DataLoader(engine, memory_cap_mb, chunk_size, sample_ratio)
    df = loader.load_data(file_path, **kwargs)
    return loader.optimize_dataframe(df)

def estimate_memory_usage(file_path: str, sample_rows: int = 1000) -> Dict[str, Any]:
    """估算文件内存使用情况"""
    # 读取样本数据
    sample_df = pd.read_csv(file_path, nrows=sample_rows)
    
    # 估算内存使用
    sample_memory = sample_df.memory_usage(deep=True).sum()
    
    # 获取文件总行数
    with open(file_path, 'r') as f:
        total_rows = sum(1 for line in f) - 1  # 减去标题行
    
    estimated_memory = (sample_memory / sample_rows) * total_rows
    
    return {
        "estimated_memory_mb": estimated_memory / (1024 * 1024),
        "total_rows": total_rows,
        "columns": len(sample_df.columns),
        "sample_memory_mb": sample_memory / (1024 * 1024)
    }

