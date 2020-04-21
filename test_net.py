from net.net import NetWork
import cv2
import uuid
import os
import time
from utils.logger import get_logger
from utils.od_utils import read_label_map

if __name__ == "__main__":
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
        dict_d['id'] = str(uuid.uuid1())

        if n >= 50:
            break
        time.sleep(3)

        net.send_data(dict_d)
        n += 1
        print("n--", str(n))
        print("send_queue size is", str(net.getQueueSize()))
