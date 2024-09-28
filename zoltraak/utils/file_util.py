class FileUtil:
    @staticmethod
    def read_file(file_path: str) -> str:
        # ターゲットファイルの現在の内容を読み込む
        with open(file_path, encoding="utf-8") as file:
            return file.read()
        return f"{file_path} を開けませんでした。"

    @staticmethod
    def write_file(file_path: str, content: str) -> str:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
            return file_path
        return ""

    # pyautogui版は封印（importチェックすれば使えると思う）
    # @staticmethod
    # def can_use_gui() -> bool:
    #     try:
    #         # マウスの位置を取得してみる
    #         _, _ = pyautogui.position()
    #         return True
    #     except Exception as e:
    #         print("GUI環境が利用できません:", e)
    #     return False
