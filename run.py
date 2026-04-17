#!/usr/bin/env python3
"""
Software Self-Improvement - Pure Python (no dependencies)

Uses only stdlib: json, subprocess, pathlib, argparse
"""

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILL_DIR = Path(__file__).parent
RESOURCES_DIR = SKILL_DIR / "resources"
SCRIPTS_DIR = RESOURCES_DIR / "scripts"
PROMPTS_DIR = RESOURCES_DIR / "prompts"

# Default config (JSON format, no yaml needed)
DEFAULT_CONFIG = {
    "target": {"type": "folder", "location": "./"},
    "rounds": 3,
    "overall_target": 85,
    "dimension_target": 85,
    "early_stop": {"enabled": True},
    "git": {"commit_per_round": True, "branch": "quality/auto-research", "push": False},
    "reporting": {"output_dir": "reports", "formats": ["markdown", "json"]},
    "dimensions": {
        "linting": {"enabled": True, "weight": 0.10, "tools": ["ruff", "eslint"]},
        "type_safety": {"enabled": True, "weight": 0.15, "tools": ["mypy", "pyright"]},
        "test_coverage": {"enabled": True, "weight": 0.20, "tools": ["pytest-cov"]},
        "security": {"enabled": True, "weight": 0.15, "tools": ["bandit", "semgrep"]},
        "performance": {"enabled": True, "weight": 0.10, "tools": ["radon-cc"]},
        "architecture": {"enabled": True, "weight": 0.10, "tools": []},
        "readability": {"enabled": True, "weight": 0.10, "tools": ["radon-mi"]},
        "error_handling": {"enabled": True, "weight": 0.05, "tools": []},
        "documentation": {"enabled": True, "weight": 0.05, "tools": ["interrogate"]}
    }
}


def load_config(config_path: Optional[str] = None) -> Dict:
    """Load configuration from JSON."""
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    
    config = DEFAULT_CONFIG.copy()
    
    # Normalize weights
    dims = config.get("dimensions", {})
    total = sum(d.get("weight", 0) for d in dims.values() if d.get("enabled", True))
    for name, dim in dims.items():
        if dim.get("enabled", True):
            dim["normalized_weight"] = dim.get("weight", 0) / total if total > 0 else 0
    
    return config


def setup_target(config: Dict) -> str:
    """Setup target folder or clone GitHub repo."""
    target_type = config.get("target", {}).get("type", "folder")
    location = config.get("target", {}).get("location", "./")
    workdir = ".sessi-work/target"
    
    if target_type == "github":
        Path(workdir).mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", location, workdir], 
                     capture_output=True)
        return workdir
    else:
        if os.path.isdir(location):
            return location
        raise ValueError(f"Target folder not found: {location}")


def run_cmd(cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
    """Run shell command."""
    return subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=cwd or os.getcwd()
    )


def run_tool(tool: str, target_path: str) -> Dict:
    """Run a quality tool and return results."""
    commands = {
        "ruff": (["ruff", "check", ".", "--output-format", "json"], "json"),
        "eslint": (["npx", "eslint", ".", "--format", "json"], "json"),
        "prettier": (["npx", "prettier", "--check", "."], "text"),
        "mypy": (["mypy", "."], "text"),
        "pyright": (["pyright"], "json"),
        "bandit": (["bandit", "-q", "-r", ".", "-f", "json"], "json"),
        "semgrep": (["semgrep", "--config", "auto", "--json"], "json"),
        "pytest-cov": (["pytest", "--cov", "--cov-report=json"], "json"),
        "pytest": (["pytest", "--tb=no", "-q"], "text"),
        "radon-cc": (["radon", "cc", "-s", "-j", "."], "json"),
        "radon-mi": (["radon", "mi", "-j", "."], "json"),
        "interrogate": (["interrogate", "-q"], "text"),
    }
    
    if tool not in commands:
        return {"score": 50, "output": "", "error": "unknown tool"}
    
    cmd, fmt = commands[tool]
    proc = run_cmd(cmd, target_path)
    
    return {
        "returncode": proc.returncode,
        "output": proc.stdout[:1000],  # Truncate
        "error": proc.stderr[:500] if proc.stderr else ""
    }


def calculate_score(dimension: str, tool_results: Dict, dim_config: Dict) -> int:
    """Calculate score from tool results."""
    scores = {"default": 50}
    
    if dimension == "linting":
        # ruff/eslint: count errors
        total = 0
        for tr in tool_results.values():
            if isinstance(tr, dict):
                # Try parse JSON output
                try:
                    data = json.loads(tr.get("output", "[]"))
                    if isinstance(data, list):
                        total += len(data)
                except:
                    pass
        scores["linting"] = max(0, 100 - total * 3)
    
    elif dimension == "type_safety":
        # mypy/pyright: count type errors
        for name, tr in tool_results.items():
            if name in ["mypy", "pyright"] and tr.get("returncode", 0) != 0:
                scores["type_safety"] = 40
                break
        else:
            scores["type_safety"] = 85
    
    elif dimension == "test_coverage":
        # pytest-cov: extract percentage
        for tr in tool_results.values():
            if isinstance(tr, dict) and "output" in tr:
                match = re.search(r"TOTAL.*?(\d+)%", tr["output"])
                if match:
                    scores["test_coverage"] = int(match.group(1))
                    break
    
    elif dimension == "security":
        # bandit/semgrep: critical findings
        critical = 0
        for tr in tool_results.values():
            if isinstance(tr, dict):
                try:
                    data = json.loads(tr.get("output", "[]"))
                    if isinstance(data, list):
                        critical += len([x for x in data if x.get("issue_severity") in ["ERROR", "HIGH"]])
                except:
                    pass
        scores["security"] = max(0, 100 - critical * 15)
    
    elif dimension == "readability":
        # radon-mi: 0-100 scale
        for tr in tool_results.values():
            if isinstance(tr, dict) and "output" in tr:
                match = re.search(r"(\d+)\.", tr["output"])
                if match:
                    scores["readability"] = int(match.group(1))
                    break
    
    elif dimension == "documentation":
        # interrogate: coverage percentage
        for tr in tool_results.values():
            if "interrogate" in str(tr) and tr.get("output"):
                match = re.search(r"(\d+)%", tr["output"])
                if match:
                    scores["documentation"] = int(match.group(1))
                    break
    
    return scores.get(dimension, scores["default"])


