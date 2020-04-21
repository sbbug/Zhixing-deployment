import cv2
import numpy as np
import requests
import json
from pypinyin import lazy_pinyin
from .par import weather_user_key, weather_coe, traffic_user_key, traffic_coe,NET_STRUCT_PATH
from requests.exceptions import ReadTimeout, ConnectionError, Timeout


# cal environment coefficient
def cal_env_coe(gps):
    pass


# cal traffic coefficient
def cal_tra_coe(gps=None, logger=None):
    '''
    :param gps:
    :return:
    '''
    lo = '116.3057764'
    la = '39.98641364'
    r = 100
    if gps is not None:
        lo = gps[0]
        la = gps[1]

    traffic_url = "https://restapi.amap.com/v3/traffic/status/circle?location={},{}&radius={}&key={}".format(lo, la, r,
                                                                                                             traffic_user_key)
    tra_coe = 1.0
    try:
        response = requests.get(traffic_url, timeout=2)  # timeout is 2s
        print("response.status_code",response.status_code)
        if response.status_code != 200:
            logger.info("gps traffic request has a error,no 200")
        else:
            json_data = response.content.decode('utf-8')
            json_data = json.loads(json_data)
            print("json_data",json_data)
            tra_status = json_data['trafficinfo']['evaluation']['status']

            if len(tra_status) is not 0 and traffic_coe.__contains__(tra_status):
                tra_coe = traffic_coe[tra_status]
            # print(wea_coe_gps)
    except ReadTimeout or Timeout:
        logger.info("traffic_url is timeout")
    except ConnectionError:
        logger.info("traffic_url is ConnectionError")

    return tra_coe


# cal weather coefficient using city name
def cal_wea_coe_by_city(city_name="101280101", logger=None):
    '''
    :param gps:
    :return:
    '''
    weather_url = 'http://t.weather.sojson.com/api/weather/city/'.format(city_name)
    response = requests.get(weather_url)

    if response.status_code != 200:
        logger.info("city weather request has a error,no 200")
    rt_res = response.content.decode('utf-8')
    rt_res = json.loads(rt_res)
    type = rt_res['data']['forecast'][0]['type']
    py = lazy_pinyin(type)
    return "-".join(py)


# cal weather coefficient using gps
def cal_wea_coe_by_gps(gps=None, logger=None):
    '''
    :param gps:
    :param logger:
    :return:
    '''
    lo = '116.3057764'
    la = '39.98641364'
    if gps is not None:
        lo = gps[0]
        la = gps[1]

    weather_url = 'https://free-api.heweather.net/s6/weather/now?location={},{}&key={}'.format(lo, la, weather_user_key)
    wea_coe_gps = 1.0
    try:
        response = requests.get(weather_url, timeout=2)  # timeout is 2s
        if response.status_code != 200:
            logger.info("gps weather request has a error,no 200")
        else:
            json_data = response.content.decode('utf-8')
            json_data = json.loads(json_data)
            wea_status = json_data['HeWeather6'][0]['now']['cond_code']

            if len(wea_status) is not 0 and weather_coe.__contains__(wea_status):
                wea_coe_gps = weather_coe[wea_status]
            print(wea_coe_gps)
    except ReadTimeout or Timeout:
        logger.info("weather_url is timeout")
    except ConnectionError:
        logger.info("weather_url is ConnectionError")

    return wea_coe_gps


# cal dust coefficient
def cal_dust_coe(img, k=0.7, hist_col=30, hist_range=(14, 19)):
    '''
    :params img:原始图片
    :k:除法系数，0-1，越小误检越多，保真越大。
    :hist_col: 直方图列数
    :hist_range: 直方图中灰度取值范围
    :return: 返回灰度系数，0-1，越大灰尘越严重
    '''

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist_cv = cv2.calcHist([gray_img], [0], None, [hist_col], [0, 256])
    hist_cv = hist_cv.ravel()
    a = np.sum(hist_cv[hist_range[0]:hist_range[1]])
    b = np.sum(hist_cv[:hist_range[0]]) + np.sum(hist_cv[hist_range[1]:])

    dust_value = a / (a + k * b+0.1)
    return dust_value

def get_net_struct():
    # 文件异常处理
    result = dict()
    result['id'] =""
    result['type'] =""
    result['time'] =""
    result['longitude'] =132.3232
    result['latitude'] =123.4566
    result['road_large_num'] ="k100"
    result['road_large_distance'] ="188"
    result['head_s'] =50.0
    result['back_s'] =100.0
    result['com_s'] =50.0
    result['head_img_labeled'] =""
    result['back_img_labeled'] =""
    result['right_level'] =""
    result['right_img_labeled'] =""
    result['left_level'] =""
    result['left_img_labeled'] =""
    result['car_num'] ="no1"
    result['sum_com_s'] =5
    result['sum_head_s'] =0.0
    result['sum_back_s'] =100.0
    result['sum_s'] =70.0

    return result
if __name__ == "__main__":
    # cal_wea_coe_by_city()
    # cal_wea_coe_by_gps()
    cal_tra_coe()