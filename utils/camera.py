"""camera.py

This code implements the Camera class, which encapsulates code to
handle IP CAM, USB webcam or the Jetson onboard camera.  In
addition, this Camera class is further extended to take a video
file or an image file as input.
"""
import logging
import threading
import subprocess
import time
import cv2


def open_cam_rtsp(uri):
    """Open an RTSP URI (IP CAM)."""
    # gst_str = ('rtspsrc location={} latency={} ! '
    #            'rtph264depay ! h264parse ! omxh264dec ! '
    #            'nvvidconv ! '
    #            'video/x-raw, width=(int){}, height=(int){}, '
    #            'format=(string)BGRx ! videoconvert ! '
    #            'appsink').format(uri, latency, width, height)
    # return cv2.VideoCapture(uri, cv2.CAP_GSTREAMER)
    return cv2.VideoCapture(uri)


def open_cam_usb(dev, width, height):
    """Open a USB webcam.

    We want to set width and height here, otherwise we could just do:
        return cv2.VideoCapture(dev)
    """
    gst_str = ('v4l2src device=/dev/video{} ! '
               'video/x-raw, width=(int){}, height=(int){} ! '
               'videoconvert ! appsink').format(dev, width, height)
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)


def open_cam_onboard(width, height):
    """Open the Jetson onboard camera."""
    gst_elements = str(subprocess.check_output('gst-inspect-1.0'))
    if 'nvcamerasrc' in gst_elements:
        # On versions of L4T prior to 28.1, you might need to add
        # 'flip-method=2' into gst_str below.
        gst_str = ('nvcamerasrc ! '
                   'video/x-raw(memory:NVMM), '
                   'width=(int)2592, height=(int)1458, '
                   'format=(string)I420, framerate=(fraction)30/1 ! '
                   'nvvidconv ! '
                   'video/x-raw, width=(int){}, height=(int){}, '
                   'format=(string)BGRx ! '
                   'videoconvert ! appsink').format(width, height)
    elif 'nvarguscamerasrc' in gst_elements:
        gst_str = ('nvarguscamerasrc ! '
                   'video/x-raw(memory:NVMM), '
                   'width=(int)1920, height=(int)1080, '
                   'format=(string)NV12, framerate=(fraction)30/1 ! '
                   'nvvidconv flip-method=2 ! '
                   'video/x-raw, width=(int){}, height=(int){}, '
                   'format=(string)BGRx ! '
                   'videoconvert ! appsink').format(width, height)
    else:
        raise RuntimeError('onboard camera source not found!')
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)


def grab_img(cam):
    """This 'grab_img' function is designed to be run in the sub-thread.
    Once started, this thread continues to grab a new image and put it
    into the global 'img_handle', until 'thread_running' is set to False.
    """
    while cam.thread_running:
        _, cam.img_handle = cam.cap.read()
        if cam.img_handle is None:
            logging.warning('Camera: grab_img(): cap.read() returns None...')
            if cam.args['TYPE'] == 'FILE' or cam.args['TYPE'] == 'RTSP':
                cam.thread_running = False
                cam.cap.release()
                cam.cap = cv2.VideoCapture(cam.args['URL'])
                _, cam.img_handle = cam.cap.read()
                cam.thread_running = True
                logging.info('Camera grab_img(): restart...')
            else:
                break

        if cam.args['TYPE'] == 'FILE':
            time.sleep(1. / cam.fps)
        elif cam.args['TYPE'] == 'RTSP':
            time.sleep(0.01)

    cam.thread_running = False


class Camera:
    """Camera class which supports reading images from theses video sources:

    1. Video file
    2. Image (jpg, png, etc.) file, repeating indefinitely
    3. RTSP (IP CAM)
    4. USB webcam
    5. Jetson onboard camera
    """

    def __init__(self, args):

        assert args['TYPE'] in ['FILE', 'RTSP']
        assert args['ID'] in ['0', '1', '2', '3']

        self.args = args
        self.is_opened = False
        self.use_thread = False
        self.thread_running = False
        self.img_handle = None
        self.img_width = 0
        self.img_height = 0
        self.cap = None
        self.fps = 1000
        self.thread = None

    def open(self):
        """Open camera based on command line arguments."""
        assert self.cap is None, 'Camera is already opened!'

        args = self.args
        self.use_thread = True

        if args['TYPE'] == 'FILE':
            self.cap = cv2.VideoCapture(args['URL'])
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            # ignore image width/height settings here
        elif args['TYPE'] == 'RTSP':
            # TODO
            self.cap = open_cam_rtsp(args['URL'])
        elif args['TYPE'] == 'USB':
            self.cap = open_cam_usb(
                args.video_dev,
                args.image_width,
                args.image_height
            )
        else:  # by default, use the jetson onboard camera
            self.cap = open_cam_onboard(
                args.image_width,
                args.image_height
            )

        if self.cap != 'OK':
            if self.cap.isOpened():
                # Try to grab the 1st image and determine width and height
                _, img = self.cap.read()
                if img is not None:
                    self.img_height, self.img_width, _ = img.shape
                    self.is_opened = True

    def start(self):
        assert not self.thread_running
        if self.use_thread:
            self.thread_running = True
            self.thread = threading.Thread(target=grab_img, args=(self,))
            self.thread.start()

    def stop(self):
        self.thread_running = False
        if self.use_thread:
            self.thread.join()

        self.is_opened = False

    def read(self):
        return self.img_handle

    def release(self):
        assert not self.thread_running
        if self.cap != 'OK':
            self.cap.release()
