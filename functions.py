"""
-------------------------------------------------
   File Name:    functions.py
   Date:         2019/11/26
   Description:  
-------------------------------------------------
"""

import os
import sys

import yaml
# import numpy as np
# import tensorflow as tf


from utils.camera import Camera
from detectron2.config import get_cfg
from predictor import AsyncPredictor

# from utils.od_utils import read_label_map, build_trt_pb, load_trt_pb, detect

MODEL_ZOO = "/media/user/TOSHIBA EXT/ZHIXING/resources/models"


# def build_model(model_args, logger):
#     # parse model_args
#     model_name = model_args['NAME']
#     model_dir = os.path.join(MODEL_ZOO, model_name)
#     labelmap_file = os.path.join(model_dir, model_args['LABEL_MAP'])
#     pb_path = os.path.join(model_dir, '{}_trt.pb'.format(model_name))
#     config_path = os.path.join(model_dir, model_args['CONFIG_PATH'])
#     checkpoint_path = os.path.join(model_dir, model_args['CHECKPOINT_PATH'])
#     do_build = model_args['BUILD']
#
#     if do_build:
#         logger.info('Building TRT graph and saving to pb: %s.' % pb_path)
#         build_trt_pb(config_path=config_path,
#                      checkpoint_path=checkpoint_path,
#                      pb_path=pb_path)
#     logger.info('Loading TRT graph from pb: %s.' % pb_path)
#     trt_graph = load_trt_pb(pb_path)
#
#     # build the class (index/name) dictionary from labelmap file
#     logger.info('Reading label map...')
#     cls_dict = read_label_map(labelmap_file)
#
#     logger.info('Starting up TensorFlow session...')
#     tf_config = tf.ConfigProto()
#     tf_config.gpu_options.allow_growth = True
#     tf_sess = tf.Session(config=tf_config, graph=trt_graph)
#
#     # if do_tensorboard:
#     #     logger.info('writing graph summary to TensorBoard')
#     #     write_graph_tensorboard(tf_sess, log_path)
#
#     logger.info('Warming up the TRT graph with a dummy image.')
#     od_type = 'faster_rcnn' if 'faster_rcnn' in model_name else 'ssd'
#     dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
#     _, _, _ = detect(dummy_img, tf_sess, conf_th=.3, od_type=od_type)
#
#     return tf_sess, od_type, cls_dict


def get_config(config_file, logger):
    logger.info('Read config from: %s', config_file)
    with open(config_file, 'r') as f:
        cfg = yaml.load(f)

    logger.info('Config: {}'.format(cfg))
    return cfg


def get_cameras(cam_args, logger):
    logger.info('Opening camera device/file ...')

    cams = {}
    for arg in cam_args:
        cam = Camera(arg)
        cam.open()
        if cam.is_opened:
            cams[arg['ID']] = cam
        else:
            # TODO: logger.warning()
            logger.warning("Failed to open camera:", arg["ID"])
            sys.exit('Failed to open camera!')

    return cams


def get_predictor(model_cfg_file, cam_dict, confidence_threshold, sample_interval, gps_controller, logger):
    cfg = get_cfg()
    cfg.merge_from_file(model_cfg_file)

    # Set score_threshold for builtin models
    cfg.MODEL.RETINANET.SCORE_THRESH_TEST = confidence_threshold
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = confidence_threshold
    cfg.MODEL.PANOPTIC_FPN.COMBINE.INSTANCES_CONFIDENCE_THRESH = confidence_threshold
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7  # only has one class (balloon)
    cfg.INPUT.MAX_SIZE_TEST = 700
    cfg.freeze()

    predictor = AsyncPredictor(cfg, cam_dict=cam_dict, sample_interval=sample_interval, gps_controller=gps_controller,
                               logger=logger)

    return predictor
