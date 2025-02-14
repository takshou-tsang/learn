import logging
import os
from logging.handlers import TimedRotatingFileHandler
from modules.config import global_config  # 引用全局配置对象


class Logger:
    @staticmethod
    def setup_logging(log_file='log/app.log'):
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=30)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.basicConfig(level=getattr(logging, global_config.get_log_level(), logging.INFO), handlers=[handler])

    @staticmethod
    def log_message(message, level=logging.INFO):
        logging.log(level, message)

    @staticmethod
    def log_error(message):
        logging.error(message)

    @staticmethod
    def log_info(message):
        logging.info(message)

    @staticmethod
    def log_debug(message):
        logging.debug(message)
