"""
-------------------------------------------------
   File Name:    predictor.py
   Author:       Zhonghao Huang
   Date:         2019/12/17
   Description:  
-------------------------------------------------
"""

import time
import threading
from queue import Queue
import numpy as np

import torch

import detectron2.data.transforms as T
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.data import MetadataCatalog
from detectron2.modeling import build_model

MAX = 100
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class DefaultPredictorBatch:
    """
    Create a simple end-to-end predictor with the given config.
    The predictor takes an BGR image, resizes it to the specified resolution,
    runs the model and produces a dict of predictions.

    This predictor takes care of model loading and input preprocessing for you.
    If you'd like to do anything more fancy, please refer to its source code
    as examples to build and use the model manually.

    Attributes:
        metadata (Metadata): the metadata of the underlying dataset, obtained from
            cfg.DATASETS.TEST.

    Examples:

    .. code-block:: python

        pred = DefaultPredictor(cfg)
        outputs = pred(inputs)
    """

    def __init__(self, cfg):
        self.cfg = cfg.clone()  # cfg can be modified by model
        self.model = build_model(self.cfg)
        self.model.eval()
        self.metadata = MetadataCatalog.get(cfg.DATASETS.TEST[0])

        checkpointer = DetectionCheckpointer(self.model)
        checkpointer.load(cfg.MODEL.WEIGHTS)

        self.transform_gen = T.ResizeShortestEdge(
            [cfg.INPUT.MIN_SIZE_TEST, cfg.INPUT.MIN_SIZE_TEST], cfg.INPUT.MAX_SIZE_TEST
        )

        self.input_format = cfg.INPUT.FORMAT
        assert self.input_format in ["RGB", "BGR"], self.input_format

    @torch.no_grad()
    def __call__(self, original_images):
        """
        Args:
            original_image (np.ndarray): an image of shape (H, W, C) (in BGR order).

        Returns:
            predictions (dict): the output of the model
        """
        batch = []
        for original_image in original_images:
            # Apply pre-processing to image.
            if self.input_format == "RGB":
                # whether the model expects BGR inputs or RGB
                original_image = original_image[:, :, ::-1]

            height, width = original_image.shape[:2]
            image = self.transform_gen.get_transform(original_image).apply_image(original_image)
            image = torch.as_tensor(image.astype("float32").transpose(2, 0, 1))

            inputs = {"image": image, "height": height, "width": width}
            batch.append(inputs)

        predictions = self.model(batch)
        return predictions


def crop(img, k):
    if img is not None and (k == '0'):
        h, w, _ = img.shape
        h1 = h//3
        w1 = w//5
        w2 = w//8
        img = img[h1:, w1: w-w2]
        # img = img[720:, 768:3360]
    elif img is not None and img.shape[0] == 720 and (k == '3'):
        h, w, _ = img.shape
        h1 = h // 3
        w1 = w // 5
        w2 = w // 8
        img = img[h1:, w1: w - w2]
        # img = img[720:, 768:3360]

    return img


class AsyncPredictor:
    def __init__(self, model_cfg, cam_dict, sample_interval, gps_controller, logger):
        self.cams = cam_dict
        self.sample_interval = sample_interval

        self.put_idx = 0
        self.get_idx = 0

        self.task_queue = Queue(MAX)
        self.result_queue = Queue(MAX)

        self._grabbing = True
        self._detecting = True
        self.thread_grab = threading.Thread(target=AsyncPredictor.loop_and_grab, args=(self,))
        self.thread_detect = threading.Thread(target=AsyncPredictor.loop_and_detect, args=(self,))

        self.predictor = DefaultPredictorBatch(model_cfg)

        self.gps_controller = gps_controller
        self.logger = logger

    def start(self):
        self._grabbing = True
        self.thread_grab.start()
        self._detecting = True
        self.thread_detect.start()

    def shutdown(self):
        self.logger.info('Cleaning up...')
        for k in self.cams.keys():
            self.cams[k].stop()  # terminate the sub-thread in camera
            self.cams[k].release()

        self._grabbing = False
        self.thread_grab.join()
        self._detecting = False
        self.thread_detect.join()

    def get(self):

        return self.result_queue.get()

    def loop_and_grab(self):
        for k in self.cams.keys():
            self.cams[k].start()

        self.logger.info('Start grabbing image....')
        while self._grabbing:
            running = False
            for k in self.cams.keys():
                running = running or self.cams[k].is_opened
            if not running:
                break

            task_t = {'0': None, '3': None, '1': None, '2': None,
                      'time': time.strftime(DATE_FORMAT, time.localtime(time.time())),
                      'gps': self.gps_controller.now_location,
                      'speed':self.gps_controller.now_speed,
                      'stake_id':self.gps_controller.now_stake_id,
                      'sub_dis':self.gps_controller.sub_dis}
            for k in self.cams.keys():
                if self.cams[k].is_opened:
                    img = self.cams[k].read()
                    img = crop(img, k)
                    task_t[k] = img

            self.task_queue.put(task_t)
            time.sleep(self.sample_interval)

    def loop_and_detect(self):
        init = True
        while self._detecting:
            if self.task_queue.qsize() > 0:
                # k, img = self.task_queue.get()
                task_t = self.task_queue.get()
                result_t = {'0': None, '3': None, '1': None, '2': None,
                            'time': task_t['time'], 'gps': task_t['gps'],
                            'speed':task_t['speed'],'stake_id':task_t['stake_id'],'sub_dis':task_t['sub_dis']}
                self.logger.info('Get a image form camera, {} left in the queue.'
                                 .format(self.task_queue.qsize()))

                imgs = []
                for k in self.cams.keys():
                    img = task_t[k]
                    if img is not None:
                        imgs.append(img)
                    else:
                        imgs.append(np.zeros((720, 1280, 3)).astype(np.uint8))

                if init:
                    results = self.predictor(imgs)
                    self.task_queue.queue.clear()
                    init = False
                else:
                    results = self.predictor(imgs)

                for i, k in enumerate(['0', '3', '1', '2']):
                    if task_t[k] is None:
                        result_t[k] = [np.zeros((720, 1280, 3)).astype(np.uint8), [], [], [], 0.]
                    else:
                        result = results[i]

                        conf = result['instances']._fields['scores'].data.cpu().tolist()
                        cls = result['instances']._fields['pred_classes'].data.cpu().tolist()
                        box = result['instances']._fields['pred_boxes'].tensor.cpu().tolist()
                        box = [list(map(int, bb)) for bb in box]
                        box = [[bb[1], bb[0], bb[3], bb[2]] for bb in box]

                        result_t[k] = [task_t[k], box, conf, cls, 0.]

                self.result_queue.put(result_t)

            else:
                self.logger.info('Detect Loop: Waiting for grabbing image....')
                time.sleep(self.sample_interval / 8.)

    def __len__(self):
        return self.result_queue.qsize()

    def __call__(self, *args, **kwargs):
        return self.get()
