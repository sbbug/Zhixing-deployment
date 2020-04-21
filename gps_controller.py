"""
-------------------------------------------------
   File Name:    gps_controller.py
   Date:         2019/12/09
   Description:
-------------------------------------------------
"""

import pynmea2
import serial
import time
import threading
from threading import Timer
import math
import csv
import subprocess


class GPSController:
    _ser = None
    _now_speed = 0.0
    _now_location = None  # [latitude, longitude]
    _stake_id_list = []  # 大桩号
    _stake_id_list_num = None
    _cfg = None
    _enable = True
    _sub_dis = 0.0  # 车辆到当前桩号的距离
    _thread_location_enable = True
    _speed_timer_control_enable = True
    _stake_jud_control_enable = True

    # ####################################### init  #######################################

    def __init__(self, enable, cfg, logger):
        self._cfg = cfg
        self._logger = logger
        self._enable = enable
        if self._enable:
            # TODO:串口容错
            try:
                self._ser = serial.Serial(self._cfg["PORT"], baudrate=self._cfg["BAUDRATE"], timeout=0.2)
            except:
                self._logger.warning("gps: serial.Serial error. set enable False")
                # self._enable = False
                return
            time.sleep(0.5)  # 启动时间，必须有

            self._load_stake_id_list(self._cfg["STAKE_ID_FILE_PATH"])
            self.thread_location = threading.Thread(target=self._read_location)
            self.thread_location.start()
            self._logger.info('Start read location ....')

            self.speed_timer_control = Timer(interval=1, function=self._cal_speed2)
            self.speed_timer_control.start()
            self._logger.info('Start calculation speed ....')

            self.stake_jud_control = Timer(interval=self._cfg["JUD_STAKE_ID_TIME_INTERVAL"],
                                           function=self._jud_stake_id2)
            self.stake_jud_control.start()
            self._logger.info('Start judge stake id ....')

    def _load_stake_id_list(self, stake_id_file_path):
        """加载桩号信息"""
        with open(stake_id_file_path) as f:
            f_csv = csv.reader(f)
            for row in f_csv:
                self._stake_id_list.append([int(row[0]), float(row[1]), float(row[2])])
        self._stake_id_list_num = len(self._stake_id_list)
        # print(self._stake_id_list)
        # print(self._stake_id_list_num)

    # ####################################### 读取位置，计算距离  #######################################

    def _read_location(self):
        while self._thread_location_enable and self._enable:
            try:
                recv = self._ser.readline().decode()
            except:
                self._logger.warning("gps: self._ser.readline().decode() error")
                continue
            if recv.startswith("$"):
                try:
                    record = pynmea2.parse(recv)
                except:
                    self._logger.warning("gps: pynmea2 parse error")
                    continue
                if recv.startswith('$GPRMC') or recv.startswith('$GNRMC'):
                    if record.status == 'A':  # 成功获取位置
                        try:
                            self._now_location = [record.longitude, record.latitude]
                        except:
                            self._logger.warning("gps: record.status == 'A' error, set location None")
                            self._now_location = None

                    else:
                        if self._now_location is not None:
                            self._logger.warning("GPS can not get location ,last location:longitude:" + str(
                                self._now_location[0]) + "latitude:" + str(self._now_location[1]))
                        else:
                            self._logger.warning("GPS can not get location ,no location")
                        self._now_location = None
                        time.sleep(1)
                        try:
                            self._ser = serial.Serial(self._cfg["PORT"], baudrate=self._cfg["BAUDRATE"], timeout=1)
                            self._logger.info("Try to open serial again")
                        except:
                            self._logger.warning("open serial again failed")
            time.sleep(0.3)

    @property
    def now_location(self):
        """:return 返回当前坐标，eg: [118.936854, 32.105107]"""
        if self._enable is False:
            return [118.936854, 32.105107]
        if self._now_location is None:
            return None
        return [round(self._now_location[0], 6), round(self._now_location[1], 6)]

    @staticmethod
    def cal_distance(long1, lat1, long2, lat2):
        """
        根据经纬度计算距离
        :param long1:经度1：小数制
        :param lat1:维度1：小数制
        :param long2:经度2：小数制
        :param lat2:维度2：小数制
        :return: 距离(m)
        """
        R = 6378137  # 地球半径
        lat1 = lat1 * math.pi / 180.0
        lat2 = lat2 * math.pi / 180.0
        a = lat1 - lat2
        b = (long1 - long2) * math.pi / 180.0
        sa2 = math.sin(a / 2.0)
        sb2 = math.sin(b / 2.0)
        d = 2 * R * math.asin(math.sqrt(sa2 * sa2 + math.cos(lat1) * math.cos(lat2) * sb2 * sb2))
        return d

    # ####################################### 计算速度  #######################################

    _last_location = None

    def _cal_speed(self):
        """计算速度，方式一"""
        location = self._now_location
        if location is None:
            self._now_speed = 0.0
            self._last_location = None
            self._logger.info("now speed: 0")
        if self._last_location is None:
            self._last_location = location
        else:
            x = math.pow((location[0] - self._last_location[0]), 2)
            y = math.pow((location[1] - self._last_location[1]), 2)
            distance_per_second = math.sqrt(x + y) * 111322.2222 * 3600 / 1000 / 1.825  # TODO:提前计算好
            self._sub_dis += distance_per_second  # 累计车辆当当前桩号的距离
            self._now_speed = round(distance_per_second, 1) * 0.2 + self._now_speed * 0.8  # 平滑更新速度
            self._logger.info("now speed:" + str(self._now_speed))
            self._last_location = location
        self.speed_timer_control = Timer(interval=1, function=self._cal_speed)
        self.speed_timer_control.start()

    def _cal_speed2(self):
        """计算速度，方式二"""
        location = self._now_location
        if location is None:
            self._now_speed = 0.0
            self._last_location = None
            self._logger.info("now speed: 0")
        if self._last_location is None:
            self._last_location = location
        else:
            distance_per_second = GPSController.cal_distance(location[0], location[1],
                                                             self._last_location[0], self._last_location[1])
            self._sub_dis += distance_per_second  # 累计车辆当当前桩号的距离
            self._now_speed = round(distance_per_second, 1) * 0.3 + self._now_speed * 0.7  # 平滑更新速度
            # self._logger.info("now speed:" + str(self._now_speed))
            self._last_location = location
        if self._speed_timer_control_enable:
            self.speed_timer_control = Timer(interval=1, function=self._cal_speed2)
            self.speed_timer_control.start()

    @property
    def now_speed(self):
        """:return 返回速度，eg:1.1 (m/s)"""
        return self._now_speed

    # ####################################### 判断桩号  #######################################
    _is_stake_id_changed = False
    _now_stake_id = None  # [idx, id] idx:id在列表中的位置，id:大桩号
    _last_stake_id = None  # 上一桩号, id:大桩号
    _start_stake_id = None  # 起始桩号, id:大桩号

    def _jud_stake_id(self):
        """判断当前桩号（有桩号经纬度情况）"""
        while self._now_location is None:  # 启动时无gps数据
            self._logger.info("Can't jud stake id, now_stake_id is none")
            time.sleep(self._cfg["JUD_STAKE_ID_TIME_INTERVAL"])
        long, lat = self._now_location[0], self._now_location[1]
        # TODO:根据速度，是否需要判断桩号
        if self._now_stake_id is None:  # 启动时，当前桩号为空
            for idx, (id, id_long, id_lat) in enumerate(self._stake_id_list):
                if GPSController.cal_distance(long, lat, id_long, id_lat) < self._cfg["JUD_STAKE_ID_DISTANCE"]:
                    self._now_stake_id = idx, id  # idx:id在列表中的位置，id:大桩号
                    self._start_stake_id = id
                    self._sub_dis = 0.0  # 车辆到桩号的距离清零
                    self._logger.info("Start stake id: K" + str(self._start_stake_id))
                    break
        else:  # 根据已知桩号，预测下一桩号
            if self._now_stake_id[0] == 0:  # 当前桩号为起始桩号,只预测第二个桩号
                next_stake = self._stake_id_list[1]
                if GPSController.cal_distance(long, lat, next_stake[1], next_stake[2]) < self._cfg[
                    "JUD_STAKE_ID_DISTANCE"]:
                    if self._now_stake_id != (1, next_stake[0]):  # 防止同一桩号多次发出桩号更新信息
                        self._last_stake_id = self._now_stake_id[1]  # 更新上一桩号
                        self._sub_dis = 0.0  # 车辆到桩号的距离清零
                        self._now_stake_id = 1, next_stake[0]
                        self._is_stake_id_changed = True
                        self._logger.info("Now stake id: K" + str(self._now_stake_id) + ",no stake id")
                # print("Now stake id: K", self.now_stake_id, ",no stake id:")
            elif self._now_stake_id[0] == self._stake_id_list_num - 1:  # 当前桩号为终止桩号，只预测倒数第二个桩号
                next_stake = self._stake_id_list[-2]
                if GPSController.cal_distance(long, lat, next_stake[1], next_stake[2]) < self._cfg[
                    "JUD_STAKE_ID_DISTANCE"]:
                    if self._now_stake_id != (self._stake_id_list_num - 2, next_stake[0]):  # 防止同一桩号多次发出桩号更新信息
                        self._last_stake_id = self._now_stake_id[1]  # 更新上一桩号
                        self._sub_dis = 0.0  # 车辆到桩号的距离清零
                        self._now_stake_id = self._stake_id_list_num - 2, next_stake[0]
                        self._is_stake_id_changed = True
                self._logger.info(
                    "Now stake id: K" + str(self.now_stake_id[1]) + ",Last stake id: K" + str(self.last_stake_id))
                # print("Now stake id: K", self.now_stake_id, ",Last stake id: K", self.last_stake_id)

            else:  # 当前桩号为中间桩,预测临近两个桩号
                next_stake_list = [self._stake_id_list[self._now_stake_id[0] - 1],  # 前一桩
                                   self._stake_id_list[self._now_stake_id[0] + 1]]  # 后一桩
                for idx, next_stake in enumerate(next_stake_list):
                    if GPSController.cal_distance(long, lat, next_stake[1], next_stake[2]) < self._cfg[
                        "JUD_STAKE_ID_DISTANCE"]:
                        if idx == 0:  # 前一桩
                            next_idx = self._now_stake_id[0] - 1
                        else:  # 后一桩
                            next_idx = self._now_stake_id[0] + 1
                        if self._now_stake_id != (next_idx, next_stake[0]):  # 防止同一桩号多次发出桩号更新信息
                            self._last_stake_id = self._now_stake_id[1]  # 更新上一桩号
                            self._sub_dis = 0.0  # 车辆到桩号的距离清零
                            self._now_stake_id = next_idx, next_stake[0]
                            self._is_stake_id_changed = True
                self._logger.info(
                    "Now stake id: K" + str(self.now_stake_id[1]) + ",Last stake id: K" + str(self.last_stake_id))
        if self._stake_jud_control_enable:
            self.stake_jud_control = Timer(interval=self._cfg["JUD_STAKE_ID_TIME_INTERVAL"],
                                           function=self._jud_stake_id)
            self.stake_jud_control.start()

    def _jud_stake_id2(self):
        """判断当前桩号(循环判断)"""
        while self._now_location is None:  # 启动时无gps数据
            self._logger.info("Can't jud stake id, now_location is none")
            time.sleep(self._cfg["JUD_STAKE_ID_TIME_INTERVAL"])
        long, lat = self._now_location[0], self._now_location[1]
        # TODO:根据速度，是否需要判断桩号
        for idx, (id, id_long, id_lat) in enumerate(self._stake_id_list):
            if GPSController.cal_distance(long, lat, id_long, id_lat) < self._cfg["JUD_STAKE_ID_DISTANCE"]:
                stake_id = idx, id  # idx:id在列表中的位置，id:大桩号
                if self._start_stake_id is None:  # 则该桩号为起始桩号
                    self._sub_dis = 0.0  # 车辆到桩号的距离清零
                    self._now_stake_id = stake_id
                    self._start_stake_id = id
                    self._logger.info("Start stake id: K" + str(self._start_stake_id))
                else:
                    if stake_id != self._now_stake_id:  # 防止同一桩号多次发出桩号更新信息
                        self._sub_dis = 0.0  # 车辆到桩号的距离清零
                        self._last_stake_id = self._now_stake_id[1]  # 更新上一桩号
                        self._now_stake_id = stake_id  # 更新当前桩号
                        self._is_stake_id_changed = True

                self._logger.info(
                    "Now stake id: K" + str(self._start_stake_id) + ", last stake id: K" + str(self.last_stake_id))
                break
        if self._stake_jud_control_enable:
            self.stake_jud_control = Timer(interval=self._cfg["JUD_STAKE_ID_TIME_INTERVAL"],
                                           function=self._jud_stake_id2)
            self.stake_jud_control.start()

    _last_stake_id_change_time = None

    @property
    def is_stake_id_changed(self):
        """返回桩号是否变化"""
        if not self._enable:
            if self._last_stake_id_change_time is None:
                self._last_stake_id_change_time = time.time()
                return True
            else:
                if time.time() - self._last_stake_id_change_time >= 10:
                    self._last_stake_id_change_time = time.time()
                    return True
                else:
                    return False
        return self._is_stake_id_changed

    def cancel_stake_changed_msg(self):
        """当主逻辑得知桩号变化后，取消桩号变化信号"""
        # TODO:是否加lock
        self._is_stake_id_changed = False

    @property
    def start_stake_id(self):
        """
        确认开始桩号
        :return: 启动时尚未确认桩号，返回None
        """
        if self._enable is False:
            return True
        if self._start_stake_id is None:
            return None
        # if self._now_speed # TODO:保证速度在一定范围
        return self._start_stake_id

    @property
    def now_stake_id(self):
        """:return 返回桩号信息，eg: 775 ;none表示系统启动时，尚未找到桩号"""
        if self._enable is False:
            return 775
        if self._now_stake_id is None:
            return None
        return self._now_stake_id[1]

    @property
    def last_stake_id(self):
        """:return 返回上一桩号, eg: 774,;none表示系统尚未找到上一桩号"""
        if self._enable is False:
            return 774
        return self._last_stake_id

    @property
    def sub_dis(self):
        """:return 返回当前车辆到当前桩号的距离"""
        if self._enable is False:
            return 100
        return int(self._sub_dis)

    @property
    def info(self):
        """:return 当前速度，当前坐标，当前桩号，当前车辆到当前桩号的距离，上一桩号"""
        return self.now_speed, self.now_location, self.now_stake_id, self.sub_dis, self.last_stake_id

    def stop(self):
        self._thread_location_enable = False
        self._speed_timer_control_enable = False
        self._stake_jud_control_enable = False


if __name__ == "__main__":
    # read location test
    # gps = GPSController("/dev/tty.usbserial-14330")
    # while True:
    #     gps.read_location()
    #     time.sleep(2)

    # cal distance test
    print(GPSController.cal_distance(118.936854, 32.105107, 118.946532, 32.110063))
