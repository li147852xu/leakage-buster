# Leakage Buster

> 自动检测时间泄漏 / KFold 泄漏 / 口径不一致，并生成**修复脚本**与**审计报告**。

## 快速开始

```bash
pip install -e .
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo
```
