import time
# import cv2
from PySide6.QtCore import Signal, QObject, Slot
from modules.camera import Camera
from modules.yolo_model import YoloModel
from modules.logger import Logger
from modules.plc import PLC
# import os

class Worker(QObject):
    run = Signal()
    finished = Signal()
    error = Signal(str)
    image_process = Signal(object)
    update_status = Signal(str)
    inference_result = Signal(str, list)

    def __init__(self):
        super().__init__()
        self.camera = Camera()
        self.plc = None
        self.running = False
        self.current_frame = None, None
        self.model = None

    @Slot()
    def start_capture(self):
        """Capture a single frame and process it."""
        self.update_status.emit("采集图片中...")
        self.image_process.emit(None)
        if self.running:
            self.error.emit("Capture is already running.")
            return

        self.running = True  # Start the capture session
        self.run.emit()
        frame, timestamp = self.camera.get_frame()
        if frame is not None:
            self.current_frame = frame, timestamp
            self.image_process.emit(frame)
            self.update_status.emit("")
            Logger.log_message("采集图片成功")
        else:
            self.update_status.emit("拍照失败！")
            self.error.emit("拍照失败！")

        self.cleanup()

    @Slot()
    def start_inference(self):
        """Run inference on a single captured frame."""
        self.update_status.emit("图像检测中...")
        self.image_process.emit(None)
        self.inference_result.emit("", [])
        self.run.emit()

        self.model = YoloModel("config/setting.json")

        # 对最近一次拍照的照片进行推理
        frame, timestamp = self.current_frame

        # 以下为测试使用
        # frame = cv2.imread("images/20241231_150322.jpg")
        # timestamp = "20241231_150322"

        if frame is not None:
            predictions, processed_img, result = self.model.predict(frame, timestamp)
            self.image_process.emit(processed_img)
            self.inference_result.emit("OK" if result else "NG", predictions)
            self.update_status.emit("图像检测完成！")
        else:
            self.update_status.emit("请先加载图片！")
            self.error.emit("No frame available for inference.")

        self.cleanup()

    def _run_continuous_capture_or_inference(self, inference=False):
        self.update_status.emit("连续采集图片..." if not inference else "自动运行检测中...")
        self.image_process.emit(None)
        self.inference_result.emit("", [])
        self.run.emit()
        self.running = True

        self.plc = PLC()
        self.model = YoloModel("config/setting.json") if inference else None
        trigger_memory = False

        # 以下为测试数据
        # folder_path = "images"
        # fake_data = []
        # fake_index = 0
        # for img_name in os.listdir(folder_path):
        #     img_path = os.path.join(folder_path, img_name)
        #     if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        #         filename, extension = os.path.splitext(img_name)
        #         fake_data.append({'frame': img_path, 'timestamp': filename})

        while self.running:
            read_bits = self.plc.read_bits()
            trigger = False
            if read_bits is not None:
                trigger = read_bits[self.plc.trigger_bit]

            if trigger and not trigger_memory:
                self.image_process.emit(None)
                self.inference_result.emit("", [])
                frame, timestamp = self.camera.get_frame()

                # 以下为测试数据
                # frame = cv2.imread(fake_data[fake_index].get('frame'))
                # timestamp = fake_data[fake_index].get('timestamp')
                # fake_index += 1
                # if fake_index >= len(fake_data):
                #     fake_index = 0

                if frame is not None:
                    Logger.log_message("采集图片成功" + (",开始检测..." if inference else ""))
                    self.image_process.emit(frame)

                    if inference:
                        predictions, processed_img, result = self.model.predict(frame, timestamp)
                        self.image_process.emit(processed_img)
                        self.inference_result.emit("OK" if result else "NG", predictions)
                        self.plc.write_bit(self.plc.result_ok_bit, result)
                        self.plc.write_bit(self.plc.result_ng_bit, not result)

                    trigger_memory = True
                else:
                    self.error.emit("拍照失败！")

            if not trigger and trigger_memory:
                trigger_memory = False
                if inference:
                    self.plc.write_bit(self.plc.result_ok_bit, False)
                    self.plc.write_bit(self.plc.result_ng_bit, False)

            time.sleep(self.plc.interval)
        self.update_status.emit("")
        self.cleanup()

    @Slot()
    def start_continuous_capture(self):
        self._run_continuous_capture_or_inference(inference=False)

    @Slot()
    def start_continuous_inference(self):
        self._run_continuous_capture_or_inference(inference=True)

    @Slot()
    def stop(self):
        """Stop the worker thread."""
        if self.running:
            self.update_status.emit("")
            self.running = False
            Logger.log_message("Stopping operations.")

    def cleanup(self):
        """任务结束后，发射结束状态、清理资源"""
        self.running = False
        self.finished.emit()
