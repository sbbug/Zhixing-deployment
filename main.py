"""
-------------------------------------------------
   File Name:    main.py
   Date:         2019/11/25
   Description:  
-------------------------------------------------
"""

import os
import time
import argparse

# CONSTANTS
DATE_FORMAT = "%Y%m%d_%H%M%S"
DATE_FORMAT_ = "%Y-%m-%d %H:%M:%S"
# OUTPUT = "/media/user/TOSHIBA EXT/ZHIXING/output"
OUTPUT = "/media/user/Elements SE/ZHIXING/output"


def loop(predictor, score, gps_controller, logger):
    """
    Loop, grab images from camera, and do object detection.
    :param predictor:
    :param score:
    :param gps_controller:
    :param logger:
    :return:
    """

    predictor.start()
    score.start_net_thread()
    # update relative coefficients
    score.cal_traffic_coe(gps_controller.now_location)  # TODO:根据gps获取系数失败
    score.cal_weather_coe(gps_controller.now_location)

    while win.is_show:
        win.update_gps_info(*gps_controller.info)

        if len(predictor) > 0:
            result = predictor.get()
            # score.run_score(result, gps_controller.now_speed, gps_controller.now_stake_id, gps_controller.sub_dis, gps_controller.start_stake_id)
            score.run_score(result, gps_controller.start_stake_id)
            win.update_freq_score(score.rt_five_score_by_freq())
            win.update_coefficient(score.rt_coes())
            win.show_img(result, score.get_cls_coes())

            if gps_controller.is_stake_id_changed:
                score.cal_environment_coe(gps_controller.last_stake_id)
                score_km = score.rt_sum_score()
                win.update_km_score(last_stake_id=gps_controller.last_stake_id,
                                    score=score_km)
                win.clean_cls_idx_count()
                score.send_score_km(
                    {
                        'gps': gps_controller.now_location,
                        'speed': gps_controller.now_speed,
                        'km': score_km,
                        'road_large_num': gps_controller.last_stake_id,
                        'road_large_distance': gps_controller.sub_dis,
                        'time': time.strftime(DATE_FORMAT_, time.localtime(time.time()))
                    }
                )
                gps_controller.cancel_stake_changed_msg()  # cancel
        else:
            # logger.info('Main Loop: Waiting for detecting....')
            time.sleep(1.5)

    predictor.shutdown()
    score.net.stop()
    win.destroy()
    gps_controller.stop()


def parse_args():
    """Parse input arguments."""
    desc = ('This script captures and displays live camera video, '
            'and does real-time object detection with TF-TRT model '
            'on Jetson TX2/TX1/Nano')
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--config', default='/home/user/code/wk/configs/sample.yaml',
                        help='Path to the config file.must be full path', type=str)
    args = parser.parse_args()
    return args


def main(args):
    name = time.strftime(DATE_FORMAT, time.localtime(time.time()))
    output_dir = os.path.join(OUTPUT, name)
    os.makedirs(output_dir, exist_ok=True)

    logger = get_logger(output_dir=output_dir)

    cfg = get_config(config_file=args.config, logger=logger)

    gps_controller = GPSController(enable=True, cfg=cfg["GPS"], logger=logger)

    win.set_cls_dict(cfg['CLS'])

    cams = get_cameras(cam_args=cfg['CAMERAS'], logger=logger)

    win.set_cam_handle(cams)

    predictor = get_predictor(cam_dict=cams,
                              model_cfg_file=cfg['MODEL_FILE'],
                              confidence_threshold=cfg['CONF_TH'],
                              sample_interval=cfg['SAMPLE_INTERVAL'],
                              gps_controller=gps_controller,
                              logger=logger)

    score = Score(logger, cfg['CLS'], name)

    loop(predictor, score=score, gps_controller=gps_controller, logger=logger)

    logger.info('Done.')


if __name__ == '__main__':
    from window import win

    from score import Score
    from gps_controller import GPSController
    from utils.logger import get_logger
    from functions import get_config, get_cameras, get_predictor

    main(parse_args())
