"""
-------------------------------------------------
   File Name:    logger.py
   Date:         2019/11/26
   Description:  
-------------------------------------------------
"""

import os
import sys
import logging

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(output_dir, level=logging.DEBUG):
    logger = logging.getLogger(output_dir)
    # Ask tensorflow logger not to propagate logs to parent
    # (which causes duplicated logging)
    # logging.getLogger('tensorflow').propagate = False
    logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt=DATE_FORMAT)

    if level == logging.DEBUG:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    fh = logging.FileHandler(os.path.join(output_dir, 'log.txt'), mode='w')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger
