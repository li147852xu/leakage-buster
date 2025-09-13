
from __future__ import annotations
import argparse, os, json, sys
import pandas as pd
from .core.checks import run_checks
from .core.report import render_report, write_fix_script, write_meta
from .core.simulator import run_time_series_simulation
from .core.cv_policy import audit_cv_policy
from .core.export import export_report
from .core.fix_plan import create_fix_plan, save_fix_plan
from .core.fix_apply import apply_minimal_fixes
from .api import audit, AuditResult

def run(train_path: str, target: str, time_col: str | None, out_dir: str, cv_type: str | None = None, 
        simulate_cv: str | None = None, leak_threshold: float = 0.02, cv_policy_file: str | None = None,
        export: str | None = None, export_sarif: str | None = None, auto_fix: str | None = None,
        fix_json: str | None = None, fixed_train: str | None = None):
    """运行泄漏检测 - v0.5-rc版本"""
    try:
        # 验证输入文件
        if not os.path.exists(train_path):
            return {
                "status": "error",
                "exit_code": 4,  # invalid-config
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
                "exit_code": 4,  # invalid-config
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
                "exit_code": 4,  # invalid-config
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
                "exit_code": 4,  # invalid-config
                "error": {
                    "type": "ValidationError",
                    "message": f"Time column '{time_col}' not found in data",
                    "details": {"column": time_col, "available_columns": list(df.columns)}
                }
            }
        
        # 运行审计
        try:
            audit_result = audit(
                df=df,
                target=target,
                time_col=time_col,
                cv_type=cv_type,
                simulate_cv=(simulate_cv == "time"),
                leak_threshold=leak_threshold,
                cv_policy_file=cv_policy_file
            )
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 4,  # invalid-config
                "error": {
                    "type": "RuntimeError",
                    "message": f"Audit failed: {str(e)}",
                    "details": {"error": str(e)}
                }
            }
        
        # 处理auto-fix
        fix_result = None
        if auto_fix == "plan" and fix_json:
            try:
                fix_plan = create_fix_plan(audit_result.risks)
                save_fix_plan(fix_plan, fix_json)
                fix_result = {
                    "plan_file": fix_json,
                    "plan_id": fix_plan.plan_id,
                    "actions_count": len(fix_plan.actions),
                    "summary": fix_plan.summary
                }
            except Exception as e:
                return {
                    "status": "error",
                    "exit_code": 4,  # invalid-config
                    "error": {
                        "type": "RuntimeError",
                        "message": f"Fix plan generation failed: {str(e)}",
                        "details": {"error": str(e)}
                    }
                }
        
        elif auto_fix == "apply" and fixed_train:
            try:
                df_fixed, fix_result = apply_minimal_fixes(df, audit_result.risks, target, time_col)
                os.makedirs(os.path.dirname(fixed_train), exist_ok=True)
                df_fixed.to_csv(fixed_train, index=False)
                fix_result = {
                    "fixed_file": fixed_train,
                    "removed_columns": fix_result.removed_columns,
                    "warnings": fix_result.warnings
                }
            except Exception as e:
                return {
                    "status": "error",
                    "exit_code": 4,  # invalid-config
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
                "fixed_train": fixed_train
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
        }
        
        # 创建输出目录
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 4,  # invalid-config
                "error": {
                    "type": "FileNotFoundError",
                    "message": f"Failed to create output directory: {str(e)}",
                    "details": {"directory": out_dir, "error": str(e)}
                }
            }
        
        # 生成输出文件
        try:
            write_meta(meta, out_dir)
            report_path = render_report(
                {"risks": audit_result.risks}, 
                meta, 
                out_dir, 
                audit_result.simulation, 
                audit_result.policy_audit
            )
            fix_path = write_fix_script({"risks": audit_result.risks}, out_dir)
        except Exception as e:
            return {
                "status": "error",
                "exit_code": 4,  # invalid-config
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
                export_result = export_report(None, sarif_path, "sarif", {"risks": audit_result.risks})
                export_results["sarif"] = export_result
            except Exception as e:
                export_results["sarif"] = {"status": "error", "message": f"SARIF export failed: {str(e)}"}
        
        # 确定退出码
        exit_code = audit_result.get_exit_code()
        
        # 返回成功结果
        result_data = {
            "report": report_path,
            "fix_script": fix_path,
            "meta": meta,
            "risks": audit_result.risks,
            "exit_code": exit_code
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
        
        # 添加修复结果
        if fix_result:
            result_data["fix_result"] = fix_result
        
        return {
            "status": "success",
            "exit_code": exit_code,
            "data": result_data
        }
        
    except Exception as e:
        # 捕获未预期的错误
        return {
            "status": "error",
            "exit_code": 4,  # invalid-config
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
    run_p.add_argument("--auto-fix", type=str, choices=["plan", "apply"], default=None,
                       help="Auto-fix mode: plan (generate fix plan) or apply (apply minimal fixes)")
    run_p.add_argument("--fix-json", type=str, default=None,
                       help="Fix plan JSON output path (for --auto-fix plan)")
    run_p.add_argument("--fixed-train", type=str, default=None,
                       help="Fixed training data CSV output path (for --auto-fix apply)")
    run_p.add_argument("--out", type=str, required=True, help="Output directory")
    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if args.cmd == "run" or (args.cmd is None and hasattr(args, "train")):
        result = run(args.train, args.target, args.time_col, args.out, 
                    args.cv_type, args.simulate_cv, args.leak_threshold,
                    args.cv_policy_file, args.export, args.export_sarif,
                    args.auto_fix, args.fix_json, args.fixed_train)
        
        # 输出JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 设置退出码
        sys.exit(result["exit_code"])
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

