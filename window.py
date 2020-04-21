"""
-------------------------------------------------
   File Name:    window.py
   Date:         2019/11/27
   Description:  
-------------------------------------------------
"""

import cv2
import threading
import numpy as np
import time
from utils.visualization import BBoxVisualization
from PIL import Image, ImageDraw, ImageFont
import queue
from multiprocessing import Process, Queue
import subprocess as sp

WINDOW_NAME = 'CameraTFTRTDemo'
FONT = cv2.FONT_HERSHEY_PLAIN
LINE = cv2.LINE_AA

resources_path = "/media/user/Elements SE/ZHIXING/resources/"
# resources_path = "/media/user/TOSHIBA EXT/ZHIXING/resources/"

start_up_img_filename = resources_path + "images/start_up.jpg"

speed_and_location_bg_filename = resources_path + "images/speed_and_location_bg.png"
time_bg_filename = resources_path + "images/time_bg.png"
km_score_coefficient_bg_filename = resources_path + "images/km_score_coefficient_bg.png"
last_km_score_bg_filename = resources_path + "images/last_km_score_bg.png"
ob_k_bg_filename = resources_path + "images/ob_k_bg.png"
real_time_score_bg_filename = resources_path + "images/real_time_score_bg.png"
win_bg_filename = resources_path + "images/win_bg.png"

gpu_load_file = "/sys/devices/gpu.0/load"
font_file_path = resources_path + "fonts/PingFang.ttc"

label_english_to_chinese = {
    "CLS0": "CLS0",
    "bottle": "瓶子",
    "plastic": "塑料袋",
    "paper": "纸巾",
    "rock": "石子",
    "bow": "木屑",
    "leaf": "树叶",
    "box": "盒子",
}

score_english_to_chinese = {
    "h_s": "前置得分",
    "b_s": "后置得分",
    "c_s": "对比得分",
    "comp_sum_score": "对比均分",
    "head_sum_score": "前置均分",
    "back_sum_score": "后置均分",
    "left_sum_level": "左侧均级",
    "right_sum_level": "左侧均级",
    "sum_s": "综合得分",
    "l_s": "左侧等级",
    "r_s": "右侧等级"
}
left_and_right_level_english_to_chinese = {
    "1": "优",
    "2": "良",
    "3": "差"
}

km_score_coefficient_english_to_chinese = {
    "dust_coe": "扬尘系数",
    "traffic_coe": "车流量系数",
    "weather_coe": "气象系数",
    "environment_coe": "路段环境系数"
}

cam_id_num_to_chinese = {
    '0': "前置摄像头",
    '1': "左侧摄像头",
    '2': "右侧摄像头",
    '3': "后置摄像头"
}


class Live(object):
    frame = None

    def __init__(self, enable, way='rtsp', url="rtsp://117.78.39.159:554/live.sdp", size=(1280, 720), fps=25):
        self.enable = enable
        if not enable:
            return
        self.frame_queue = Queue(maxsize=5)
        self.fps = fps
        self.size = size

        if way == "rtmp":
            self.command = ['ffmpeg',
                            '-re',
                            '-loglevel', 'error',
                            '-y',
                            '-f', 'rawvideo',
                            '-vcodec', 'rawvideo',
                            '-pix_fmt', 'bgr24',
                            '-s', "{}x{}".format(*self.size),
                            '-r', str(fps),
                            '-i', '-',
                            '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p',
                            '-preset', 'ultrafast',
                            # '-preset', 'veryfast',
                            '-f', 'flv',
                            url]
        elif way == "rtsp":
            self.command = ['ffmpeg',
                            '-loglevel', 'error',
                            '-y',
                            '-f', 'rawvideo',
                            '-vcodec', 'rawvideo',
                            '-pix_fmt', 'bgr24',
                            '-s', "{}x{}".format(*self.size),
                            '-r', str(fps),
                            '-i', '-',
                            '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p',
                            '-preset', 'ultrafast',
                            '-rtsp_transport', 'tcp',
                            '-f', 'rtsp',
                            url]

    def read_frame(self, view):
        if not self.enable:
            return
            # print("开启推流")
        frame = cv2.resize(view, self.size)
        # put frame into queue
        if self.frame_queue.full():
            self.frame_queue.get()
            self.frame_queue.put(frame)
        else:
            self.frame_queue.put(frame)

        # time.sleep(1 / 12)
        # self.p.stdin.write(frame.tostring())

    def push_frame(self, queue):
        # 防止多线程时 command 未被设置
        while True:
            if len(self.command) > 0:
                # 管道配置
                p = sp.Popen(self.command, stdin=sp.PIPE)
                break

        now_frame = None
        while True:
            if queue.empty() is not True:
                frame = queue.get()
                now_frame = frame
                # write to pipe
                try:
                    p.stdin.write(frame.tostring())
                except:
                    pass
                time.sleep(1 / self.fps)
            elif now_frame is not None:
                try:
                    p.stdin.write(now_frame.tostring())
                except:
                    pass
                time.sleep(1 / self.fps)

    def run(self):
        # threads = [
        #     # threading.Thread(target=self.read_frame),
        #     threading.Thread(target=self.push_frame),
        # ]
        # [thread.setDaemon(True) for thread in threads]
        # [thread.start() for thread in threads]

        # self.process = threading.Thread(target=self.push_frame, args=(self.frame_queue,))
        # self.process.setDaemon(True)
        # self.process.start()

        if self.enable:
            # self.process = threading.Thread(target=self.push_frame, args=(self.frame_queue,))
            # self.process.setDaemon(True)
            # self.process.start()
            self.process = Process(target=self.push_frame, args=(self.frame_queue,))
            self.process.daemon = True
            self.process.start()


