
# CLI 参数规范

## 命令格式

```bash
leakage-buster run [OPTIONS]
```

## 必需参数

| 参数 | 类型 | 描述 | 示例 |
|------|------|------|------|
| `--train` | string | 训练数据CSV文件路径 | `--train data/train.csv` |
| `--target` | string | 目标列名称 | `--target y` |
| `--out` | string | 输出目录路径 | `--out runs/audit_2024` |

## 可选参数

| 参数 | 类型 | 默认值 | 描述 | 示例 |
|------|------|--------|------|------|
| `--time-col` | string | `null` | 时间列名称，用于时间序列分析 | `--time-col date` |
| `--cv-type` | string | `null` | CV策略类型 | `--cv-type timeseries` |

## CV策略类型

| 值 | 描述 | 适用场景 |
|----|------|----------|
| `kfold` | 标准K折交叉验证 | 无时间依赖的独立样本 |
| `timeseries` | 时间序列分割 | 有时间顺序的数据 |
| `group` | 分组交叉验证 | 有分组结构的数据 |

## 输出文件

执行成功后，在输出目录中生成以下文件：

| 文件名 | 描述 |
|--------|------|
| `report.html` | 可视化审计报告 |
| `fix_transforms.py` | 修复建议代码 |
| `meta.json` | 元数据和参数信息 |

## 使用示例

### 基础用法
```bash
leakage-buster run --train data.csv --target y --out results/
```

### 时间序列数据
```bash
leakage-buster run \
  --train data.csv \
  --target y \
  --time-col timestamp \
  --cv-type timeseries \
  --out results/
```

### 分组数据
```bash
leakage-buster run \
  --train data.csv \
  --target y \
  --cv-type group \
  --out results/
```

## 错误处理

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `FileNotFoundError: train file not found` | 训练文件不存在 | 检查文件路径是否正确 |
| `ValueError: target column not found` | 目标列不存在 | 检查列名是否正确 |
| `ValueError: time column not found` | 时间列不存在 | 检查时间列名或移除该参数 |
| `ValueError: invalid cv_type` | CV类型无效 | 使用 `kfold`、`timeseries` 或 `group` |

### 退出码

| 退出码 | 含义 | 处理建议 |
|--------|------|----------|
| 0 | 成功 | 正常处理输出结果 |
| 2 | 参数错误 | 检查命令行参数 |
| 3 | 文件错误 | 检查文件路径和权限 |
| 4 | 运行时错误 | 查看错误日志，联系支持 |

## 性能考虑

- **大文件处理**: 对于超过100万行的CSV文件，建议先采样测试
- **内存使用**: 检测过程会加载整个数据集到内存
- **并行处理**: 当前版本为单线程，后续版本将支持并行检测

## 集成建议

### 与 tabular-agent 集成

```python
import subprocess
import json

def audit_dataset(train_path, target_col, time_col=None, cv_type=None):
    """执行数据泄漏审计"""
    cmd = [
        "leakage-buster", "run",
        "--train", train_path,
        "--target", target_col,
        "--out", "runs/audit"
    ]
    
    if time_col:
        cmd.extend(["--time-col", time_col])
    if cv_type:
        cmd.extend(["--cv-type", cv_type])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"error": f"Audit failed with code {e.returncode}"}
```

### 批量处理

```bash
# 批量审计多个数据集
for dataset in data/*.csv; do
  echo "Auditing $dataset..."
  leakage-buster run \
    --train "$dataset" \
    --target "target" \
    --out "results/$(basename "$dataset" .csv)"
done
```

