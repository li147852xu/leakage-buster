
from __future__ import annotations
import argparse, os, json, sys
import pandas as pd
from .core.checks import run_checks
from .core.report import render_report, write_fix_script, write_meta
from .core.simulator import run_time_series_simulation
from .core.cv_policy import audit_cv_policy
from .core.export import export_report
from .core.loader import load_data, estimate_memory_usage
from .core.parallel import ParallelProcessor
from .api import audit, plan_fixes, apply_fixes_to_dataframe, export_audit_result

# 退出码定义
EXIT_OK = 0
EXIT_WARNINGS = 2
EXIT_HIGH_LEAKAGE = 3
EXIT_INVALID_CONFIG = 4

def run(train_path: str, target: str, time_col: str | None, out_dir: str, 
        cv_type: str | None = None, simulate_cv: str | None = None, 
        leak_threshold: float = 0.02, cv_policy_file: str | None = None,
        export: str | None = None, export_sarif: str | None = None, 
        auto_fix: str | None = None, fix_json: str | None = None, 
        fixed_train: str | None = None, engine: str = "pandas",
        n_jobs: int = -1, memory_cap: int = 4096, sample_ratio: float | None = None):
    """运行泄漏检测 - v1.0版本"""
    try:
        # 验证输入文件
        if not os.path.exists(train_path):
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Training file not found: {train_path}",
                    "details": {"file": train_path}
                }
            }
        
        # 估算内存使用
        try:
            memory_info = estimate_memory_usage(train_path)
            print(f"📊 数据概览: {memory_info['total_rows']:,} 行, {memory_info['columns']} 列")
            print(f"💾 预估内存: {memory_info['estimated_memory_mb']:.1f} MB")
            
            # 如果预估内存超过限制，启用采样
            if memory_info['estimated_memory_mb'] > memory_cap * 0.8:
                if sample_ratio is None:
                    sample_ratio = min(0.5, memory_cap / memory_info['estimated_memory_mb'])
                    print(f"⚠️  内存超限，自动启用采样: {sample_ratio:.1%}")
        except Exception as e:
            print(f"⚠️  内存估算失败: {e}")
        
        # 读取数据
        try:
            print(f"🔄 加载数据 (引擎: {engine})...")
            df = load_data(
                train_path, 
                engine=engine, 
                memory_cap_mb=memory_cap,
                sample_ratio=sample_ratio
            )
            print(f"✅ 数据加载完成: {len(df):,} 行, {len(df.columns)} 列")
        except Exception as e:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Failed to read CSV file: {str(e)}",
                    "details": {"file": train_path, "error": str(e)}
                }
            }
        
        # 验证目标列
        if target not in df.columns:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "ValidationError",
                    "message": f"Target column '{target}' not found in data",
                    "details": {"column": target, "available_columns": list(df.columns)}
                }
            }
        
        # 验证时间列
        if time_col and time_col not in df.columns:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "ValidationError",
                    "message": f"Time column '{time_col}' not found in data",
                    "details": {"column": time_col, "available_columns": list(df.columns)}
                }
            }
        
        # 使用API进行审计
        try:
            print("🔍 开始审计...")
            audit_result = audit(
                df, target=target, time_col=time_col, cv_type=cv_type,
                simulate_cv=simulate_cv, leak_threshold=leak_threshold,
                cv_policy_file=cv_policy_file, engine=engine, n_jobs=n_jobs,
                memory_cap=memory_cap, sample_ratio=sample_ratio
            )
            print(f"✅ 审计完成: 发现 {audit_result.risk_count} 个风险")
        except Exception as e:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "RuntimeError",
                    "message": f"Audit failed: {str(e)}",
                    "details": {"error": str(e)}
                }
            }
        
        # 确定退出码
        exit_code = EXIT_OK
        if audit_result.has_high_risk:
            exit_code = EXIT_HIGH_LEAKAGE
            print("🚨 检测到高危泄漏！")
        elif audit_result.has_medium_risk:
            exit_code = EXIT_WARNINGS
            print("⚠️  检测到中危风险")
        else:
            print("✅ 未发现明显风险")
        
        # 处理auto-fix
        fix_plan = None
        if auto_fix == "plan":
            try:
                print("📋 生成修复计划...")
                fix_plan = plan_fixes(audit_result, train_path)
                # 写入修复计划JSON
                if fix_json:
                    os.makedirs(os.path.dirname(fix_json), exist_ok=True)
                    with open(fix_json, 'w', encoding='utf-8') as f:
                        json.dump(fix_plan.model_dump(), f, ensure_ascii=False, indent=2)
                    print(f"✅ 修复计划已保存: {fix_json}")
            except Exception as e:
                return {
                    "status": "error",
                    "exit_code": EXIT_INVALID_CONFIG,
                    "error": {
                        "type": "RuntimeError",
                        "message": f"Fix planning failed: {str(e)}",
                        "details": {"error": str(e)}
                    }
                }
        
        elif auto_fix == "apply":
            try:
                print("🔧 应用修复...")
                fix_plan = plan_fixes(audit_result, train_path)
                fixed_df = apply_fixes_to_dataframe(df, fix_plan)
                # 写入修复后的数据
                if fixed_train:
                    os.makedirs(os.path.dirname(fixed_train), exist_ok=True)
                    fixed_df.to_csv(fixed_train, index=False)
                    print(f"✅ 修复后数据已保存: {fixed_train}")
            except Exception as e:
                return {
                    "status": "error",
                    "exit_code": EXIT_INVALID_CONFIG,
                    "error": {
                        "type": "RuntimeError",
                        "message": f"Fix application failed: {str(e)}",
                        "details": {"error": str(e)}
                    }
                }
        
        # 准备元数据
        meta = {
            "args": {
                "train": train_path, 
                "target": target, 
                "time_col": time_col, 
                "out": out_dir, 
                "cv_type": cv_type,
                "simulate_cv": simulate_cv,
                "leak_threshold": leak_threshold,
                "cv_policy_file": cv_policy_file,
                "export": export,
                "export_sarif": export_sarif,
                "auto_fix": auto_fix,
                "fix_json": fix_json,
                "fixed_train": fixed_train,
                "engine": engine,
                "n_jobs": n_jobs,
                "memory_cap": memory_cap,
                "sample_ratio": sample_ratio
            },
            "n_rows": int(len(df)),
            "n_cols": int(df.shape[1]),
            "target": target,
            "time_col": time_col,
            "cv_type": cv_type,
            "simulate_cv": simulate_cv,
            "leak_threshold": leak_threshold,
            "cv_policy_file": cv_policy_file,
            "export": export,
            "export_sarif": export_sarif,
            "auto_fix": auto_fix,
            "fix_json": fix_json,
            "fixed_train": fixed_train,
            "engine": engine,
            "n_jobs": n_jobs,
            "memory_cap": memory_cap,
            "sample_ratio": sample_ratio,
            "git_hash": os.popen('git rev-parse HEAD 2>/dev/null || echo "unknown"').read().strip(),
            "random_seed": "42"
        }
        
        # 创建输出目录
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Failed to create output directory: {str(e)}",
                    "details": {"directory": out_dir, "error": str(e)}
                }
            }
        
        # 生成输出文件
        try:
            print("📄 生成报告...")
            write_meta(meta, out_dir)
            report_path = render_report(audit_result.data, meta, out_dir, audit_result.simulation, audit_result.policy_audit)
            fix_path = write_fix_script(audit_result.data, out_dir)
            print(f"✅ 报告已生成: {report_path}")
        except Exception as e:
            return {
                "status": "error",
                "exit_code": EXIT_INVALID_CONFIG,
                "error": {
                    "type": "RuntimeError",
                    "message": f"Failed to generate output files: {str(e)}",
                    "details": {"error": str(e)}
                }
            }
        
        # 处理导出
        export_results = {}
        if export:
            try:
                print(f"📤 导出 {export.upper()}...")
                if export == "pdf":
                    pdf_path = os.path.join(out_dir, "report.pdf")
                    export_result = export_report(report_path, pdf_path, "pdf")
                    export_results["pdf"] = export_result
                    print(f"✅ PDF已导出: {pdf_path}")
                else:
                    export_results["export"] = {"status": "error", "message": f"Unsupported export type: {export}"}
            except Exception as e:
                export_results["export"] = {"status": "error", "message": f"Export failed: {str(e)}"}
        
        if export_sarif:
            try:
                print("📤 导出SARIF...")
                sarif_path = export_sarif
                export_result = export_report(None, sarif_path, "sarif", audit_result.data)
                export_results["sarif"] = export_result
                print(f"✅ SARIF已导出: {sarif_path}")
            except Exception as e:
                export_results["sarif"] = {"status": "error", "message": f"SARIF export failed: {str(e)}"}
        
        # 返回成功结果
        result_data = {
            "report": report_path,
            "fix_script": fix_path,
            "meta": meta,
            "risks": audit_result.risks,
            "summary": {
                "total_risks": audit_result.risk_count,
                "high_risks": audit_result.high_risk_count,
                "medium_risks": audit_result.medium_risk_count,
                "low_risks": audit_result.low_risk_count,
                "has_high_risk": audit_result.has_high_risk,
                "has_medium_risk": audit_result.has_medium_risk
            }
        }
        
        # 添加模拟结果
        if audit_result.simulation:
            result_data["simulation"] = audit_result.simulation
        
        # 添加策略审计结果
        if audit_result.policy_audit:
            result_data["policy_audit"] = audit_result.policy_audit
        
        # 添加导出结果
        if export_results:
            result_data["exports"] = export_results
        
        # 添加修复计划
        if fix_plan:
            result_data["fix_plan"] = fix_plan.model_dump()
        
        return {
            "status": "success",
            "exit_code": exit_code,
            "data": result_data
        }
        
    except Exception as e:
        # 捕获未预期的错误
        return {
            "status": "error",
            "exit_code": EXIT_INVALID_CONFIG,
            "error": {
                "type": "RuntimeError",
                "message": f"Unexpected error: {str(e)}",
                "details": {"error": str(e)}
            }
        }

