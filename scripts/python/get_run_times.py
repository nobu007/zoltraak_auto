import json
import os
import subprocess
from datetime import datetime


class GitHubActionsAnalyzer:
    def __init__(self):
        self.github_org = os.getenv("GITHUB_ORG", "nobu007")
        self.github_project = os.getenv("GITHUB_PROJECT", "zoltraak_auto")
        self.workflow_file = os.getenv("WORKFLOW_FILE", "integration-tests.yml")
        self.branch_name = os.getenv("BRANCH_NAME", "main")
        self.job_name = os.getenv("JOB_NAME", "integration-tests")
        self.step_filter = os.getenv("STEP_FILTER", "integration")
        self.page_limit = int(os.getenv("PAGE_LIMIT", "10"))
        self.cache_dir = "cache"

        # キャッシュディレクトリの作成
        os.makedirs(self.cache_dir, exist_ok=True)

    def _call_github_api(self, path: str) -> dict:
        """GitHub APIを呼び出す"""
        cmd = ["gh", "api", f"https://api.github.com/repos/{self.github_org}/{self.github_project}/{path}"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)  # noqa: S603
        return json.loads(result.stdout)

    def _get_datetime(self, time_str: str) -> datetime:
        """ISO形式の時間文字列をdatetimeオブジェクトに変換"""
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

    def _calculate_job_duration(self, job: dict) -> float:
        """ジョブの合計実行時間を計算"""
        if not job["started_at"] or not job["completed_at"]:
            return -1.0

        start_time = self._get_datetime(job["started_at"])
        complete_time = self._get_datetime(job["completed_at"])
        return (complete_time - start_time).total_seconds()

    def get_run_data(self) -> list[tuple[str, float]]:
        """ワークフローの実行データを取得"""
        run_data = []
        run_number = 0

        for page in range(1, self.page_limit + 1):
            runs = self._call_github_api(f"actions/runs?branch={self.branch_name}&per_page=100&page={page}")

            for run in runs["workflow_runs"]:
                if run["path"] != f".github/workflows/{self.workflow_file}":
                    continue

                run_number += 1
                run_id = run["id"]
                cache_file = os.path.join(self.cache_dir, f"{run_id}.json")

                try:
                    with open(cache_file, encoding="utf-8") as f:
                        job_data = json.load(f)
                        print(f"Cache hit: {cache_file}")
                except FileNotFoundError:
                    job_data = self._call_github_api(f"actions/runs/{run_id}/jobs")
                    print(f"Cache miss: Fetched data for run {run_id}")
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(job_data, f, indent=2)

                for job in job_data["jobs"]:
                    if job["name"] == self.job_name:
                        duration = self._calculate_job_duration(job)
                        if duration >= 0:
                            run_data.append((f"#{run_number}", duration))
                        break

        return run_data

    def generate_chart(self, run_data: list[tuple[str, float]], file_path: str = "chart.md") -> None:
        """Mermaidチャートを生成"""
        times = [str(int(duration)) for _, duration in run_data]
        labels = [label for label, _ in run_data]

        chart_content = f"""```mermaid
xychart-beta
title "Integration Test Job Execution Time[sec]"
x-axis [{', '.join(labels)}]
y-axis "Seconds"
line [{', '.join(times)}]
```"""

        print(f"Generating chart with {len(run_data)} data points")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(chart_content)


def main():
    analyzer = GitHubActionsAnalyzer()
    run_data = analyzer.get_run_data()
    analyzer.generate_chart(run_data)


if __name__ == "__main__":
    main()
