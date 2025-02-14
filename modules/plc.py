from pymodbus.client import ModbusTcpClient
from modules.logger import Logger
from modules.config import global_config


class PLC:
    def __init__(self):
        # 从全局配置中读取 PLC 设置
        plc_settings = global_config.get_plc_settings()

        # 初始化 PLC 属性
        self.ip = plc_settings['ip']
        self.port = plc_settings['port']
        self.trigger_bit = plc_settings['trigger_bit']
        self.result_ok_bit = plc_settings['result_ok_bit']
        self.result_ng_bit = plc_settings['result_ng_bit']
        self.heartbeat_bit = plc_settings['heartbeat_bit']
        self.interval = plc_settings['interval']

        self.client = ModbusTcpClient(self.ip, port=self.port, timeout=5, retries=3)

    def connect(self):
        """连接IO板"""
        return self.client.connect()

    def read_bits(self):
        """读取IO板0-7位的状态"""
        try:
            if not self.connect():
                Logger.log_error("无法连接到IO板 at {}:{}".format(self.ip, self.port))
            response = self.client.read_discrete_inputs(address=0, count=8, slave=1)
            self.close()
            if not response.isError():
                return response.bits
            else:
                Logger.log_error(f"读取IO失败: {response}.")
                return None
        except Exception as e:
            Logger.log_error(f"读取IO错误: {e}.")
            return None

    def write_bit(self, address, value=False, retries=3):
        """按位写入IO板 with retry mechanism."""
        try:
            if not self.connect():
                Logger.log_error("无法连接到IO板 at {}:{}".format(self.ip, self.port))
            response = self.client.write_coil(address=address, value=value, slave=1)
            self.close()
            if not response.isError():
                Logger.log_message(f"成功写入值 {value} 到IO板输出位DO{address}")
                return
            else:
                Logger.log_error(f"写入IO失败: {response}.")
                return
        except Exception as e:
            Logger.log_error(f"写入IO错误: {e}.")
            return None

    def close(self):
        """与IO板断开连接."""
        if self.client.connected:
            self.client.close()
