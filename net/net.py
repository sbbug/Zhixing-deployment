"""
-------------------------------------------------
   File Name:    main.py
   Date:         2019/12/19
   Description:
-------------------------------------------------
"""
from utils.visualization import BBoxVisualization
from net.par import net_url, time_out, disk_dir, date_format
import requests
import json
import cv2
import base64
from queue import Queue
from threading import Thread
import uuid
from requests.exceptions import ReadTimeout, ConnectionError, Timeout
import os
import time
from utils.logger import get_logger


class NetWork:

    def __init__(self, cls_dict, log, log_path, max_size=None):
        if max_size == None:
            self.max_size = 100
        else:
            self.max_size = max_size

        self.send_queue = Queue(self.max_size)
        self.logger = log
        self.display = BBoxVisualization(cls_dict)
        self.thread_send = None
        self.use_thread = True
        self.thread_running = False
        self.log_path = log_path

    def getQueueSize(self):
        '''
        :return:
        '''
        return self.send_queue.qsize()

    # main.py callback send_data
    def send_data(self, dict_data):
        '''
        :param dict_data: format:
        {
          type: point,short_seg,long_seg string
          time: yyyy-MM-dd HH:mm:ss   string
          longitude:132.3232  float
          latitude:123.4566   float
          road_large_num:k100  string
          head_s:50.0 float
          back_s:100.0 float
          com_s:50.0 float
          head_img_labeled:numpy
          back_img_labeled:numpy
          right_level:'3'
          right_img_labeled:numpy
          left_level:'3'
          left_img_labeled:numpy
          car_num:no1 string
          car_speed:5 integer
          sum_com_s:60.0 float
          sum_head_s:70.0 float
          sum_back_s:70.0 float
          sum_s:70.0 integer
        }
        :return:
        '''

        # first save data to disk
        if dict_data['type'] == 'point':
            self.__save_disk(dict_data)
        # then process data
        json_data = self.__process_data(dict_data)
        # send data to queue
        if self.send_queue.qsize()<self.max_size:
            self.send_queue.put(json_data)
        else:
            self.send_queue.get()
            self.send_queue.put(json_data)
            self.logger.info("the send_queue is full, json_data is gived up")

    # before sending ,save data to local  disk
    def __save_disk(self, dict_data):

        date_img_path = os.path.join(disk_dir, self.log_path, "images")
        os.makedirs(date_img_path, exist_ok=True)

        # date_head_camera_path = os.path.join(date_img_path, "h_c")
        # if not os.path.exists(date_head_camera_path):
        #     os.mkdir(date_head_camera_path)
        # date_back_camera_path = os.path.join(date_img_path, "b_c")
        # if not os.path.exists(date_back_camera_path):
        #     os.mkdir(date_back_camera_path)
        train_head_data_path = os.path.join(date_img_path, "train")
        if not os.path.exists(train_head_data_path):
            os.mkdir(train_head_data_path)

        # cv2.imwrite(os.path.join(date_head_camera_path, str(time.time()) + ".jpg"), dict_data['head_img_labeled'])
        # cv2.imwrite(os.path.join(date_back_camera_path, str(time.time()) + ".jpg"), dict_data['back_img_labeled'])
        cv2.imwrite(os.path.join(train_head_data_path, str(time.time()) + ".jpg"), dict_data['head_img_label'])

        del dict_data['head_img_label']

    def __dict_to_json(self, dict_data):
        '''
        :param dict_data:
        :return:
        '''
        json_data = json.dumps(dict_data)
        return json_data

    def __process_data(self, dict_data):
        '''
        :param dict_data:
        :return:
        '''
        if dict_data['head_img_labeled'] is not '':  # -1 notes null
            # resize
            dict_data['head_img_labeled'] = cv2.resize(dict_data['head_img_labeled'], (300, 300))
            # encode
            dict_data['head_img_labeled'] = self.numpy_to_base64(dict_data['head_img_labeled'])
            #dict_data['head_img_labeled'] = ''
        if dict_data['back_img_labeled'] is not '':
            # resize
            dict_data['back_img_labeled'] = cv2.resize(dict_data['back_img_labeled'], (300, 300))
            # encode
            dict_data['back_img_labeled'] = self.numpy_to_base64(dict_data['back_img_labeled'])
            #dict_data['back_img_labeled'] = ''
        if dict_data['right_img_labeled'] is not '':
            # resize
            dict_data['right_img_labeled'] = cv2.resize(dict_data['right_img_labeled'], (300, 300))
            # encode
            dict_data['right_img_labeled'] = self.numpy_to_base64(dict_data['right_img_labeled'])
            #dict_data['right_img_labeled'] = ''

        if dict_data['left_img_labeled'] is not '':
            # resize
            dict_data['left_img_labeled'] = cv2.resize(dict_data['left_img_labeled'], (300, 300))
            # encode
            dict_data['left_img_labeled'] = self.numpy_to_base64(dict_data['left_img_labeled'])
            #dict_data['left_img_labeled'] = ''


        # add uuid
        dict_data['id'] = str(uuid.uuid1())
        dict_json = self.__dict_to_json(dict_data)
        return dict_json

    def numpy_to_base64(self, data_np):
        '''
        :param data_np:
        :return:
        '''
        retval, buffer = cv2.imencode('.jpg', data_np)  # image extension .jpg
        img_byte = base64.b64encode(buffer)
        img_str = img_byte.decode('ascii')

        return img_str

    # start thread
    def start(self):
        '''
        :return:
        '''
        if self.use_thread:
            self.thread_running = True
            self.thread_send = Thread(target=self.__start_send, )
            self.thread_send.start()
            self.logger.info("started data send-thread ")

    #  stop thread_send
    def stop(self):
        '''
        :return:
        '''
        self.thread_running = False
        if self.use_thread:
            self.thread_send.join()

    # define thread to send data from queue
    def __start_send(self):
        '''
        :param json_data:
        :return:
        '''
        while self.thread_running:
            if self.send_queue.qsize() > 0:
                self.logger.info("now net queue is {}".format(self.send_queue.qsize()))
                json_data = self.send_queue.get()
                try:
                    # timeout is 3s
                    res = requests.post(net_url, data=json_data, headers={'content-type': 'application/json'},
                                        timeout=time_out)
                    res = json.loads(res.text)
                    self.logger.info(res)
                    if res['code'] == 200:
                        continue
                except ReadTimeout or Timeout:
                    count = 0
                    while count < 3:

                        try:
                            count += 1
                            res = requests.post(net_url, data=json_data, headers={'content-type': 'application/json'},
                                                timeout=time_out)
                            res = json.loads(res.text)
                            if res['code'] == 200:
                                break
                        except ConnectionError:
                            self.logger.info("ConnectionError")
                        except ReadTimeout or Timeout:
                            self.logger.info("netword send is timeout")
                except ConnectionError:
                    self.logger.info("ConnectionError")
            else:
                self.logger.info('Net: Waiting for sending data....')
                time.sleep(2)

