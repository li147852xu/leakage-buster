# PyPI 和 Codecov 完成指南

## 🎯 当前状态

✅ **已完成**:
- CI工作流修复 (Python 3.9-3.12)
- 覆盖率配置 (73% coverage)
- PyPI包构建 (setup.py, MANIFEST.in, LICENSE)
- GitHub Actions配置
- 代码覆盖率报告生成

## 🚀 完成 PyPI 发布

### 1. 获取 PyPI API Token

1. 访问 [PyPI](https://pypi.org) 并登录
2. 进入 [Account Settings](https://pypi.org/manage/account/)
3. 滚动到 "API tokens" 部分
4. 点击 "Add API token"
5. 输入名称: `leakage-buster-github`
6. 选择范围: `Entire account (all projects)`
7. 复制生成的 token (格式: `pypi-...`)

### 2. 配置 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets:

```
TEST_PYPI_API_TOKEN=pypi-your-testpypi-token
PYPI_API_TOKEN=pypi-your-pypi-token
```

### 3. 发布到 TestPyPI (测试)

```bash
# 使用发布脚本
python scripts/publish.py

# 或手动发布
twine upload --repository testpypi dist/*
```

### 4. 发布到正式 PyPI

```bash
# 手动发布
twine upload dist/*

# 或通过 GitHub Actions (推送 v* 标签)
git tag v1.0.3
git push origin v1.0.3
```

## 📊 完成 Codecov 集成

### 1. 连接 Codecov

1. 访问 [Codecov](https://codecov.io)
2. 使用 GitHub 账号登录
3. 添加仓库: `li147852xu/leakage-buster`
4. 获取 Codecov token (如果需要)

### 2. 配置 GitHub Secrets (如需要)

```
CODECOV_TOKEN=your-codecov-token
```

### 3. 验证集成

推送代码后，Codecov 会自动:
- 分析覆盖率报告
- 更新徽章
- 显示覆盖率详情

## 🔍 验证步骤

### PyPI 验证
1. 访问 https://pypi.org/project/leakage-buster/
2. 确认版本 1.0.2 可见
3. 测试安装: `pip install leakage-buster==1.0.2`

### Codecov 验证
1. 访问 https://codecov.io/gh/li147852xu/leakage-buster
2. 确认覆盖率报告显示 73%
3. 检查徽章状态

### GitHub 徽章验证
- [![PyPI version](https://img.shields.io/pypi/v/leakage-buster.svg)](https://pypi.org/project/leakage-buster/)
- [![codecov](https://codecov.io/gh/li147852xu/leakage-buster/branch/main/graph/badge.svg)](https://codecov.io/gh/li147852xu/leakage-buster)

## 📋 当前覆盖率报告

```
Name                                   Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------
src/leakage_buster/api.py                 80     22     14      1    71%
src/leakage_buster/cli.py                155     55     40      6    67%
src/leakage_buster/core/checks.py        289     48    138     25    78%
src/leakage_buster/core/cv_policy.py     129     10     46     10    87%
src/leakage_buster/core/export.py         90     14     20      7    79%
src/leakage_buster/core/fix_apply.py      51     16     26      7    60%
src/leakage_buster/core/fix_plan.py       72      6     24      3    86%
src/leakage_buster/core/loader.py        100     38     42      7    54%
src/leakage_buster/core/parallel.py       75     38     12      2    45%
src/leakage_buster/core/report.py         65     16     16      3    77%
src/leakage_buster/core/simulator.py      87     12     28      7    83%
----------------------------------------------------------------------------------
TOTAL                                   1195    275    406     78    73%
```

## 🎉 完成后的状态

当所有步骤完成后，您将看到:

- ✅ **PyPI 徽章**: 显示最新版本号
- ✅ **Codecov 徽章**: 显示 73% 覆盖率
- ✅ **CI 徽章**: 显示 passing 状态
- ✅ **Python 版本徽章**: 显示支持的版本
- ✅ **License 徽章**: 显示 MIT 许可证

## 📞 需要帮助?

如果遇到问题，请检查:
1. API tokens 是否正确配置
2. GitHub Secrets 是否设置
3. 仓库权限是否正确
4. 网络连接是否正常

---

**状态**: 🟡 等待 API token 配置
**下一步**: 配置 PyPI 和 Codecov API tokens
