import sys
import os
import time
import cv2
import subprocess
# from PySide6 import QtCore
# from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem
from PySide6.QtGui import QIcon, QImage, QPixmap, QColor, QBrush
# from PySide6.QtCore import QThread

from modules import *
from modules.logger import Logger
from modules.worker import Worker

# Set DPI for High DPI displays
os.environ["QT_FONT_DPI"] = "96"

# Constants for inference results
RESULT_OK = "OK"
RESULT_NG = "NG"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Set application title and description
        title = "AI视觉检测系统"
        description = "AI视觉检测系统 V1.0"
        self.setWindowTitle(title)
        self.ui.titleRightInfo.setText(description)

        # Initialize worker
        self.initialize_worker()

        # Setup UI and connections after worker has been initialized
        self.setup_ui()

    def initialize_worker(self):
        """Initialize the worker thread and connect signals."""
        Logger.setup_logging()
        self.worker = Worker()  # Instantiate the worker here
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        # Connect worker signals to slots
        self.worker.run.connect(self.on_worker_run)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.image_process.connect(lambda x: self.show_image(x, self.ui.image_view))
        self.worker.update_status.connect(lambda x: self.show_status(x))
        self.worker.inference_result.connect(lambda x, y: self.show_inference_result(x, y))

        self.worker_thread.start()  # Start the worker thread

    def setup_ui(self):
        """Setup UI components and button connections."""
        self.ui.toggleButton.clicked.connect(lambda: UIFunctions.toggleMenu(self, True))
        # self.ui.settingsTopBtn.clicked.connect(self.openCloseRightBox)

        # SET UI DEFINITIONS
        UIFunctions.uiDefinitions(self)

        # Setup button connections
        button_actions = {
            self.ui.btn_home: self.show_home,
            self.ui.btn_camera: self.show_camera_settings,
            self.ui.btn_setting: self.show_model_settings,
            self.ui.btn_shot: self.worker.start_capture,
            self.ui.btn_predict: self.worker.start_inference,
            self.ui.btn_autoshot: self.worker.start_continuous_capture,
            self.ui.btn_continue: self.worker.start_continuous_inference,
            self.ui.btn_stop: self.stop,
        }

        for button, action in button_actions.items():
            button.clicked.connect(action)

        # Set original page
        self.ui.stackedWidget.setCurrentWidget(self.ui.home)
        self.ui.btn_home.setStyleSheet(UIFunctions.selectMenu(self.ui.btn_home.styleSheet()))
        self.showMaximized()

    def openCloseRightBox(self):
        UIFunctions.toggleRightBox(self, True)

    # def show_splash_screen(self):
    #     """Show the splash screen."""
    #     splash_pix = QPixmap("images/splash.jpg")  # 替换为你的启动画面文件
    #     splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    #     splash.setMask(splash_pix.mask())
    #     splash.show()
    #
    #     # Simulate loading process
    #     for _ in range(5):  # 这里可以根据需要调整加载时间
    #         time.sleep(1)  # 模拟一些加载过程
    #         QApplication.processEvents()  # 处理事件，保持界面响应
    #
    #     splash.finish(self)  # 关闭启动画面

    def show_home(self):
        """Show the home page."""
        self.ui.stackedWidget.setCurrentWidget(self.ui.home)
        self.reset_button_styles(self.ui.btn_home)

    def show_camera_settings(self):
        """Show the camera settings page."""
        self.ui.stackedWidget.setCurrentWidget(self.ui.camera_setting)
        self.reset_button_styles(self.ui.btn_camera)

    def show_model_settings(self):
        """Show the model settings page."""
        self.ui.stackedWidget.setCurrentWidget(self.ui.model_setting)
        self.reset_button_styles(self.ui.btn_setting)

    def reset_button_styles(self, active_button):
        """Reset the styles of buttons and set the active one."""
        for button in (self.ui.btn_home, self.ui.btn_camera, self.ui.btn_setting):
            UIFunctions.resetStyle(self, button.objectName())
        active_button.setStyleSheet(UIFunctions.selectMenu(active_button.styleSheet()))

    def stop(self):
        """Stop the worker and worker thread."""
        self.worker.stop()  # Signal the worker to stop

    def on_worker_run(self):
        """Enable buttons when the worker finishes."""
        self.disable_buttons()

    def on_worker_finished(self):
        """Enable buttons when the worker finishes."""
        self.enable_buttons()

    def disable_buttons(self):
        for button in (self.ui.btn_shot, self.ui.btn_predict, self.ui.btn_autoshot, self.ui.btn_continue):
            button.setDisabled(True)
        self.ui.btn_stop.setEnabled(True)

    def enable_buttons(self):
        for button in (self.ui.btn_shot, self.ui.btn_predict, self.ui.btn_autoshot, self.ui.btn_continue):
            button.setEnabled(True)
        self.ui.btn_stop.setEnabled(True)

    def handle_error(self, message):
        """Handle errors from the worker."""
        # QMessageBox.critical(self, "Error", message)
        pass

    def show_image(self, img_src, label):
        """Display image in a QLabel."""
        if img_src is not None:
            try:
                ih, iw, _ = img_src.shape
                w, h = label.geometry().width(), label.geometry().height()
                # Maintain original aspect ratio
                if iw / w > ih / h:
                    scal = w / iw
                    img_src_ = cv2.resize(img_src, (w, int(scal * ih)))
                else:
                    scal = h / ih
                    img_src_ = cv2.resize(img_src, (int(scal * iw), h))

                frame = cv2.cvtColor(img_src_, cv2.COLOR_BGR2RGB)
                img = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[2] * frame.shape[1],
                             QImage.Format_RGB888)
                label.setPixmap(QPixmap.fromImage(img))
            except Exception as e:
                Logger.log_message(f"Error displaying image: {e}")
        else:
            label.clear()

    def show_status(self, msg):
        """Show status message in a label."""
        self.ui.label_status.setText(msg)
        self.ui.label_status.setStyleSheet("color: black; font-size: 24px;")

    def show_inference_result(self, result_ready, inference_result):
        """Show inference result message in a label and table."""
        self.ui.label_result.setText(result_ready)
        if result_ready == RESULT_OK:
            self.ui.label_result.setStyleSheet("background-color: green; color: white; font-size: 72px;")
        elif result_ready == RESULT_NG:
            self.ui.label_result.setStyleSheet("background-color: red; color: white; font-size: 72px;")
        else:
            self.ui.label_result.setStyleSheet("")  # Reset to default

        # Clear the table and update with results
        self.ui.label_total.setText("")
        self.ui.table_result.clearContents()

        target_num = len(inference_result)
        if target_num == 0:
            return

        self.ui.table_result.setRowCount(target_num)
        success_num = 0
        for index, target in enumerate(inference_result):
            self.ui.table_result.setItem(index, 0, QTableWidgetItem(target["label"]))
            self.ui.table_result.setItem(index, 1, QTableWidgetItem(str(target["target_conf"])))
            self.ui.table_result.setItem(index, 2, QTableWidgetItem(str(target["predict_conf"])))
            result = RESULT_OK if target["predict_conf"] >= target["target_conf"] else RESULT_NG
            self.ui.table_result.setItem(index, 3, QTableWidgetItem(result))

            if result == RESULT_OK:
                success_num += 1

            # Set cell colors based on the result
            for col in range(4):  # For the first four columns
                item = self.ui.table_result.item(index, col)
                if result == RESULT_OK:
                    item.setForeground(QBrush(QColor(Qt.green)))
                elif result == RESULT_NG:
                    item.setForeground(QBrush(QColor(Qt.red)))

        self.ui.label_total.setText(f"检测数：{target_num}  |  OK数：{success_num}")
        self.ui.label_total.setStyleSheet("color: black; font-size: 24px;")

    def closeEvent(self, event):
        """Cleanup on close."""
        self.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
        event.accept()
        Logger.log_message("Application closed.")

    def resizeEvent(self, event):
        # Update Size Grips
        UIFunctions.resize_grips(self)

    def mousePressEvent(self, event):
        # SET DRAG POS WINDOW
        self.dragPos = event.globalPosition().toPoint()


def get_mainboard_serial_number():
    try:
        # 执行wmic命令获取主板序列号
        result = subprocess.run(['wmic', 'diskdrive', 'get', 'serialnumber'], capture_output=True, text=True,
                                check=True)
        # 输出结果通常包含标题行和序列号行，序列号行可能在第二行或第三行
        lines = result.stdout.split('\n')
        # 跳过第一行（标题行）
        for line in lines[1:]:  # 从第二行开始迭代
            stripped_line = line.strip()
            # 检查行是否非空且不是标题行（即不以"SerialNumber"开头）
            if stripped_line and not stripped_line.startswith("SerialNumber"):
                # 假设这是序列号行（注意：这取决于wmic输出的格式）
                return stripped_line
        return None  # 如果没有找到序列号，返回None
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving mainboard serial number: {e}")
        return None


if __name__ == "__main__":
    # mainboard_serial_number = get_mainboard_serial_number()
    # allowed_mainboard_serial_number = "WKPYYWGS"
    # if mainboard_serial_number != allowed_mainboard_serial_number:
    #     print("未授权电脑，无法运行！")
    #     sys.exit()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    window = MainWindow()
    # window.show_splash_screen()
    window.show()
    sys.exit(app.exec())