if __name__ == "__main__":
    from utils.od_utils import read_label_map

    DATE_FORMAT = "%Y%m%d_%H%M%S"
    OUTPUT = "/media/user/TOSHIBA EXT/ZHIXING/output"
    name = time.strftime(DATE_FORMAT, time.localtime(time.time()))
    output_dir = os.path.join(OUTPUT, name)
    os.makedirs(output_dir, exist_ok=True)
    logger = get_logger(output_dir=output_dir)
    cls_dict = read_label_map(
        "/media/user/TOSHIBA EXT/ZHIXING/resources/models/ssd_inception_v2_zh/pascal_label_map.pbtxt")
    net = NetWork(cls_dict, logger, name)
    net.start()
    n = 0
    # print(dict_d['head_img_labeled'])
    while True:
        dict_d = dict()
        dict_d['type'] = 'point'
        dict_d['time'] = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        dict_d['longitude'] = 132.323212
        dict_d['latitude'] = 123.456634
        dict_d['road_large_num'] = 'k100'
        dict_d['head_s'] = 50.0
        dict_d['back_s'] = 100.0
        dict_d['com_s'] = 50.0
        dict_d['head_img_labeled'] = cv2.imread("./net/image_0_000049_2117.jpg")
        dict_d['back_img_labeled'] = cv2.imread("./net/image_0_000049_2117.jpg")
        dict_d['right_level'] = '3'
        dict_d['right_img_labeled'] = cv2.imread("./net/image_0_000049_2117.jpg")
        dict_d['left_level'] = '3'
        dict_d['left_img_labeled'] = cv2.imread("./net/image_0_000049_2117.jpg")
        dict_d['car_num'] = 'No1'
        dict_d['car_speed'] = '8'
        dict_d['sum_com_s'] = 60.0
        dict_d['sum_head_s'] = 70.0
        dict_d['sum_back_s'] = 70.0
        dict_d['sum_s'] = 70.0
        dict_d['id'] = str(uuid.uuid1())

        if n >= 50:
            break
        time.sleep(3)

        net.send_data(dict_d)
        n += 1
        print("n--", str(n))
        print("send_queue size is", str(net.getQueueSize()))
