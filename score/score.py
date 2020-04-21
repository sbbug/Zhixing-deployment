"""
-------------------------------------------------
   File Name:    score.py
   Date:         2019/12/4
   Description:
-------------------------------------------------
"""
from .par import cls_weight, cls_weight_copy, right_left_start_score, CAR_NUM, environment_coe, environment_road_num
from .functions import cal_dust_coe, cal_wea_coe_by_gps, cal_tra_coe, get_net_struct
from utils.visualization import BBoxVisualization
import uuid
from net.net import NetWork


class Score:

    def __init__(self, log=None, cls_dict=None, name=None):
        self.cls_dict = cls_dict
        self.now_camera_num = 4  # cameras' number
        self.now_cam_info = dict()  # each camera' info
        self.need_score_cam = ['0', '3', '1', '2']  # head and back camera num
        self.dust_coe = 0.0
        self.traffic_coe = 1.0
        self.weather_coe = 1.0
        self.environment_coe = 1.0
        self.scores = {
            'h_s': 100.0,
            'b_s': 100.0,
            'c_s': 100.0,
            'r_s': '1',
            'l_s': '1'
        }
        self.head_scores = list()  # store old scores
        self.back_scores = list()  # store old scores
        self.left_scores = list()
        self.right_scores = list()
        self.logger = log

        # draw image
        self._vis = BBoxVisualization(cls_dict)
        # a time -- 0,1,2,3
        self.t_s = dict()
        #
        self.net = NetWork(cls_dict, log, name)
        # cal number of cls according to km
        self.cls_km_dict = dict()
        self.cls_km_dict['0'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['3'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['1'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['2'] = [0 for _ in range(len(self.cls_dict))]

    # when stake changes,set cls_km_dict zero
    def clear_cls_km_dict(self):
        self.cls_km_dict['0'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['3'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['1'] = [0 for _ in range(len(self.cls_dict))]
        self.cls_km_dict['2'] = [0 for _ in range(len(self.cls_dict))]

    # cal cls
    def __cal_cls_km_dict(self, cam_id, cls):
        '''
        :param cam_id:
        :param cls:
        :return:
        '''
        for idx in cls:
            self.cls_km_dict[cam_id][idx] += 1

    # get cls_km_dict
    def get_cls_km_dict(self):
        '''
        :return:
        format:{
         ‘0’：[],
         '3':[],
         ....
        }
        '''

        return self.cls_km_dict

    # start net thread
    def start_net_thread(self):

        if not self.net.thread_running:
            self.logger.info("start net thread ")
            self.net.start()

    # when system init ,call the function once
    def cal_weather_coe(self, gps=None):
        '''
        :param gps: (0,0) tuple
        :return:
        '''
        if gps is None:
            gps = (118.936854, 32.105107)
        else:
            gps = tuple(gps)
        self.weather_coe = cal_wea_coe_by_gps(gps=gps, logger=self.logger)

    # call the function per km
    def cal_traffic_coe(self, gps=None):
        '''
        :param gps: (0,0) tuple
        :return:
        '''
        if gps is None:
            gps = (118.936854, 32.105107)

        else:
            gps = tuple(gps)

        self.traffic_coe = cal_tra_coe(gps=gps, logger=self.logger)

    # front camera scoring
    def __head_score(self, head_info):
        '''
        :param head_info: type:dict format
        :return:
        '''
        cls_total = sum(head_info['cls'].values())
        h_s = 0
        cls_freq_d = head_info['cls']
        if cls_total == 0:
            pass
        else:
            for c in cls_freq_d.keys():
                h_s += cls_weight[c] * (c / cls_total) * 100

        if 100 - h_s <= 0:
            return 0.0

        return round(100.0 - h_s, 1)

    # back camera scoring
    def __back_score(self, back_info):
        '''
        :param back_info:
        :return:
        '''
        cls_total = sum(back_info['cls'].values())
        b_s = 0
        cls_freq_d = back_info['cls']
        if cls_total == 0:
            pass
        else:
            for c in cls_freq_d.keys():
                b_s += cls_weight[c] * (c / cls_total) * 100

        rt_bs = 100 - b_s * (1 - self.dust_coe)
        self.dust_coe = self.__damp_dust_coe(self.dust_coe)  # after using it ,set 1.0 for next image to update
        if rt_bs < 0:
            return 0.0
        return round(rt_bs, 1)

    # damp dust_coe
    def __damp_dust_coe(self, dust_coe):
        '''
        :param dust_coe:
        :return:
        '''

        return dust_coe / 2

    def cal_environment_coe(self, stake_id):
        '''
        :param stake_id:
        :return:
        '''
        env_road = '1'
        for k in environment_road_num.keys():
            flag = False
            for interval in environment_road_num[k]:
                if stake_id >= interval[0] and stake_id <= interval[1]:
                    print("\n now env_road :", env_road, "\n")
                    env_road = k
                    flag = True
                    break
            if flag is True:
                break

        self.environment_coe = environment_coe[env_road]

    # front and back comparing
    def __comp_score(self, h_s, b_c):
        '''
        :param h_s:
        :param b_c:
        :return:
        '''

        if b_c - h_s < 0:
            return 0.0

        return round(b_c - h_s, 1)

    # front back comp score right_level left_level
    def rt_five_score_by_freq(self):
        '''
        :return: type {'h_s':h_s,'b_s':b_s,'c_s':c_s,'r_s':,'l_s':,}
        '''
        self.scores['c_s'] = self.__comp_score(self.scores['h_s'], self.scores['b_s'])
        return self.scores

    # sum comp_score
    def rt_sum_score(self):
        '''
        :return:{'comp_sum_score':,'head_sum_score':,'back_sum_score':,'sum_s':}
        '''
        sum_scores = dict()

        sum_scores['head_sum_score'] = self.__sum_score_by_avg(self.head_scores)
        sum_scores['back_sum_score'] = self.__sum_score_by_avg(self.back_scores)
        sum_scores['comp_sum_score'] = self.__sum_comp_score(self.head_scores, self.back_scores)
        sum_scores['sum_s'] = self.__sum_score_by_coes(self.back_scores)

        self.head_scores.clear()  # clear prepared to next km
        self.back_scores.clear()  # clear prepared to next km

        if not right_left_start_score:
            sum_scores['left_sum_level'] = '3'
            sum_scores['right_sum_level'] = '2'
        else:
            sum_scores['left_sum_level'] = self.get_level(sum(self.left_scores) / len(self.left_scores))
            sum_scores['right_sum_level'] = self.get_level(sum(self.right_scores) / len(self.right_scores))
            self.right_scores.clear()  # clear
            self.left_scores.clear()

        return sum_scores

    # for sum_head_score ,sum_back_score
    def __sum_score_by_coes(self, scores):
        '''
        :param scores:
        :return:
        '''
        m = len(scores)
        if m == 0:
            return 0.0
        sum_s = 0.0
        for p_s in scores:
            sum_s += (p_s * self.traffic_coe + p_s * self.environment_coe + p_s * self.weather_coe) / 3

        return round(sum_s / m, 1)

    # for sum_head_score ,sum_back_score by average
    def __sum_score_by_avg(self, scores):
        '''
        :param scores:
        :return:
        '''
        m = len(scores)
        if m == 0:
            return 0.0
        sum_s = sum(scores)

        return round(sum_s / m, 1)

    # for sum_comp_score
    def __sum_comp_score(self, head_scores_list, back_scores_list):
        '''
        :param head_scores_list:
        :param back_scores_list:
        :return:
        '''

        len_list = max(len(head_scores_list), len(back_scores_list))

        if len_list == 0:
            return 0.0

        head_scores_list_avg = sum(head_scores_list) / len_list
        back_scores_list_avg = sum(back_scores_list) / len_list

        return round(back_scores_list_avg - head_scores_list_avg, 1)

    # start four camera score
    def start_score(self):
        '''
        :return:
        '''
        self.scores['h_s'] = self.__head_score(self.now_cam_info['0'])
        self.scores['b_s'] = self.__back_score(self.now_cam_info['3'])
        self.scores['c_s'] = self.__comp_score(self.scores['h_s'], self.scores['b_s'])
        self.head_scores.append(self.scores['h_s'])
        self.back_scores.append(self.scores['b_s'])

        # left right score
        if right_left_start_score:
            self.scores['r_s'] = self.get_level(self.__head_score(self.now_cam_info['2']))
            self.scores['l_s'] = self.get_level(self.__head_score(self.now_cam_info['1']))
            self.left_scores.append(self.scores['l_s'])
            self.right_scores.append(self.scores['r_s'])
        else:
            self.scores['r_s'] = '2'
            self.scores['l_s'] = '2'

    def get_level(self, score):
        if score < 60:
            return '3'
        elif score >= 60 and score <= 70:
            return '2'
        return '1'

    def send_score_km(self, data):
        '''
        :return:
        '''
        res_send_struct = get_net_struct()
        res_send_struct['type'] = "long_seg"
        res_send_struct['time'] = data['time']
        if data['gps'] is None:
            res_send_struct['longitude'] = ''
            res_send_struct['latitude'] = ''
        else:
            res_send_struct['longitude'] = data['gps'][0]
            res_send_struct['latitude'] = data['gps'][1]
        res_send_struct['car_num'] = CAR_NUM
        res_send_struct['car_speed'] = data['speed']
        res_send_struct['road_large_num'] = 'k' + str(data["road_large_num"])
        res_send_struct['road_large_distance'] = str(data["road_large_distance"])
        res_send_struct['sum_com_s'] = data['km']['comp_sum_score']
        res_send_struct['sum_head_s'] = data['km']['head_sum_score']
        res_send_struct['sum_back_s'] = data['km']['back_sum_score']
        res_send_struct['sum_s'] = data['km']['sum_s']

        self.net.send_data(res_send_struct)

    def _call_cls_count(self, cam_many_dict):
        '''
        :param camera_info: [img_numpy, box, conf, cls, 0.], head
        :return: 0: 'paper'
                  1: 'bottle'
                  2: 'plastic'
                  3: 'rock'
                  4: 'bow'
                  5: 'leaf'
                  6: 'box'
        '''
        res = list()

        if cam_many_dict['0'] is not None and cam_many_dict['0'][3] is not None:
                cls_fre_0 = self.cal_cls_fre(cam_many_dict['0'][3])

                res.append(cls_fre_0['2'])
                res.append(cls_fre_0['1'])
                res.append(cls_fre_0['3'])
                res.append(cls_fre_0['4'])
                res.append(cls_fre_0['6'])
                res.append(cls_fre_0['5'])
                res.append(cls_fre_0['0'])
        return res

    def run_score(self, cam_many_dict, start_send):
        '''
        :param cam_many_dict:
        {
        '0': [img_numpy, box, conf, cls, 0.], head
        '3': [img_numpy, box, conf, cls, 0.], back
        '1': [img_numpy, box, conf, cls, 0.], left
        '2': [img_numpy, box, conf, cls, 0.], right
        'time': task_t['time'],
        'gps': task_t['gps'],
        'speed': 
        'stake_id':
        }
        :param start_send: 当得到起始桩号时，才开始发送实时得分
        :return:
        '''
        # package struct to send
        if start_send is not None:
            self.head_scores.clear()  # clear prepared to next km
            self.back_scores.clear()  # clear prepared to next km
        res_send_struct = get_net_struct()
        res_send_struct['type'] = "point"
        res_send_struct['time'] = cam_many_dict['time']
        if cam_many_dict["gps"] is None:
            return
        res_send_struct['longitude'] = cam_many_dict['gps'][0]
        res_send_struct['latitude'] = cam_many_dict['gps'][1]
        res_send_struct['car_num'] = CAR_NUM
        res_send_struct['car_speed'] = int(cam_many_dict['speed'] * 3.6)
        res_send_struct['road_large_num'] = 'k' + str(cam_many_dict['stake_id'])
        res_send_struct['road_large_distance'] = str(int(cam_many_dict['sub_dis']))
        # update dust
        if cam_many_dict['3'] is not None and cam_many_dict['3'][0] is not None:
            self.dust_coe = cal_dust_coe(cam_many_dict['3'][0])

        # cal head score
        if cam_many_dict['0'] is not None and cam_many_dict['0'][0] is not None:
            cls_fre_0 = self.cal_cls_fre(cam_many_dict['0'][3])
            self.scores['h_s'] = self.__head_score({'cls': cls_fre_0})
            self.head_scores.append(self.scores['h_s'])
            res_send_struct['head_s'] = self.scores['h_s']
            res_send_struct['head_img_label'] = cam_many_dict['0'][0].copy()
            res_send_struct['head_img_labeled'] = self._vis.draw_bboxes(
                cam_many_dict['0'][0],
                cam_many_dict['0'][1],
                cam_many_dict['0'][2],
                cam_many_dict['0'][3],
            )

            # self.__cal_cls_km_dict('0',cam_many_dict['0'][3])
        # cal back score
        if cam_many_dict['3'] is not None and cam_many_dict['3'][0] is not None:
            cls_fre_3 = self.cal_cls_fre(cam_many_dict['3'][3])
            self.scores['b_s'] = self.__back_score({'cls': cls_fre_3})
            self.back_scores.append(self.scores['b_s'])
            res_send_struct['back_s'] = self.scores['b_s']
            res_send_struct['back_img_labeled'] = self._vis.draw_bboxes(
                cam_many_dict['3'][0],
                cam_many_dict['3'][1],
                cam_many_dict['3'][2],
                cam_many_dict['3'][3],
            )
            # self.__cal_cls_km_dict('3', cam_many_dict['3'][3])
        # cal compare score
        res_send_struct['com_s'] = self.__comp_score(self.scores['h_s'], self.scores['b_s'])
        # cal left level
        if cam_many_dict['1'] is not None and cam_many_dict['1'][0] is not None:
            cls_fre_1 = self.cal_cls_fre(cam_many_dict['1'][3])
            self.scores['l_s'] = self.get_level(self.__head_score({'cls': cls_fre_1}))
            self.left_scores.append(self.scores['l_s'])
            if self.scores['l_s'] == '1':
                res_send_struct['left_level'] = self.scores['l_s']
                res_send_struct['left_img_labeled'] = self._vis.draw_bboxes(
                    cam_many_dict['1'][0],
                    cam_many_dict['1'][1],
                    cam_many_dict['1'][2],
                    cam_many_dict['1'][3],
                )
            # self.__cal_cls_km_dict('1', cam_many_dict['1'][3])
        # cal right level
        if cam_many_dict['2'] is not None and cam_many_dict['2'][0] is not None:
            cls_fre_2 = self.cal_cls_fre(cam_many_dict['2'][3])
            self.scores['r_s'] = self.get_level(self.__head_score({'cls': cls_fre_2}))
            self.right_scores.append(self.scores['r_s'])
            if self.scores['r_s'] == '1':
                res_send_struct['right_level'] = self.scores['r_s']
                res_send_struct['right_img_labeled'] = self._vis.draw_bboxes(
                    cam_many_dict['2'][0],
                    cam_many_dict['2'][1],
                    cam_many_dict['2'][2],
                    cam_many_dict['2'][3],
                )
            # self.__cal_cls_km_dict('2', cam_many_dict['2'][3])
        if start_send is not None and cam_many_dict['0'] is not None and cam_many_dict['0'][0] is not None and \
                cam_many_dict['3'] is not None and \
                cam_many_dict['3'][0] is not None:
            res_send_struct['cls_count'] = self._call_cls_count(cam_many_dict)
            self.net.send_data(res_send_struct)

    # run
    def run_score___(self, cam_single_dict):
        '''
        :param cam_single_dict: type:dict format:{"cam_id": k, "cls": cls, "img": img, "gps": (0,0)}
        :return:
        '''
        now_t = cam_single_dict['t']
        cam_id = cam_single_dict['cam_id']
        gps = cam_single_dict['gps']
        # consider head and back camera
        if cam_single_dict['cam_id'] in self.need_score_cam:

            # if cam_id is 3 ,consider updating dust
            if cam_single_dict['cam_id'] == "3" and len(cam_single_dict['cls']) == 0:
                self.dust_coe = cal_dust_coe(cam_single_dict['img'])

            if not self.t_s.__contains__(now_t):
                self.t_s[now_t] = dict()

            if not self.t_s[now_t].__contains__(cam_id):
                self.t_s[now_t][cam_id] = dict()

            if cam_id == "0":
                # store unlabel img
                self.t_s[now_t][cam_id]['head_img_label'] = cam_single_dict['img'].copy()
                self.t_s[now_t][cam_id]['head_img_labeled'] = self._vis.draw_bboxes(
                    cam_single_dict['img'],
                    cam_single_dict['box'],
                    cam_single_dict['conf'],
                    cam_single_dict['cls'],
                )
            elif cam_id == "3":
                self.t_s[now_t][cam_id]['back_img_labeled'] = self._vis.draw_bboxes(
                    cam_single_dict['img'],
                    cam_single_dict['box'],
                    cam_single_dict['conf'],
                    cam_single_dict['cls'],
                )
            elif cam_id == "2":
                self.t_s[now_t][cam_id]['right_img_labeled'] = self._vis.draw_bboxes(
                    cam_single_dict['img'],
                    cam_single_dict['box'],
                    cam_single_dict['conf'],
                    cam_single_dict['cls'],
                )
                self.t_s[now_t][cam_id]['left_img_labeled'] = self.t_s[now_t][cam_id]['right_img_labeled']

            # calculate cls frequency
            cam_single_dict['cls'] = self.cal_cls_fre(cam_single_dict['cls'])

        if cam_id == "0":
            self.scores['h_s'] = self.__head_score(cam_single_dict)
            self.t_s[now_t][cam_id]['head_s'] = self.scores['h_s']
            self.head_scores.append(self.scores['h_s'])
        elif cam_id == "3":
            self.scores['b_s'] = self.__back_score(cam_single_dict)
            self.t_s[now_t][cam_id]['back_s'] = self.scores['b_s']
            self.back_scores.append(self.scores['b_s'])
        elif cam_id == "2":
            # right score
            if right_left_start_score:
                self.scores['r_s'] = self.get_level(self.__head_score(cam_single_dict))
                self.right_scores.append(self.scores['r_s'])
            else:
                self.scores['r_s'] = '2'
            self.t_s[now_t][cam_id]['right_level'] = self.scores['r_s']
        elif cam_id == "1":
            # left score
            if right_left_start_score:
                self.scores['l_s'] = self.get_level(self.__head_score(cam_single_dict))
                self.left_scores.append(self.scores['l_s'])
            else:
                self.scores['l_s'] = '2'
            self.t_s[now_t][cam_id]['left_level'] = self.scores['l_s']
        self.logger.info("self.t_s size is {}".format(len(self.t_s)))
        keys = list(self.t_s.keys())
        for t in keys:
            if len(self.t_s[t]) == 3:
                # data struct to use send data
                res_send_struct = get_net_struct()
                res_send_struct['type'] = "point"
                res_send_struct['time'] = str(t)
                res_send_struct['longitude'] = gps[0]
                res_send_struct['latitude'] = gps[1]
                res_send_struct['head_s'] = self.t_s[t]['0']['head_s']
                res_send_struct['back_s'] = self.t_s[t]['3']['back_s']
                res_send_struct['com_s'] = self.__comp_score(res_send_struct['head_s'], res_send_struct['back_s'])
                res_send_struct['head_img_label'] = self.t_s[t]['0']['head_img_label'].copy()
                res_send_struct['head_img_labeled'] = self.t_s[t]['0']['head_img_labeled'].copy()
                res_send_struct['back_img_labeled'] = self.t_s[t]['3']['back_img_labeled'].copy()
                res_send_struct['right_level'] = self.t_s[t]['2']['right_level']
                res_send_struct['right_img_labeled'] = self.t_s[t]['2']['right_img_labeled'].copy()
                res_send_struct['left_level'] = self.t_s[t]['2']['right_level']
                res_send_struct['left_img_labeled'] = self.t_s[t]['2']['right_img_labeled'].copy()

                self.net.send_data(res_send_struct)
                del self.t_s[t]

    # run
    def run_score_(self, cam_single_dict):
        '''
        :param cam_single_dict: type:dict format:{"cam_id":k, "cls": cls,"gps":(0,0)}
        :return:
        '''
        if len(self.now_cam_info) == self.now_camera_num:
            # start score
            self.start_score()

            self.now_cam_info.clear()

        # consider head and back camera
        if cam_single_dict['cam_id'] in self.need_score_cam:

            # if cam_id is 3 ,consider updating dust
            if cam_single_dict['cam_id'] == "3" and len(cam_single_dict['cls']) == 0:
                self.dust_coe = cal_dust_coe(cam_single_dict['img'])

            # calculate cls frequency
            cam_single_dict['cls'] = self.cal_cls_fre(cam_single_dict['cls'])
            self.now_cam_info[cam_single_dict['cam_id']] = cam_single_dict

    # calculate cls frequency
    def cal_cls_fre(self, cls):
        '''
        :param cls:
        :return:
        '''
        cls_freq = dict()
        for k in cls:
            if cls_freq.__contains__(k):
                cls_freq[k] += 1
            else:
                cls_freq[k] = 1
        return cls_freq

    # return coes
    def rt_coes(self):
        '''
        :return:
        '''
        coes = dict()
        coes['traffic_coe'] = self.traffic_coe
        coes['weather_coe'] = self.weather_coe
        coes['environment_coe'] = self.environment_coe
        coes['dust_coe'] = self.dust_coe
        return coes

    def get_cls_coes(self):
        return cls_weight_copy
