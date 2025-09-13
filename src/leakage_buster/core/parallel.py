
from __future__ import annotations
import multiprocessing as mp
from typing import List, Callable, Any, Dict, Optional
import time
import psutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import warnings

try:
    from joblib import Parallel, delayed
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

class ParallelProcessor:
    """并行处理器"""
    
    def __init__(self, n_jobs: int = -1, backend: str = "threading", 
                 memory_cap_mb: int = 4096, timeout: int = 300):
        self.n_jobs = n_jobs if n_jobs > 0 else mp.cpu_count()
        self.backend = backend
        self.memory_cap_mb = memory_cap_mb
        self.timeout = timeout
        
        # 根据内存限制调整并行数
        self.n_jobs = min(self.n_jobs, self._get_optimal_jobs())
    
    def _get_optimal_jobs(self) -> int:
        """根据内存和CPU获取最优并行数"""
        cpu_count = mp.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # 基于内存的并行数限制
        memory_based_jobs = max(1, int(memory_gb / (self.memory_cap_mb / 1024)))
        
        return min(cpu_count, memory_based_jobs, 8)  # 最多8个进程
    
    def parallel_apply(self, func: Callable, data_list: List[Any], 
                      progress: bool = False) -> List[Any]:
        """并行应用函数"""
        if len(data_list) <= 1 or self.n_jobs == 1:
            return [func(item) for item in data_list]
        
        if JOBLIB_AVAILABLE and self.backend in ["loky", "threading"]:
            return self._joblib_parallel_apply(func, data_list, progress)
        else:
            return self._concurrent_parallel_apply(func, data_list)
    
    def _joblib_parallel_apply(self, func: Callable, data_list: List[Any], 
                              progress: bool = False) -> List[Any]:
        """使用joblib并行应用"""
        try:
            return Parallel(
                n_jobs=self.n_jobs,
                backend=self.backend,
                timeout=self.timeout,
                verbose=1 if progress else 0
            )(delayed(func)(item) for item in data_list)
        except Exception as e:
            warnings.warn(f"Joblib parallel failed: {e}, falling back to sequential")
            return [func(item) for item in data_list]
    
    def _concurrent_parallel_apply(self, func: Callable, data_list: List[Any]) -> List[Any]:
        """使用concurrent.futures并行应用"""
        try:
            if self.backend == "threading":
                with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
                    return list(executor.map(func, data_list))
            else:
                with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
                    return list(executor.map(func, data_list))
        except Exception as e:
            warnings.warn(f"Concurrent parallel failed: {e}, falling back to sequential")
            return [func(item) for item in data_list]
    
    def parallel_map(self, func: Callable, *iterables, progress: bool = False) -> List[Any]:
        """并行映射函数"""
        if len(iterables) == 0:
            return []
        
        # 检查所有iterables长度相同
        lengths = [len(iterable) for iterable in iterables]
        if not all(length == lengths[0] for length in lengths):
            raise ValueError("All iterables must have the same length")
        
        # 创建参数元组列表
        data_list = list(zip(*iterables))
        
        def wrapper(args):
            return func(*args)
        
        return self.parallel_apply(wrapper, data_list, progress)
    
    def batch_process(self, func: Callable, data_list: List[Any], 
                     batch_size: Optional[int] = None) -> List[Any]:
        """批处理数据"""
        if batch_size is None:
            batch_size = max(1, len(data_list) // self.n_jobs)
        
        batches = [data_list[i:i + batch_size] for i in range(0, len(data_list), batch_size)]
        
        def process_batch(batch):
            return [func(item) for item in batch]
        
        results = self.parallel_apply(process_batch, batches)
        
        # 展平结果
        return [item for batch_result in results for item in batch_result]
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "cpu_count": mp.cpu_count(),
            "n_jobs": self.n_jobs,
            "backend": self.backend,
            "memory_cap_mb": self.memory_cap_mb,
            "timeout": self.timeout,
            "joblib_available": JOBLIB_AVAILABLE,
            "memory_usage_percent": psutil.virtual_memory().percent
        }

def parallel_apply(func: Callable, data_list: List[Any], n_jobs: int = -1,
                   backend: str = "threading", progress: bool = False) -> List[Any]:
    """并行应用函数的便捷函数"""
    processor = ParallelProcessor(n_jobs=n_jobs, backend=backend)
    return processor.parallel_apply(func, data_list, progress)

def parallel_map(func: Callable, *iterables, n_jobs: int = -1,
                 backend: str = "threading", progress: bool = False) -> List[Any]:
    """并行映射函数的便捷函数"""
    processor = ParallelProcessor(n_jobs=n_jobs, backend=backend)
    return processor.parallel_map(func, *iterables, progress=progress)

def batch_process(func: Callable, data_list: List[Any], n_jobs: int = -1,
                  batch_size: Optional[int] = None) -> List[Any]:
    """批处理数据的便捷函数"""
    processor = ParallelProcessor(n_jobs=n_jobs)
    return processor.batch_process(func, data_list, batch_size)