class Window:
    _now_view = None  # 当前画面
    _full_screen = True  # 是否全屏
    _window_name = None
    _show_enable = True  # 开启显示
    _show_start = None
    _show_fps = False
    _screen_width, _screen_height = None, None
    camera_view = {}
    _view_lock = threading.Lock()
    _vis = None
    _h_cls_idx_count = None
    _b_cls_idx_count = None
    _fps = 0.0
    _cls_dict = None
    _now_stake_id = None
    _freq_score = {}
    _km_score = {}
    _coefficient = {}
    _now_speed = 0.0
    _now_location = None
    _sub_dis = 0
    _last_stake_id = None
    _is_show = True
    _ob_k = {}
    _cams = None

    def __init__(self, enable, window_name="zhixing", full_screen=True):
        """
        init
        :param enable: 是否显示界面
        :param window_name: 窗口title名（未用）
        :param full_screen: 是否全屏
        """
        self._show_enable = enable
        self._window_name = window_name
        self._full_screen = full_screen

        if self._show_enable:
            try:
                import pyautogui
                self._screen_width, self._screen_height = pyautogui.size()
            except:
                self._screen_width, self._screen_height = 1920, 1200
            self._init_view()
            self.show_start_up()
            self._load_bg()
            time.sleep(0.2)
            self.thread = threading.Thread(target=self._update_view)
            self.thread.start()
            self.live = Live(enable=True)
            self.live.run()

    def _init_view(self):
        """
        初始化窗口
        :return:
        """
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        if self._full_screen:
            self.set_full_screen(True)
        else:
            cv2.resizeWindow(WINDOW_NAME, self._screen_width, self._screen_width)
            cv2.moveWindow(WINDOW_NAME, 0, 0)
        cv2.setWindowTitle(WINDOW_NAME, 'Camera TF_TRT Object Detection Demo '
                                        'for Jetson TX2/TX1')

    def _load_bg(self):
        """加载背景文件，除了win_bg"""
        self._km_score_coefficient_bg = cv2.imread(km_score_coefficient_bg_filename)
        self._time_bg = cv2.imread(time_bg_filename)
        self._km_score_coefficient_bg = cv2.imread(km_score_coefficient_bg_filename)
        self._last_km_score_bg = cv2.imread(last_km_score_bg_filename)
        self._ob_k_bg = cv2.imread(ob_k_bg_filename)
        self._real_time_score_bg = cv2.imread(real_time_score_bg_filename)
        self._speed_and_location_bg = cv2.imread(speed_and_location_bg_filename)

    def set_cls_dict(self, cls_dict):
        """确认目标种类，并实例化绘框句柄"""
        self._cls_dict = cls_dict
        self._vis = BBoxVisualization(cls_dict)
        self._h_cls_idx_count = [0 for _ in range(len(self._cls_dict))]
        self._b_cls_idx_count = [0 for _ in range(len(self._cls_dict))]

    def set_cam_handle(self, cams):
        """设置实时视频流句柄"""
        self._cams = cams

    def set_full_screen(self, full_scrn):
        """
        窗口调节函数，全屏或退出全屏
        :param full_scrn:
        :return:
        """
        prop = cv2.WINDOW_FULLSCREEN if full_scrn else cv2.WINDOW_NORMAL
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, prop)

    @staticmethod
    def change_cv2_draw(image, strs, local, sizes, colour):  # 解决cv2.putText显示中文问题
        cv2img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pilimg = Image.fromarray(cv2img)
        draw = ImageDraw.Draw(pilimg)  # 图片上打印
        font = ImageFont.truetype(font_file_path, sizes, encoding="utf-8")
        draw.text(local, strs, colour, font=font)
        image = cv2.cvtColor(np.array(pilimg), cv2.COLOR_RGB2BGR)
        return image

    # ####################################### show start up  #######################################
    def show_start_up(self):
        """开机界面"""
        if self._show_enable:
            self._show_start = True
            start_up_img = cv2.imread(start_up_img_filename)
            print("加载开机界面", end=' ')
            while start_up_img is None:  # 设置系统开机自启后，需要等待磁盘加载
                start_up_img = cv2.imread(start_up_img_filename)
                print(".", end=' ')
                time.sleep(0.5)
            print()
            start_up_img = cv2.resize(start_up_img, (self._screen_width, self._screen_height))
            cv2.imshow(WINDOW_NAME, start_up_img)

    # ####################################### show img and img info  #######################################
    def show_img(self, result, ob_k):
        """
        为外部调用，传参已显示结果
        :param result: 众多结果
        :param ob_k: 各类别系数
        :return:
        """
        if not self._show_enable:
            return
        for i, cam_id in enumerate(['0', '3', '1', '2']):
            img, box, conf, cls, curr_fps = result[cam_id]
            if img is None:
                continue

            # self.camera_view[k] = [img, info]
            # box = info["box"]
            # conf = info["conf"]
            # cls = info["cls"]
            # curr_fps = info["curr_fps"]
            # ob_k = info["k"]

            self._fps = curr_fps if self._fps == 0.0 else (self._fps * 0.9 + curr_fps * 0.1)
            img = self._vis.draw_bboxes(img, box, conf, cls)  # 绘制框
            if self._now_view is None:
                self._now_view = cv2.imread(win_bg_filename)
                self._draw_ob_k(ob_k)
            img = cv2.resize(img, (320, 300))
            img = self._draw_img_info(img, cls, cam_id)  # 写信息
            h, w, _ = img.shape
            if cam_id == '0':
                self._now_view[260:260 + 300, 28:28 + 320] = img
            elif cam_id == '1':
                self._now_view[260:260 + 300, 712:712 + 320] = img
            elif cam_id == '2':
                self._now_view[260:260 + 300, 1052:1052 + 320] = img
            elif cam_id == '3':
                self._now_view[260:260 + 300, 368:368 + 320] = img

        # if self._show_fps:
        #     self._draw_help_and_fps_and_gpu(True, self._fps)
        # else:
        #     self._draw_help_and_fps_and_gpu(False)
        # cv2.imshow(WINDOW_NAME, self._now_view)

    def _draw_img_info(self, img, cls, k):
        """
        在图片上增加信息
        :param img: 图片
        :param cls: 信息
        :return:
        """
        # 统计个数
        if k == '0':
            for idx in cls:
                self._h_cls_idx_count[idx] += 1
                # 绘制个数文字
            for key, label in self._cls_dict.items():
                text = label_english_to_chinese[label] + ":" + str(self._h_cls_idx_count[key])
                y = key * 30
                # cv2.putText(img, text, (200, 300 + y), FONT, 10.0, (255, 0, 0), 4, LINE)
                img = Window.change_cv2_draw(img, text, (50, 50 + y), 20, (0, 0, 255))  # 中文
        elif k == '3':
            for idx in cls:
                self._b_cls_idx_count[idx] += 1
            for key, label in self._cls_dict.items():
                text = label_english_to_chinese[label] + ":" + str(self._b_cls_idx_count[key])
                y = key * 30
                # cv2.putText(img, text, (200, 300 + y), FONT, 10.0, (255, 0, 0), 4, LINE)
                img = Window.change_cv2_draw(img, text, (50, 50 + y), 20, (0, 0, 255))  # 中文
        elif k == '1':
            level = self._freq_score["l_s"]
            img = Window.change_cv2_draw(img, left_and_right_level_english_to_chinese[level], (50, 50), 20,
                                         (0, 0, 255))
        elif k == '2':
            level = self._freq_score["r_s"]
            img = Window.change_cv2_draw(img, left_and_right_level_english_to_chinese[level], (50, 50), 20,
                                         (0, 0, 255))

        img = Window.change_cv2_draw(img, cam_id_num_to_chinese[k], (10, 22), 20, (0, 0, 255))  # 中文

        return img

    def clean_cls_idx_count(self):
        """置零公里级目标统计数"""
        if self._h_cls_idx_count is not None:
            self._h_cls_idx_count = [0 for _ in self._h_cls_idx_count]
        if self._b_cls_idx_count is not None:
            self._b_cls_idx_count = [0 for _ in self._b_cls_idx_count]

    # ####################################### draw help and fps gpu usage info  #######################################
    def _draw_help_and_fps_and_gpu(self, show, fps=0.0):
        """Draw help message and fps number at top-left corner of the image."""
        width = 500
        height = 60
        area = np.ones((height, width, 3), dtype=np.uint8)
        if show:
            help_text = "'Esc' to Quit, 'H' for FPS & Help, 'F' for Fullscreen"
            fps_text = 'FPS: {:.1f}, GPU usage: {:.2f}%'.format(fps, Window._get_gpu_usage())
            cv2.putText(area, help_text, (11, 20), FONT, 1.0, (32, 32, 32), 4, LINE)
            cv2.putText(area, help_text, (10, 20), FONT, 1.0, (240, 240, 240), 1, LINE)
            cv2.putText(area, fps_text, (11, 50), FONT, 1.0, (32, 32, 32), 4, LINE)
            cv2.putText(area, fps_text, (10, 50), FONT, 1.0, (240, 240, 240), 1, LINE)
        self._now_view[:height, :width, :] = area

    @staticmethod
    def _get_gpu_usage():
        with open(gpu_load_file, 'r') as gpu_file:
            file_data = gpu_file.read()
        return int(file_data) / 10

    # ####################################### update and draw score  #######################################
    def update_freq_score(self, info):
        """更新按频率采样得分"""
        self._freq_score = info

    def update_km_score(self, last_stake_id, score):
        """更新按公里采样得分"""
        self._last_stake_id = last_stake_id
        self._km_score = score

    def update_coefficient(self, coefficient):
        self._coefficient = coefficient

    def _draw_ob_k(self, ob_k):
        """绘制目标系数"""
        ob_k_area = self._ob_k_bg.copy()
        h, w, _ = ob_k_area.shape
        text = ""
        for key, label in self._cls_dict.items():
            text += label_english_to_chinese[label] + ":" + str(ob_k[label]) + "%   "
        ob_k_area = Window.change_cv2_draw(ob_k_area, text, (145, 7), 12,
                                           (0, 255, 255))
        self._now_view[230:230 + h, 28:28 + w, :] = ob_k_area

    def _draw_real_time_score(self):
        """"绘制按频率采样得分"""
        real_time_score_area = self._real_time_score_bg.copy()
        h_r, w_r, _ = real_time_score_area.shape

        if self._now_stake_id is None:
            real_time_score_area = Window.change_cv2_draw(real_time_score_area, "当前桩号未知", (85, 8), 18, (255, 255, 255))
        else:
            real_time_score_area = Window.change_cv2_draw(real_time_score_area,
                                                          'K' + str(self._now_stake_id) + "+" + str(self._sub_dis),
                                                          (85, 8), 18, (255, 255, 255))
        # 绘制按频率采样得分
        for idx, (label, score) in enumerate(self._freq_score.items()):
            if label == "h_s":
                real_time_score_area = Window.change_cv2_draw(real_time_score_area, str(round(score, 1)), (25, 65), 15,
                                                              (255, 255, 255))
            if label == "b_s":
                real_time_score_area = Window.change_cv2_draw(real_time_score_area, str(round(score, 1)), (160, 65), 15,
                                                              (255, 255, 255))
            if label == "c_s":
                real_time_score_area = Window.change_cv2_draw(real_time_score_area, str(round(score, 1)), (300, 65), 15,
                                                              (255, 255, 255))
            if label == "l_s":
                real_time_score_area = Window.change_cv2_draw(real_time_score_area,
                                                              left_and_right_level_english_to_chinese[score], (435, 65),
                                                              15,
                                                              (255, 255, 255))
            if label == "r_s":
                real_time_score_area = Window.change_cv2_draw(real_time_score_area,
                                                              left_and_right_level_english_to_chinese[score], (572, 65),
                                                              15,
                                                              (255, 255, 255))
            # cv2.putText(score_area, text, (50, y), FONT, 4.0, (0, 255, 0), 4, LINE)

        # 绘制系数
        self._now_view[98:98 + h_r, 28:28 + w_r, :] = real_time_score_area

    def _draw_coefficient(self):
        km_coefficient_area = self._km_score_coefficient_bg.copy()
        h_c, w_c, _ = km_coefficient_area.shape
        # 绘制系数
        coefficient_text = ""
        for idx, (label, k) in enumerate(self._coefficient.items()):
            coefficient_text += km_score_coefficient_english_to_chinese[label] + ":" + str(
                str(round(k, 1))) + "            "
        km_coefficient_area = Window.change_cv2_draw(km_coefficient_area, coefficient_text, (140, 7), 12,
                                                     (0, 255, 255))  # 中文
        self._now_view[230:230 + h_c, 712:712 + w_c, :] = km_coefficient_area

    _last_km_score = None

    def _draw_km_score(self):
        """绘制按公里采样得分"""
        # if self._last_km_score is not None and self._last_km_score == self._km_score:
        #     return
        # self._last_km_score = self._km_score
        km_score_area = self._last_km_score_bg.copy()
        h_s, w_s, _ = km_score_area.shape
        # km_coefficient_area = self._km_score_coefficient_bg.copy()
        # h_c, w_c, _ = km_coefficient_area.shape

        if self._last_stake_id is None:
            km_score_area = Window.change_cv2_draw(km_score_area, "上一桩号未知", (118, 8), 18,
                                                   (255, 255, 255))
        else:
            km_score_area = Window.change_cv2_draw(km_score_area, 'K' + str(self._last_stake_id), (118, 8), 18,
                                                   (255, 255, 255))
        # 绘制按公里采样得分
        for idx, (label, score) in enumerate(self._km_score.items()):
            if label == "head_sum_score":
                km_score_area = Window.change_cv2_draw(km_score_area, str(round(score, 1)), (25, 65), 15,
                                                       (255, 255, 255))
            if label == "back_sum_score":
                km_score_area = Window.change_cv2_draw(km_score_area, str(round(score, 1)), (135, 65), 15,
                                                       (255, 255, 255))
            if label == "comp_sum_score":
                km_score_area = Window.change_cv2_draw(km_score_area, str(round(score, 1)), (245, 65), 15,
                                                       (255, 255, 255))
            if label == "sum_s":
                km_score_area = Window.change_cv2_draw(km_score_area, str(round(score, 1)), (355, 65), 15,
                                                       (255, 255, 255))
            if label == "left_sum_level":
                km_score_area = Window.change_cv2_draw(km_score_area, left_and_right_level_english_to_chinese[score],
                                                       (465, 65), 15,
                                                       (255, 255, 255))
            if label == "right_sum_level":
                km_score_area = Window.change_cv2_draw(km_score_area, left_and_right_level_english_to_chinese[score],
                                                       (575, 65), 15,
                                                       (255, 255, 255))

            # cv2.putText(score_area, text, (50, y), FONT, 4.0, (0, 255, 0), 4, LINE)

        self._now_view[98:98 + h_s, 712:712 + w_s, :] = km_score_area

    # ####################################### update and draw score  #######################################

    def update_gps_info(self, speed, location, stake_id, sub_dis, last_stake_id):
        """更新速度和位置"""
        self._now_speed = speed
        self._now_location = location
        self._now_stake_id = stake_id
        self._sub_dis = sub_dis
        self._last_stake_id = last_stake_id

    def _show_speed_location(self):
        """显示时间速度和经纬度"""
        time_area = self._time_bg.copy()
        speed_and_location_area = self._speed_and_location_bg.copy()
        h_s, w_s, _ = speed_and_location_area.shape
        h_t, w_t, _ = time_area.shape

        local_time = time.strftime("%Y-%m-%d   %H:%M:%S", time.localtime())
        if self._now_location is not None:
            speed_and_location_text = '{:0.2f}km/h\n\n{:0.6f} {:0.6f}'.format(self._now_speed * 3.6, self._now_location[0], self._now_location[1])
        else:
            speed_and_location_text = '{:0.2f}km/h\n\n 未知'.format(self._now_speed * 3.6)

        time_area = Window.change_cv2_draw(time_area, local_time, (18, 0), 21, (0, 255, 255))  # 中文
        speed_and_location_area = Window.change_cv2_draw(speed_and_location_area, speed_and_location_text, (0, 0), 15,
                                                         (0, 255, 255))
        # time
        self._now_view[25:25 + h_t, 1110:1110 + w_t, :] = time_area
        # speed and location
        self._now_view[16:16 + h_s, 50:50 + w_s, :] = speed_and_location_area

    # ####################################### 实时显示4路视频流  #######################################

    def _show_real_time_stream(self):
        """实时显示4路视频流"""
        if self._cams is None:
            return
        for cam_id, cam in self._cams.items():
            img = cam.read()
            if img is None:
                img = np.zeros((300, 320, 3), dtype=np.uint8)  # 当前画面读取识别，显示黑屏
            else:
                img = cv2.resize(img, (320, 300))
            img = Window.change_cv2_draw(img, cam_id_num_to_chinese[cam_id], (10, 22), 20, (0, 0, 255))  # 中文
            if cam_id == '0':
                self._now_view[580:580 + 300, 28:28 + 320] = img
            elif cam_id == '1':
                self._now_view[580:580 + 300, 712:712 + 320] = img
            elif cam_id == '2':
                self._now_view[580:580 + 300, 1052:1052 + 320] = img
            elif cam_id == '3':
                self._now_view[580:580 + 300, 368:368 + 320] = img
        # time.sleep(0.01)

    # ####################################### 线程实时刷新结果，并监听键盘  #######################################
    last_time = 0

    def _update_view(self):
        """线程实时刷新结果，并监听键盘"""
        while True:
            if self._show_enable:
                if self._now_view is not None:
                    # self._view_lock.acquire()
                    self.live.read_frame(self._now_view)
                    self._draw_real_time_score()
                    self._draw_coefficient()
                    self._draw_km_score()
                    self._show_speed_location()
                    self._show_real_time_stream()
                    self.live.read_frame(self._now_view)
                    # self.live.frame = self._now_view
                    show_view = cv2.resize(self._now_view, (self._screen_width, self._screen_height))
                    cv2.imshow(WINDOW_NAME, show_view)
                    # self._view_lock.release()
                key = cv2.waitKey(1)
                if key == 27:  # ESC key: quit program
                    if self._now_view is not None:
                        show_view = Window.change_cv2_draw(self._now_view, "正在关闭系统...",
                                                           (0, 0),
                                                           35,
                                                           (255, 0, 0))
                        show_view = cv2.resize(show_view, (self._screen_width, self._screen_height))
                        cv2.imshow(WINDOW_NAME, show_view)
                        cv2.waitKey(1)
                    self._is_show = False
                    break
                if key == ord('H') or key == ord('h'):  # Toggle help/fps/gpu
                    self._show_fps = not self._show_fps
                elif key == ord('F') or key == ord('f'):  # Toggle fullscreen
                    self._full_screen = not self._full_screen
                    self.set_full_screen(self._full_screen)
            else:
                break

    @property
    def is_show(self):
        """:return 返回是否退出"""
        return self._is_show

    def destroy(self):
        """清除"""
        if self.live.enable:
            self.live.process.terminate()
            self.live.process.join()
        self._show_enable = False
        cv2.destroyAllWindows()


win = Window(enable=True)

if __name__ == "__main__":
    win = Window(enable=False)
    win.show_start_up()
