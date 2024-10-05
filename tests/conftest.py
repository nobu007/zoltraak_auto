# conftest.py(tests)

# 失敗したテストの行数をFAILURES WITH LINE NUMBERSに追加表示するカスタムプラグイン
def pytest_terminal_summary(terminalreporter):
    reports = terminalreporter.getreports("failed")
    if reports:
        terminalreporter.section("FAILURES WITH LINE NUMBERS")
        for report in reports:
            file_name = report.location[0]
            line_number = report.location[1] + 1  # 行数(シンプルな数値)、1行ずれるので修正して使う
            test_name = report.nodeid.split("::")[-1]
            terminalreporter.line(f"FAILED {file_name}:{line_number} <=(click to jump) {test_name}")


# 実験中
def summary_failures(self):
    if self.config.option.tbstyle != "no":
        self.write_sep("=", "custom short test summary info")
        for rep in self.stats.get("failed", []):
            file_name = rep.location[0]
            line_number = rep.location[1]
            test_name = rep.nodeid.split("::")[-1]
            self.write_line(f"FAILED {file_name}::{test_name}::{line_number}")
