import cv2
import requests
import numpy as np
import os
import time
from modules.logger import Logger
from modules.config import global_config


class Camera:
    def __init__(self):
        # 从全局配置中读取 Camera 设置
        camera_settings = global_config.config['Camera']

        # 初始化 Camera 属性
        self.url = camera_settings.get('url', '')
        self.username = camera_settings.get('username', '')
        self.password = camera_settings.get('password', '')
        self.photo_dir = camera_settings.get('photo_dir', '')
        self.saveRequire = camera_settings.getboolean('saveRequire', fallback=False)

    def get_frame(self):
        try:
            response = requests.get(self.url, auth=requests.auth.HTTPDigestAuth(self.username, self.password),
                                    timeout=5)
            if response.status_code == 200:
                result = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
                if result is None:
                    Logger.log_error("图片解码异常")
                    return None, None

                timestamp = time.strftime('%Y%m%d_%H%M%S')
                if self.saveRequire:
                    # 文件夹格式yyyy-mm-dd, 如2025-01-01
                    root_dir = os.path.join(str(self.photo_dir), time.strftime('%Y-%m-%d'))
                    os.makedirs(root_dir, exist_ok=True)  # Ensure results directory exists

                    save_path = os.path.join(root_dir, f"{timestamp}.jpg")
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                return result, timestamp
            else:
                Logger.log_error(f"拍照失败, 状态码: {response.status_code}")
                return None, None
        except Exception as e:
            Logger.log_error(f"拍照失败：{str(e)}")
            return None, None
