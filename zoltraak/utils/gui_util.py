import tkinter as tk

import pyperclip


class GuiUtil:
    @staticmethod
    def can_use_gui():
        root = None
        try:
            # Tkinterのウィンドウを作成
            root = tk.Tk()
            root.withdraw()  # ウィンドウを表示しない
            return True
        except Exception:
            return False
        finally:
            # ウィンドウを破棄
            if root:
                root.destroy()

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        if GuiUtil.can_use_gui():
            pyperclip.copy(text)  # クリップボードにコピー
            return True
        return False

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
