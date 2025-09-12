
# JSON Schema 规范

## 输出格式

Leakage Buster 的输出遵循统一的 JSON 格式，便于与 tabular-agent 等下游系统集成。

## 成功输出 Schema

```json
{
  "status": "success",
  "exit_code": 0,
  "data": {
    "report": "path/to/report.html",
    "fix_script": "path/to/fix_transforms.py",
    "meta": {
      "args": {
        "train": "path/to/train.csv",
        "target": "target_column",
        "time_col": "date_column",
        "cv_type": "timeseries",
        "out": "output_directory"
      },
      "n_rows": 1000,
      "n_cols": 10,
      "target": "target_column",
      "time_col": "date_column",
      "cv_type": "timeseries"
    },
    "risks": [
      {
        "name": "风险项名称",
        "severity": "high|medium|low",
        "detail": "风险描述",
        "evidence": {
          "columns": {...},
          "candidates": [...],
          "recommended": "...",
          "specified": "..."
        }
      }
    ]
  }
}
```

## 错误输出 Schema

```json
{
  "status": "error",
  "exit_code": 2,
  "error": {
    "type": "ValidationError|FileNotFoundError|RuntimeError",
    "message": "错误描述",
    "details": {
      "file": "problematic_file.csv",
      "column": "missing_column",
      "line": 123
    }
  }
}
```

## 字段规范

### RiskItem 结构

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `name` | string | ✅ | 风险项名称，用于识别风险类型 |
| `severity` | string | ✅ | 严重级别：`high`、`medium`、`low` |
| `detail` | string | ✅ | 人类可读的风险描述 |
| `evidence` | object | ✅ | 证据数据，结构因风险类型而异 |

### 严重级别定义

- **high**: 高危风险，可能导致模型过拟合或数据泄漏
- **medium**: 中危风险，建议修复但不影响基本功能
- **low**: 低危风险，优化建议

### Evidence 结构示例

#### 目标泄漏证据
```json
{
  "columns": {
    "suspicious_col": 0.99,
    "another_col": 0.98
  }
}
```

#### 分组泄漏证据
```json
{
  "candidates": [
    {
      "column": "user_id",
      "nunique": 100,
      "dup_rate": 0.9
    }
  ]
}
```

#### CV策略证据
```json
{
  "specified": "kfold",
  "recommended": "timeseries",
  "has_time": true,
  "has_groups": false,
  "group_columns": []
}
```

## 退出码定义

| 退出码 | 含义 | 描述 |
|--------|------|------|
| 0 | 成功 | 检测完成，无错误 |
| 2 | 验证错误 | 输入数据格式错误、必需参数缺失 |
| 3 | 文件错误 | 文件不存在、无法读取、权限问题 |
| 4 | 运行时错误 | 检测过程中发生异常 |

## 与 tabular-agent 集成

### 输入接口

tabular-agent 调用 leakage-buster 时，应提供以下参数：

```bash
leakage-buster run \
  --train <csv_path> \
  --target <target_column> \
  --time-col <time_column> \
  --cv-type <kfold|timeseries|group> \
  --out <output_directory>
```

### 输出解析

tabular-agent 应解析 JSON 输出中的以下关键信息：

1. **状态检查**: 检查 `status` 和 `exit_code`
2. **风险分析**: 遍历 `risks` 数组，按 `severity` 分类
3. **修复建议**: 使用 `fix_script` 路径获取具体修复代码
4. **元数据**: 使用 `meta` 信息进行后续处理

### 错误处理

```python
import json
import subprocess

def run_leakage_audit(train_path, target, time_col=None, cv_type=None, out_dir="runs/audit"):
    try:
        result = subprocess.run([
            "leakage-buster", "run",
            "--train", train_path,
            "--target", target,
            "--out", out_dir
        ] + (["--time-col", time_col] if time_col else [])
         + (["--cv-type", cv_type] if cv_type else []),
            capture_output=True, text=True, check=True
        )
        
        output = json.loads(result.stdout)
        if output["status"] == "success":
            return output["data"]
        else:
            raise RuntimeError(f"Audit failed: {output['error']['message']}")
            
    except subprocess.CalledProcessError as e:
        # 处理退出码错误
        if e.returncode == 2:
            raise ValueError("Invalid input parameters")
        elif e.returncode == 3:
            raise FileNotFoundError("Input file not found or inaccessible")
        elif e.returncode == 4:
            raise RuntimeError("Audit execution failed")
        else:
            raise RuntimeError(f"Unknown error: {e.returncode}")
```

