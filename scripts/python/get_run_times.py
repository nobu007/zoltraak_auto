import json
import os
import subprocess
from datetime import datetime

# 環境変数から設定値を取得
GITHUB_ORG = os.getenv("GITHUB_ORG", "nobu007")
GITHUB_PROJECT = os.getenv("GITHUB_PROJECT", "zoltraak_auto")
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "integration-tests.yml")
BRANCH_NAME = os.getenv("BRANCH_NAME", "main")
JOB_NAME = os.getenv("JOB_NAME", "integration-tests")
STEP_FILTER = os.getenv("STEP_FILTER", "integration")
PAGE_LIMIT = int(os.getenv("PAGE_LIMIT", "10"))  # ページ数を環境変数で設定可能


# GitHub API呼び出し関数
def _call_github_api(path: str) -> dict:
    # URL例: https://api.github.com/repos/nobu007/zoltraak_auto/actions/runs?branch=main&per_page=100&page=1
    cmd = ["gh", "api", f"https://api.github.com/repos/{GITHUB_ORG}/{GITHUB_PROJECT}/{path}"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)  # noqa: S603
    return json.loads(result.stdout)


# 実行時間の取得関数
def get_run_times() -> list[float]:
    run_ids = []
    for i in range(1, PAGE_LIMIT + 1):  # ページ数は環境変数で調整可能
        runs_data = _call_github_api(f"actions/runs?branch={BRANCH_NAME}&per_page=100&page={i}")
        for run in runs_data["workflow_runs"]:
            if run["path"] == f".github/workflows/{WORKFLOW_FILE}":
                run_ids.append(run["id"])  # noqa: PERF401

    times = []
    for run_id in run_ids:
        try:
            with open(f"{run_id}.json", encoding="utf-8") as f:
                job_data = json.load(f)
                print(f"{run_id}.json loaded")
        except FileNotFoundError:
            job_data = _call_github_api(f"actions/runs/{run_id}/jobs")
            print(f"actions/runs/{run_id}/jobs loaded")
            with open(f"{run_id}.json", "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2)
                print(f"{run_id}.json saved")

        for job in job_data["jobs"]:
            if job["name"] == JOB_NAME:
                for step in job["steps"]:
                    if STEP_FILTER in step["name"]:
                        start_time = datetime.fromisoformat(step["started_at"].replace("Z", "+00:00"))
                        complete_time = datetime.fromisoformat(step["completed_at"].replace("Z", "+00:00"))
                        duration = (complete_time - start_time).total_seconds()
                        times.append(duration)
    return times


# Mermaidチャート生成関数
def generate_chart(times: list[float], file_path: str = "chart.md") -> str:
    chart_content = _generate_chart_content(times)
    _store_chart(chart_content, file_path)


def _generate_chart_content(times: list[float]) -> str:
    data = ", ".join([str(int(t)) for t in times if t != 0])
    chart_content = f"""```mermaid
xychart-beta
line [{data}]
```
"""
    print("generate_chart chart_content len=", len(chart_content))
    return chart_content


def _store_chart(chart_content: str, file_path: str) -> None:
    print("store_chart file_path=", file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(chart_content)


# 実行
if __name__ == "__main__":
    times_ = get_run_times()
    generate_chart(times_)
