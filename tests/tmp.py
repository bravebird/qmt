import pyautogui
import time
from pywinauto import Application


class WindowImageFinder:
    def __init__(self, image_path):
        self.image_path = image_path
        self.app = None
        self.window = None

    def find_window(self):
        # Locate the window on screen based on the provided image
        window_location = pyautogui.locateOnScreen(self.image_path)
        if not window_location:
            raise Exception(f"No window found matching the image: {self.image_path}")

            # Click on the located window to bring it to the foreground
        pyautogui.click(window_location)
        time.sleep(1)  # Wait for the window to come to the foreground

        # Connect to the window using pywinauto
        windows = Application(backend="uia").top_window()
        self.app = Application(backend="uia").connect(handle=windows.handle)
        self.window = self.app.window(handle=windows.handle)

    def bring_window_to_top(self):
        if self.window:
            try:
                self.window.set_focus()
            except Exception as e:
                raise Exception(f"Failed to bring window to top: {e}")
        else:
            raise Exception("Window not found. Make sure to call find_window() first.")

    def find_and_click_button(self, button_text):
        """查找指定文本的按钮并点击"""
        if not self.window:
            raise Exception("Window is not set. Make sure to call find_window() and bring_window_to_top() first.")

        try:
            button = self.window.child_window(title=button_text, control_type="Button")
            if button.exists(timeout=5):
                button.click_input()
                print("Button clicked!")
            else:
                raise Exception(f"Button with text '{button_text}' not found!")
        except Exception as e:
            raise Exception(f"Button with text '{button_text}' not found: {e}")

    def find_and_click_image_button(self, button_image_path, timeout=10):
        """查找图形按钮并点击"""
        if not self.window:
            raise Exception("Window is not set. Make sure to call find_window() and bring_window_to_top() first.")

        try:
            # Locate the button image on screen
            button_location = pyautogui.locateOnScreen(button_image_path)
            if button_location:
                pyautogui.click(button_location)
                print("Image button clicked!")
            else:
                raise Exception(f"Image button not found with path '{button_image_path}'.")
        except Exception as e:
            raise Exception(f"Image button with path '{button_image_path}' not found: {e}")

        # 示例用法


if __name__ == "__main__":
    try:
        # 创建图像窗口查找器对象，传入窗口截图图像
        finder = WindowImageFinder("window_image.png")

        # 查找窗口
        finder.find_window()

        # 将窗口置顶
        finder.bring_window_to_top()

        # 查找并点击文本按钮
        finder.find_and_click_button("Click Me")

        # 查找并点击图形按钮
        finder.find_and_click_image_button("button_image.png")
    except Exception as e:
        print(e)