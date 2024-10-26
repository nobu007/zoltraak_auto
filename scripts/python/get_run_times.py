import json
import os
import subprocess
from datetime import datetime

from pydantic import BaseModel, Field


class StepDuration(BaseModel):
    step_name: str
    duration: float


class JobDuration(BaseModel):
    # TODO: implement
    job_name: str
    duration: float
    steps: list[StepDuration] = Field(default_factory=list)


class RunDuration(BaseModel):
    run_id: int
    run_number: int
    step_durations: list[StepDuration] = Field(default_factory=list)


class RunData(BaseModel):
    job_id: str = "unknown_id"  # TODO: 必要なら追加
    job_name: str = "unknown_name"  # TODO: 必要なら追加
    run_durations: list[RunDuration] = Field(default_factory=list)


class GitHubActionsAnalyzer:
    def __init__(self):
        self.github_org = os.getenv("GITHUB_ORG", "nobu007")
        self.github_project = os.getenv("GITHUB_PROJECT", "zoltraak_auto")
        self.workflow_file = os.getenv("WORKFLOW_FILE", "integration-tests.yml")
        self.branch_name = os.getenv("BRANCH_NAME", "main")
        self.job_name = os.getenv("JOB_NAME", "integration-tests")
        self.step_filters = os.getenv("STEP_FILTERS", "test_performance_first_run,test_performance_second_run")
        self.page_limit = int(os.getenv("PAGE_LIMIT", "3"))
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
        # 注意: 自身のjob(実行中)は正しく取れない。jobをテスト用と計測用に分けること
        if not job["started_at"] or not job["completed_at"]:
            return -1.0

        start_time = self._get_datetime(job["started_at"])
        complete_time = self._get_datetime(job["completed_at"])
        return (complete_time - start_time).total_seconds()

    def _calculate_step_duration(self, job: dict, step_filter: str) -> float:
        """ステップの実行時間を計算"""
        # 注意: jobに複数のstepがある場合、最初に見つかったstepの時間を返す
        for step in job["steps"]:
            if step_filter in step["name"]:
                start_time = datetime.fromisoformat(step["started_at"].replace("Z", "+00:00"))
                complete_time = datetime.fromisoformat(step["completed_at"].replace("Z", "+00:00"))
                return (complete_time - start_time).total_seconds()
        return -1.0

    def add_step_durations(self, job: dict, run_duration: RunDuration) -> None:
        for step_filter in self.step_filters.split(","):
            duration = self._calculate_step_duration(job, step_filter)
            if duration >= 0:
                run_duration.step_durations.append(StepDuration(step_name=step_filter, duration=duration))

    def get_run_data(self) -> RunData:
        """ワークフローの実行データを取得
        戻り値: (run_number, 実行時間)のリスト
        """
        run_data = RunData()

        for page in range(1, self.page_limit + 1):
            runs = self._call_github_api(f"actions/runs?branch={self.branch_name}&per_page=10&page={page}")

            for run in runs["workflow_runs"]:
                if run["path"] != f".github/workflows/{self.workflow_file}":
                    continue

                run_id = run["id"]
                run_number = run["run_number"]
                run_duration = RunDuration(run_id=run_id, run_number=run_number)
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
                        self.add_step_durations(job, run_duration)
                        run_data.run_durations.append(run_duration)
                        break

        return run_data

    def generate_chart(self, run_data: RunData, file_path: str = "chart.md") -> None:
        """Mermaidチャートを生成"""
        chart_content = ""

        if len(run_data.run_durations) == 0:
            return

        # データ構造を変更
        # 元: run_duration → step_duration → step_name, duration
        # 後: step_name → list[duration]
        step_name_list = []
        run_duration = run_data.run_durations[0]
        for step_duration in run_duration.step_durations:
            step_name_list.append(step_duration.step_name)  # noqa: PERF401

        # step_nameごとに１つのグラフを作る
        for step_name in step_name_list:
            times = []
            labels = []

            for run_duration in run_data.run_durations:
                labels.append("#" + str(run_duration.run_number))
                for step_duration in run_duration.step_durations:
                    if step_duration.step_name == step_name:
                        # step_nameに対応するdurationを追加
                        times.append(str(step_duration.duration))
                        break

            # データがない場合はスキップ(全部ジョブを中断した場合など)
            if len(times) == 0:
                continue

            chart_content += f"""```mermaid
xychart-beta
title "Integration Test({step_name}) Job Execution Time[sec]"
x-axis [{', '.join(labels)}]
y-axis "Seconds"
line [{', '.join(times)}]
```
"""

            print(f"Generating chart for {step_name}")

        # 複数のグラフを１つのファイルに書き込む
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(chart_content)


def main():
    analyzer = GitHubActionsAnalyzer()
    run_data = analyzer.get_run_data()
    analyzer.generate_chart(run_data)


if __name__ == "__main__":
    main()
