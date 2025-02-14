import json
import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
from modules.logger import Logger
from modules.config import global_config  # 引用全局配置对象


class YoloModel:
    def __init__(self, config_path):
        self.load_config(config_path)
        self.models = []
        self.load_models()

    def load_config(self, config_path):
        """从JSON文件读取配置文件."""
        try:
            with open(config_path) as f:
                config = json.load(f)
                self.task_name = config[0].get("task_name", "")
                self.model_configs = config[0].get("model", [])
                self.targets = config[0].get("targets", [])
                Logger.log_info("成功加载配置文件.")
        except FileNotFoundError:
            Logger.log_error("配置文件未找到.")
            raise
        except json.JSONDecodeError:
            Logger.log_error("解析配置文件失败.")
            raise
        except Exception as e:
            Logger.log_error(f"加载配置文件失败: {str(e)}")
            raise

    def load_models(self):
        """从配置文件加载模型配置."""
        try:
            for model_config in self.model_configs:
                model_path = model_config.get("path", "")
                if model_path:
                    self.models.append(
                        (YOLO(model_path), model_config.get("conf", 0.2)))  # Store model and confidence threshold
                else:
                    Logger.log_info("模型路径错误.")
            Logger.log_info("成功加载模型.")
        except Exception as e:
            Logger.log_error(f"加载模型错误: {str(e)}")
            raise

    def openvino_model(self, img):
        pass

    def predict(self, img, timestamp=None):
        """对输入图片进行预测."""
        if img is None:
            Logger.log_error("No image provided for prediction.")
            return []

        start_time = time.time()
        Logger.log_message(f"模型预测开始...")
        result = self.models[0][0].predict(img, conf=self.models[0][1])[0]  # Run the first model prediction
        Logger.log_message("模型预测完成")
        prediction_result = self.extract_prediction_result(result)

        Logger.log_message("检测判定开始...")
        all_predictions = []  # 保存所有目标的预测结果

        # 遍历每个目标进行预测
        for target in self.targets:
            target_predictions = self.process_target(prediction_result, target, img)
            all_predictions.append(target_predictions)

        Logger.log_message("检测判定完成")
        process_img, result_ready = self.draw_judge_results(img, all_predictions, timestamp)

        Logger.log_info(f"检测时间: {time.time() - start_time:.2f}s")
        return all_predictions, process_img, result_ready

    def process_target(self, prediction_result, target, orig_img):
        """对每个目标遍历进行二次模型预测."""
        conf1 = target["conf1"]
        conf2 = target["conf2"]
        target_label = target["label"]
        color = target['color']
        predefined_region = np.array(target["predefined_region"])
        # morphology = target.get("morphology")

        final_predictions = {
            "label": target_label,
            "predict_conf": 0.00,
            "boxes": predefined_region,
            "color": [0, 0, 255],
            "target_conf": conf1
        }

        # 刷选出与目标标签一致，且在预设坐标范围，置信度大于预设值的第一次预测结果
        filtered_boxes = []

        for cls_name, box, conf in prediction_result:
            if cls_name == target_label and self.is_in_region(box, predefined_region):
                filtered_boxes.append((box, conf))

        if filtered_boxes:
            candidate_box = max(filtered_boxes, key=lambda x: x[1])
            final_predictions["boxes"] = candidate_box[0]
            final_predictions["predict_conf"] = round(candidate_box[1], 2)

            if final_predictions["predict_conf"] >= final_predictions["target_conf"]:
                final_predictions["color"] = color

            # 用形态学对检测结果进行二次检测（如检测圆度、直径等）
            # if morphology is not None:
            #     self.morphology_detect(orig_img, candidate_box[0], morphology, target_label)

        # 对符合条件的第一次预测结果进行二次模型检测
        # if filtered_boxes:
        #     candidate_box = max(filtered_boxes, key=lambda x: x[1])
        #     second_stage_conf_predict = self.crop_and_predict(orig_img, candidate_box[0], target_label)
        #     final_predictions["predict_conf"] = second_stage_conf_predict
        #
        #     if second_stage_conf_predict > conf2:
        #         final_predictions["boxes"] = candidate_box[0]
        #         final_predictions["color"] = color
        # print(final_predictions)
        return final_predictions

    def extract_prediction_result(self, result):
        """打包预测结果，转换为类别名称、框、置信度的元组列表."""
        cls = result.boxes.cls.cpu().numpy()
        boxes = result.boxes.xyxy.cpu().numpy()
        conf = result.boxes.conf.cpu().numpy()
        names = result.names

        return [(names[int(x)], y, z) for x, y, z in zip(cls, boxes, conf)]

    def is_in_region(self, box, region):
        """检查检测框是否在预设范围."""
        return (
                box[0] >= region[0] and box[1] >= region[1] and
                box[2] <= region[2] and box[3] <= region[3]
        )

    def crop_and_predict(self, orig_img, box, target_label):
        """按照第一次预测结果框裁剪图像，并进行二次模型检测"""
        x1, y1, x2, y2 = box.astype(int)
        padding = 20

        # 确保增加后的边界框不会超出图像尺寸
        x1, y1 = max(x1 - padding, 0), max(y1 - padding, 0)
        x2, y2 = min(x2 + padding, orig_img.shape[1] - 1), min(y2 + padding, orig_img.shape[0] - 1)

        cropped_img = orig_img[y1:y2, x1:x2]
        if cropped_img.size == 0:
            return 0

        try:
            # 用二次模型对裁减图片进行预测
            result = self.models[1][0].predict(cropped_img, conf=self.models[1][1])[0]  # Use the second model

            extract_result = self.extract_prediction_result(result)
            return self.get_highest_confidence_target(extract_result, target_label)

        except Exception as e:
            Logger.log_error(f"预测发生错误: {str(e)}")
            return 0

    def morphology_detect(self, orig_img, box, morphology, target_label):
        """按照第一次预测结果框裁剪图像，并进行形态学检测"""
        x1, y1, x2, y2 = box.astype(int)
        cropped_img = orig_img[y1:y2, x1:x2]
        if cropped_img.size == 0:
            return 0

        if morphology["type"] == "circle":
            return self.circle_detect(cropped_img, target_label)
        return 0

    def circle_detect(self, image, label):
        """检测圆度及圆形直径"""
        # 将图像转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 使用高斯滤波来减少噪声
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        # 使用 Hough 变换检测圆形
        circles = cv2.HoughCircles(blurred,
                                   cv2.HOUGH_GRADIENT,
                                   dp=1,
                                   minDist=10,
                                   param1=50,
                                   param2=30,
                                   minRadius=0,
                                   maxRadius=0)

        # 处理检测到的圆
        diameter = 0
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                # 获取圆心 (x, y) 和半径 radius
                center_x, center_y, radius = i[0], i[1], i[2]
                # 计算直径
                diameter = radius * 2
                print(f'标签，{label}，圆心: ({center_x}, {center_y}), 半径: {radius}, 直径: {diameter}')
        return diameter

    def get_highest_confidence_target(self, predictions, target_label):
        """从 YOLO 预测结果中获取标签为 target_label 的置信度最大的目标"""
        filtered_predictions = [
            pred for pred in predictions if pred[0] == target_label
        ]

        # 如果没有找到目标，则返回 None
        if not filtered_predictions:
            return 0

        # 找出置信度最大的目标
        highest_confidence_target = max(filtered_predictions, key=lambda x: x[1])

        return highest_confidence_target[1]

    def draw_judge_results(self, orig_img, prediction_result, timestamp):
        """画检测框及保存图片."""
        result_ready = True

        for prediction in prediction_result:
            box = prediction["boxes"].astype(int)  # Ensure box coordinates are integers
            label = f"{prediction["label"]} {prediction["predict_conf"]:.2f}"
            cv2.rectangle(orig_img, (box[0], box[1]), (box[2], box[3]), prediction["color"], 2)
            cv2.putText(orig_img, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, prediction["color"], 2)

            result_ready &= (prediction["predict_conf"] >= prediction["target_conf"])

        # 文件夹格式task_name/yyyy-mm-dd, 如3UG-64530-3AO/2025-01-01
        inference_settings = global_config.get_inference_settings()
        root_dir = os.path.join(str(inference_settings['result_dir']), str(self.task_name), time.strftime('%Y-%m-%d'))
        os.makedirs(root_dir, exist_ok=True)  # Ensure results directory exists

        if timestamp is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(root_dir, f"{'OK' if result_ready else 'NG'}_{timestamp}.jpg")
        resized_img = cv2.resize(orig_img, (1280, 720))
        cv2.imwrite(save_path, resized_img)

        return orig_img, result_ready
