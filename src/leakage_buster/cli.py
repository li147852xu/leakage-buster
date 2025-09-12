
from __future__ import annotations
import argparse, os, json, sys
import pandas as pd
from .core.checks import run_checks
from .core.report import render_report, write_fix_script, write_meta
from .core.simulator import run_time_series_simulation
from .core.cv_policy import audit_cv_policy
from .core.export import export_report

def run(train_path: str, target: str, time_col: str | None, out_dir: str, cv_type: str | None = None, 
        simulate_cv: str | None = None, leak_threshold: float = 0.02, cv_policy_file: str | None = None,
        export: str | None = None, export_sarif: str | None = None):
    """运行泄漏检测 - v0.4版本"""
    try:
        # 验证输入文件
        if not os.path.exists(train_path):
            return {
                "status": "error",
                "exit_code": 3,
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Training file not found: {train_path}",
                    "details": {"file": train_path}
                }
            }
        
        # 读取数据
        try:
            df = pd.read_csv(train_path)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 3,
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
                "exit_code": 2,
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
                "exit_code": 2,
                "error": {
                    "type": "ValidationError",
                    "message": f"Time column '{time_col}' not found in data",
                    "details": {"column": time_col, "available_columns": list(df.columns)}
                }
            }
        
        # 运行检测
        try:
            results = run_checks(df, target=target, time_col=time_col, cv_type=cv_type)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 4,
                "error": {
                    "type": "RuntimeError",
                    "message": f"Detection failed: {str(e)}",
                    "details": {"error": str(e)}
                }
            }
        
        # 运行时序模拟（如果启用）
        simulation_results = None
        if simulate_cv == "time":
            try:
                # 提取可疑特征
                suspicious_cols = []
                for risk in results.get("risks", []):
                    if "suspicious_columns" in risk.get("evidence", {}):
                        suspicious_cols.extend(risk["evidence"]["suspicious_columns"].keys())
                
                if suspicious_cols:
                    simulation_results = run_time_series_simulation(
                        df, target, time_col, suspicious_cols, leak_threshold
                    )
            except Exception as e:
                # 模拟失败不影响主流程
                simulation_results = {"error": f"Simulation failed: {str(e)}"}
        
        # 运行CV策略审计（如果提供策略文件）
        policy_audit = None
        if cv_policy_file:
            try:
                policy_audit = audit_cv_policy(df, target, time_col, cv_policy_file)
            except Exception as e:
                # 策略审计失败不影响主流程
                policy_audit = {"error": f"Policy audit failed: {str(e)}"}
        
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
                "export_sarif": export_sarif
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
        }
        
        # 创建输出目录
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 3,
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Failed to create output directory: {str(e)}",
                    "details": {"directory": out_dir, "error": str(e)}
                }
            }
        
        # 生成输出文件
        try:
            write_meta(meta, out_dir)
            report_path = render_report(results, meta, out_dir, simulation_results, policy_audit)
            fix_path = write_fix_script(results, out_dir)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 4,
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
                if export == "pdf":
                    pdf_path = os.path.join(out_dir, "report.pdf")
                    export_result = export_report(report_path, pdf_path, "pdf")
                    export_results["pdf"] = export_result
                else:
                    export_results["export"] = {"status": "error", "message": f"Unsupported export type: {export}"}
            except Exception as e:
                export_results["export"] = {"status": "error", "message": f"Export failed: {str(e)}"}
        
        if export_sarif:
            try:
                sarif_path = export_sarif
                export_result = export_report(None, sarif_path, "sarif", results)
                export_results["sarif"] = export_result
            except Exception as e:
                export_results["sarif"] = {"status": "error", "message": f"SARIF export failed: {str(e)}"}
        
        # 返回成功结果
        result_data = {
            "report": report_path,
            "fix_script": fix_path,
            "meta": meta,
            "risks": results["risks"]
        }
        
        # 添加模拟结果
        if simulation_results:
            result_data["simulation"] = simulation_results
        
        # 添加策略审计结果
        if policy_audit:
            result_data["policy_audit"] = policy_audit
        
        # 添加导出结果
        if export_results:
            result_data["exports"] = export_results
        
        return {
            "status": "success",
            "exit_code": 0,
            "data": result_data
        }
        
    except Exception as e:
        # 捕获未预期的错误
        return {
            "status": "error",
            "exit_code": 4,
            "error": {
                "type": "RuntimeError",
                "message": f"Unexpected error: {str(e)}",
                "details": {"error": str(e)}
            }
        }

def build_parser():
    p = argparse.ArgumentParser(prog="leakage-buster", description="Time leakage & fold auditor")
    sub = p.add_subparsers(dest="cmd")
    run_p = sub.add_parser("run", help="Run audit")
    run_p.add_argument("--train", type=str, required=True, help="Training data CSV file")
    run_p.add_argument("--target", type=str, required=True, help="Target column name")
    run_p.add_argument("--time-col", type=str, default=None, help="Time column name (optional)")
    run_p.add_argument("--cv-type", type=str, choices=["kfold", "timeseries", "group"], default=None, 
                       help="CV strategy: kfold/timeseries/group")
    run_p.add_argument("--simulate-cv", type=str, choices=["time"], default=None,
                       help="Enable time series simulation: time")
    run_p.add_argument("--leak-threshold", type=float, default=0.02,
                       help="Leak threshold for simulation (default: 0.02)")
    run_p.add_argument("--cv-policy-file", type=str, default=None,
                       help="CV policy configuration file (YAML)")
    run_p.add_argument("--export", type=str, choices=["pdf"], default=None,
                       help="Export report format: pdf")
    run_p.add_argument("--export-sarif", type=str, default=None,
                       help="Export SARIF file path for GitHub Code Scanning")
    run_p.add_argument("--out", type=str, required=True, help="Output directory")
    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if args.cmd == "run" or (args.cmd is None and hasattr(args, "train")):
        result = run(args.train, args.target, args.time_col, args.out, 
                    args.cv_type, args.simulate_cv, args.leak_threshold,
                    args.cv_policy_file, args.export, args.export_sarif)
        
        # 输出JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 设置退出码
        sys.exit(result["exit_code"])
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

