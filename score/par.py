# cls_weight = {
#         "paper":0.15,
#         "rock":0.05,
#         "bow":0.15,
#         "bottle":0.3,
#         "box":0.15,
#         "leaf":0.05,
#         "plastic":0.2
# }
cls_weight = {
    0: 0.15,
    1: 0.30,
    2: 0.20,
    3: 0.05,
    4: 0.15,
    5: 0.05,
    6: 0.15
}
cls_weight_copy = {
    "plastic": 20,
    "bottle": 30,
    "rock": 5,
    "bow": 10,
    "box": 15,
    "leaf": 5,
    "paper": 15,

}
traffic_coe = {
    "0": 1.0,  # 未知
    "1": 1.05,  # 畅通
    "2": 1.15,  # 缓行
    "3": 1.20,  # 拥堵
    "4": 1.25  # 严重拥堵
}
weather_coe = {
    "100": 1.0,
    "305": 1.05,
    "306": 1.05,
    "307": 1.05,
    "400": 1.10,
    "401": 1.10,
    "402": 1.20
}

environment_coe = {
    "0": 1,  # 道路
    "1": 0,  # 隧道
    "2": 1.2,  # 雨棚
    "3": 1  # 大桥
}

environment_road_num = {
    "1": [[956, 958], [793, 981], [987, 989], [990, 992], [1001, 1002]],
    "2": [[991, 993], [993, 995]],
    "3": [[960, 964], [968, 969], [971, 974]],
}

weather_user_key = "8cc570f936744dda89057da7f87b3241"
traffic_user_key = "b3b36cd2aa0ec87f476de3d82bb8ae51"
right_left_start_score = False
NET_STRUCT_PATH = "./configs/net_struct.json"
CAR_NUM = "ACN403"
