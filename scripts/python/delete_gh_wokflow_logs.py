import json
import subprocess
import time

# GitHubリポジトリ情報
owner = "nobu007"
repo = "zoltraak_auto"

# 全てのワークフロー実行IDを取得し、削除する
try:
    run_ids = []
    page = 1
    while True:
        # ページごとに実行履歴を取得
        result = subprocess.run(  # noqa: S603
            ["gh", "api", f"repos/{owner}/{repo}/actions/runs", "-page=1", "-per_page=10"],  # noqa: S607, S603
            capture_output=True,
            text=True,
            check=True,
        )

        # JSONレスポンスを解析
        workflow_data = json.loads(result.stdout)
        if "workflow_runs" not in workflow_data or not workflow_data["workflow_runs"]:
            break  # 次のページがない場合は終了

        # 各ページの実行IDをリストに追加
        run_ids = []
        run_ids.extend([run["id"] for run in workflow_data["workflow_runs"]])

        # 各ワークフロー実行の削除
        for run_id in run_ids:
            print(f"Deleting workflow run ID: {run_id}")
            delete_cmd = ["gh", "api", f"repos/{owner}/{repo}/actions/runs/{run_id}", "-X", "DELETE"]
            subprocess.run(delete_cmd, check=True)  # noqa: S603
            print(f"Deleted workflow run ID: {run_id}")
        page += 1
        print("page=", page)
        time.sleep(10)

except subprocess.CalledProcessError as e:
    print(f"Subprocess error: {e}")
except json.JSONDecodeError:
    print("Error decoding JSON from GitHub API response")
except subprocess.SubprocessError as e:
    print(f"Subprocess error: {e}")
except Exception as e:  # noqa: BLE001
    print(f"Unexpected error: {e}")