def build_parser():
    p = argparse.ArgumentParser(
        prog="leakage-buster", 
        description="Data leakage detection and audit tool v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 基本检测
  leakage-buster run --train data.csv --target y --out runs/audit
  
  # 高性能检测
  leakage-buster run --train data.csv --target y --time-col date --out runs/audit \\
    --engine pandas --n-jobs 8 --memory-cap 4096
  
  # 生成修复计划
  leakage-buster run --train data.csv --target y --out runs/audit \\
    --auto-fix plan --fix-json runs/audit/fix_plan.json
  
  # 应用修复
  leakage-buster run --train data.csv --target y --out runs/audit \\
    --auto-fix apply --fixed-train runs/audit/fixed_data.csv
  
  # 导出PDF和SARIF
  leakage-buster run --train data.csv --target y --out runs/audit \\
    --export pdf --export-sarif runs/audit/leakage.sarif
        """
    )
    sub = p.add_subparsers(dest="cmd")
    run_p = sub.add_parser("run", help="Run leakage audit")
    
    # 基础参数
    run_p.add_argument("--train", type=str, required=True, help="Training data CSV file")
    run_p.add_argument("--target", type=str, required=True, help="Target column name")
    run_p.add_argument("--time-col", type=str, default=None, help="Time column name (optional)")
    run_p.add_argument("--out", type=str, required=True, help="Output directory")
    
    # CV策略参数
    run_p.add_argument("--cv-type", type=str, choices=["kfold", "timeseries", "group"], 
                       default=None, help="CV strategy: kfold/timeseries/group")
    run_p.add_argument("--simulate-cv", type=str, choices=["time"], default=None,
                       help="Enable time series simulation: time")
    run_p.add_argument("--leak-threshold", type=float, default=0.02,
                       help="Leak threshold for simulation (default: 0.02)")
    run_p.add_argument("--cv-policy-file", type=str, default=None,
                       help="CV policy configuration file (YAML)")
    
    # 性能参数
    run_p.add_argument("--engine", type=str, choices=["pandas", "polars"], default="pandas",
                       help="Data processing engine (default: pandas)")
    run_p.add_argument("--n-jobs", type=int, default=-1,
                       help="Number of parallel jobs (default: auto)")
    run_p.add_argument("--memory-cap", type=int, default=4096,
                       help="Memory limit in MB (default: 4096)")
    run_p.add_argument("--sample-ratio", type=float, default=None,
                       help="Sample ratio for large datasets (0.0-1.0)")
    
    # 导出参数
    run_p.add_argument("--export", type=str, choices=["pdf"], default=None,
                       help="Export report format: pdf")
    run_p.add_argument("--export-sarif", type=str, default=None,
                       help="Export SARIF file path for GitHub Code Scanning")
    
    # 自动修复参数
    run_p.add_argument("--auto-fix", type=str, choices=["plan", "apply"], default=None,
                       help="Auto-fix mode: plan (generate fix plan) or apply (apply fixes)")
    run_p.add_argument("--fix-json", type=str, default=None,
                       help="Fix plan JSON output path (used with --auto-fix plan)")
    run_p.add_argument("--fixed-train", type=str, default=None,
                       help="Fixed training data CSV output path (used with --auto-fix apply)")
    
    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if args.cmd == "run" or (args.cmd is None and hasattr(args, "train")):
        result = run(args.train, args.target, args.time_col, args.out, 
                    args.cv_type, args.simulate_cv, args.leak_threshold,
                    args.cv_policy_file, args.export, args.export_sarif,
                    args.auto_fix, args.fix_json, args.fixed_train,
                    args.engine, args.n_jobs, args.memory_cap, args.sample_ratio)
        
        # 输出JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 设置退出码
        sys.exit(result["exit_code"])
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

