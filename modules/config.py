import configparser
import os


class Config:
    def __init__(self, config_file='config/config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        # 确保配置文件目录存在
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 检查配置文件是否存在
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # 创建默认配置文件
            self.create_default_config()

    def create_default_config(self):
        self.config['Logging'] = {'level': 'INFO'}
        self.config['Camera'] = {
            'url': '',
            'username': '',
            'password': '',
            'photo_dir': '',
            'saveRequire': 'false'
        }
        self.config['PLC'] = {
            'ip': '',
            'port': '10000',
            'trigger_bit': '0',
            'result_ok_bit': '0',
            'result_ng_bit': '1',
            'heartbeat_bit': '1',
            'interval': '1.0'
        }
        self.config['Inference'] = {'result_dir': ''}

        # 确保目录存在
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 写入默认配置文件
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_log_level(self):
        return self.config.get('Logging', 'level', fallback='INFO').upper()

    def get_camera_settings(self):
        return {
            'url': self.config.get('Camera', 'url', fallback=''),
            'username': self.config.get('Camera', 'username', fallback=''),
            'password': self.config.get('Camera', 'password', fallback=''),
            'photo_dir': self.config.get('Camera', 'photo_dir', fallback=''),
            'saveRequire': self.config.getboolean('Camera', 'saveRequire', fallback=False)
        }

    def get_plc_settings(self):
        return {
            'ip': self.config.get('PLC', 'ip', fallback=''),
            'port': self.config.getint('PLC', 'port', fallback=10000),
            'trigger_bit': self.config.getint('PLC', 'trigger_bit', fallback=0),
            'result_ok_bit': self.config.getint('PLC', 'result_ok_bit', fallback=0),
            'result_ng_bit': self.config.getint('PLC', 'result_ng_bit', fallback=1),
            'heartbeat_bit': self.config.getint('PLC', 'heartbeat_bit', fallback=2),
            'interval': self.config.getfloat('PLC', 'interval', fallback=1.0)
        }

    def get_inference_settings(self):
        return {
            'result_dir': self.config.get('Inference', 'result_dir', fallback='')
        }


# 创建全局配置实例
global_config = Config()
