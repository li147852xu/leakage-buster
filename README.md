
# Leakage Buster v0.1

> 自动检测时间泄漏 / KFold 泄漏 / 口径不一致，并生成**修复脚本**与**审计报告**。

## 快速开始

### 安装

```bash
pip install -e .
```

### 基础用法

```bash
# 基础检测
leakage-buster run --train data.csv --target y --out results/

# 时间序列数据
leakage-buster run --train data.csv --target y --time-col date --out results/
```

## 检测功能

- **目标泄漏检测**: 识别与目标高度相关的特征（|corr|/R²≥0.98）
- **分类纯度异常**: 检测类别纯度异常（p≈0 或 1）
- **KFold泄漏预警**: 识别高重复/低唯一度列，建议使用GroupKFold
- **时间列解析**: 验证时间列格式并提供时间感知建议

## 输出文件

执行成功后，在输出目录中生成：

| 文件名 | 描述 |
|--------|------|
| `report.html` | 可视化审计报告 |
| `fix_transforms.py` | 修复建议代码 |
| `meta.json` | 元数据和参数信息 |

## 使用示例

```bash
# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo
```

## 测试

```bash
# 运行测试
pytest -q

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo
```