def evaluate_dimension(target_path: str, config: Dict, dimension: str) -> Dict:
    """Evaluate one dimension."""
    dim_config = config.get("dimensions", {}).get(dimension, {})
    tools = dim_config.get("tools", [])
    
    result = {"dimension": dimension, "score": 50, "findings": [], "tool_outputs": {}}
    
    # Run tools
    tool_results = {}
    for tool in tools:
        if run_tool(tool, target_path).get("returncode", 0) is not None:
            tool_results[tool] = run_tool(tool, target_path)
    
    # Calculate score
    result["score"] = calculate_score(dimension, tool_results, dim_config)
    result["tool_outputs"] = {k: v.get("output", "")[:200] for k, v in tool_results.items()}
    
    return result


def calculate_overall(scores: Dict, config: Dict) -> Dict:
    """Calculate weighted overall score."""
    dimensions = config.get("dimensions", {})
    weighted = 0
    total = 0
    
    for name, dim in dimensions.items():
        if dim.get("enabled", True) and name in scores:
            w = dim.get("normalized_weight", 0)
            weighted += scores[name] * w
            total += w
    
    overall = int(weighted * 100) if total > 0 else 0
    target = config.get("overall_target", 85)
    
    failing = [
        name for name, score in scores.items()
        if score < dimensions.get(name, {}).get("target", target)
    ]
    
    return {
        "overall": overall,
        "meets_target": overall >= target and not failing,
        "failing_dimensions": failing
    }


def run_quality_round(target_path: str, config: Dict, round_num: int) -> Dict:
    """Run one quality improvement round."""
    print(f"\n{'='*50}")
    print(f"🔄 Round {round_num}")
    print(f"{'='*50}")
    
    scores = {}
    dimensions = config.get("dimensions", {})
    
    # Evaluate each enabled dimension
    for dim_name, dim_cfg in dimensions.items():
        if not dim_cfg.get("enabled", True):
            continue
        
        print(f"  📊 Evaluating: {dim_name}")
        result = evaluate_dimension(target_path, config, dim_name)
        scores[dim_name] = result["score"]
        print(f"     Score: {result['score']}")
    
    # Calculate overall
    overall = calculate_overall(scores, config)
    scores["overall"] = overall["overall"]
    
    print(f"\n  📈 Overall: {overall['overall']} (target: {config.get('overall_target', 85)})")
    
    if overall["meets_target"]:
        print(f"✅ Early stop: targets met!")
        return {"round": round_num, "scores": scores, "meets_target": True, "early_stop": True}
    
    return {
        "round": round_num,
        "scores": scores,
        "overall": overall["overall"],
        "meets_target": False,
        "failing": overall["failing_dimensions"]
    }


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def generate_report(results: List[Dict], config: Dict) -> str:
    """Generate final report."""
    if not results:
        return "No results"
    
    lines = ["# Quality Improvement Report", "", "## Summary", "", "| Round | Overall | Meets Target |", "|-------|---------|------------|"]
    
    for r in results:
        meets = "✅" if r.get("meets_target") else "❌"
        lines.append(f"| {r['round']} | {r.get('overall', r.get('scores', {}).get('overall', 0))} | {meets} |")
    
    # Deltas
    if len(results) >= 2:
        first = results[0].get("overall", 0)
        last = results[-1].get("overall", 0)
        delta = last - first
        lines.extend(["", f"## Change", f"- Overall: {first} → {last} ({delta:+d})"])
    
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    """Main execution."""
    print("🚀 Software Self-Improvement")
    print("=" * 50)
    
    # Load config
    config = load_config(args.config)
    config["rounds"] = args.rounds
    config["overall_target"] = args.overall_target
    
    print(f"Target: {args.target}")
    print(f"Rounds: {args.rounds}")
    print(f"Overall target: {args.overall_target}")
    
    # Setup target
    target_path = setup_target(config)
    print(f"📁 Target: {target_path}")
    
    # Run rounds
    ensure_dir("reports")
    ensure_dir(".sessi-work/scores")
    
    all_results = []
    
    for round_num in range(1, args.rounds + 1):
        result = run_quality_round(target_path, config, round_num)
        all_results.append(result)
        
        if result.get("early_stop") and config.get("early_stop", {}).get("enabled", True):
            break
    
    # Generate report
    report = generate_report(all_results, config)
    with open("reports/FINAL.md", "w") as f:
        f.write(report)
    
    print("\n" + "=" * 50)
    print("✅ Complete!")
    print("📁 Reports: reports/FINAL.md")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Software Self-Improvement (no dependencies)")
    parser.add_argument("--target", default="./", help="Target folder or GitHub URL")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rounds")
    parser.add_argument("--overall-target", type=int, default=85, help="Overall target")
    parser.add_argument("--config", help="Path to config.json")
    
    args = parser.parse_args()
    
    try:
        return run(args)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())