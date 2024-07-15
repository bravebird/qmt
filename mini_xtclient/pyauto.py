import re
from pywinauto import Application, findwindows
from pywinauto.findwindows import ElementNotFoundError
import win32gui
import win32con
import pyautogui
import time
import ctypes

# 检查并导入 OpenCV
try:
    import cv2
except ImportError:
    raise ImportError("OpenCV 无法导入。请安装它，命令为 'pip install opencv-python'")

# 配置日志记录器
from loggers import logger


class WindowRegexFinder:
    def __init__(self, regex_pattern: str):
        self.regex_pattern = regex_pattern
        self.app = None
        self.window = None
        self.handle = None

    def get_scaling_factor(self):
        # 获取 Windows 的 DPI 缩放系数
        dpi_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
        logger.debug(f"DPI 缩放系数: {dpi_scale}")
        return dpi_scale

    def find_window(self) -> None:
        try:
            # 使用正则表达式查找与窗口标题匹配的所有窗口
            windows = findwindows.find_windows(title_re=self.regex_pattern)
            if windows:
                self.handle = windows[0]
                logger.debug(f"找到窗口句柄: {self.handle}")
                self.app = Application(backend="uia").connect(handle=self.handle)
                self.window = self.app.window(handle=self.handle)
            else:
                raise Exception(f"未找到符合模式的窗口: {self.regex_pattern}")
        except ElementNotFoundError as e:
            raise Exception(f"查找窗口失败: {e}")

    def bring_window_to_top(self) -> None:
        if not self.handle:
            raise Exception("未找到窗口句柄。请先调用 find_window() 方法。")

        try:
            win32gui.SetForegroundWindow(self.handle)
            win32gui.ShowWindow(self.handle, win32con.SW_NORMAL)
            self.app = Application(backend="uia").connect(handle=self.handle)
            self.window = self.app.window(handle=self.handle)
            logger.debug(f"窗口 {self.handle} 已置顶并聚焦。")
        except Exception as e:
            raise Exception(f"无法将窗口置顶或连接：{e}")

    def find_and_click_button(self, button_text: str) -> None:
        """通过文本查找并点击按钮"""
        if not self.window:
            raise Exception("未设置窗口。请先调用 find_window() 和 bring_window_to_top() 方法。")

        try:
            button = self.window.child_window(title=button_text, control_type="Button")
            if button.exists(timeout=5):
                button.click_input()
                logger.debug("按钮点击成功！")
            else:
                raise Exception(f"未找到文本为 '{button_text}' 的按钮！")
        except ElementNotFoundError as e:
            raise Exception(f"未找到文本为 '{button_text}' 的按钮：{e}")

    def find_and_click_image_button(self, image_path: str) -> None:
        """通过图像查找并点击按钮"""


        logger.debug(f"查找路径 {image_path} 中的按钮图像")

        try:
            # 确保图像加载正确
            image = cv2.imread(image_path)
            if image is None:
                raise Exception(f"图像未加载。检查路径: {image_path}")

            # 获取系统 DPI 缩放系数
            scaling_factor = self.get_scaling_factor()

            # 使用调整后的缩放系数在屏幕上定位按钮
            button_location = pyautogui.locateOnScreen(image_path, confidence=0.8)
            logger.debug(f"原始按钮位置: {button_location}")

            if button_location:
                button_point = pyautogui.center(button_location)
                pyautogui.moveTo(button_point)  # 不进行缩放调整
                logger.debug(f"移动到按钮位置 (未缩放): {button_point}")
                time.sleep(5)  # 暂停以验证位置是否正确
                pyautogui.click()
                logger.debug("图像按钮点击成功！")
            else:
                raise Exception(f"屏幕上未找到按钮。图像路径: {image_path}")
        except Exception as e:
            logger.exception(f"点击图像按钮时出错：{e}")


if __name__ == "__main__":
    try:
        # 创建一个基于正则表达式的窗口查找对象，传递一个正则表达式模式
        finder = WindowRegexFinder(r"e海方舟-量化交易版[.\d ]+")

        # 查找窗口句柄
        finder.find_window()

        # 将窗口置顶
        finder.bring_window_to_top()

        # 查找并点击图像按钮
        finder.find_and_click_image_button("../config/login_button.PNG")
    except Exception as e:
        logger.error(e)
