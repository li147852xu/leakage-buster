
from __future__ import annotations
import argparse, os, json
import pandas as pd
from .core.checks import run_checks
from .core.report import render_report, write_fix_script, write_meta

def run(train_path: str, target: str, time_col: str | None, out_dir: str, cv_type: str | None = None):
    df = pd.read_csv(train_path)
    results = run_checks(df, target=target, time_col=time_col, cv_type=cv_type)
    meta = {
        "args": {"train": train_path, "target": target, "time_col": time_col, "out": out_dir, "cv_type": cv_type},
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "target": target,
        "time_col": time_col,
        "cv_type": cv_type,
    }
    os.makedirs(out_dir, exist_ok=True)
    write_meta(meta, out_dir)
    report_path = render_report(results, meta, out_dir)
    fix_path = write_fix_script(results, out_dir)
    return {"report": report_path, "fix_script": fix_path}

def build_parser():
    p = argparse.ArgumentParser(prog="leakage-buster", description="Time leakage & fold auditor")
    sub = p.add_subparsers(dest="cmd")
    run_p = sub.add_parser("run", help="Run audit")
    run_p.add_argument("--train", type=str, required=True)
    run_p.add_argument("--target", type=str, required=True)
    run_p.add_argument("--time-col", type=str, default=None)
    run_p.add_argument("--cv-type", type=str, choices=["kfold", "timeseries", "group"], default=None, 
                       help="CV strategy: kfold/timeseries/group")
    run_p.add_argument("--out", type=str, required=True)
    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "run" or (args.cmd is None and hasattr(args, "train")):
        paths = run(args.train, args.target, args.time_col, args.out, args.cv_type)
        print(json.dumps(paths, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

