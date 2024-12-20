import os
import cv2
import numpy as np
from pyorbbecsdk import *
from utils import frame_to_bgr_image

"""
Real-time save aligned RGBD information    
"""

class FrameSaver:
    def __init__(self, resolution=(640, 480)):
        self.pipeline = Pipeline()
        self.config = Config()
        self.saved_color_cnt = 0
        self.saved_depth_cnt = 0
        self.has_color_sensor = False
        self.resolution = resolution

        # Create directories for saving images
        self.save_image_dir_color = os.path.join(os.getcwd(), "data/orbbec/rgbd_0818", "rgb")
        self.save_image_dir_depth = os.path.join(os.getcwd(), "data/orbbec/rgbd_0818", "depth")
        os.makedirs(self.save_image_dir_color, exist_ok=True)
        os.makedirs(self.save_image_dir_depth, exist_ok=True)

        self._setup_pipeline()

    def _setup_pipeline(self):
        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            if profile_list is not None:
                color_profile = profile_list.get_default_video_stream_profile()
                self.config.enable_stream(color_profile)
                self.has_color_sensor = True
        except OBError as e:
            print(e)

        depth_profile_list = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        if depth_profile_list is not None:
            depth_profile = depth_profile_list.get_default_video_stream_profile()
            self.config.enable_stream(depth_profile)

        self.pipeline.start(self.config)

    def save_aligned_frames(self):
        frames = self.pipeline.wait_for_frames(100)
        if frames is None:
            return

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if color_frame is not None:
            self._save_color_frame(color_frame, self.saved_color_cnt)
            self.saved_color_cnt += 1

        if depth_frame is not None:
            self._save_depth_frame(depth_frame, self.saved_depth_cnt)
            self.saved_depth_cnt += 1

    def _save_color_frame(self, frame: ColorFrame, index):
        width, height = self.resolution
        image = frame_to_bgr_image(frame)
        if image is None:
            print("Failed to convert frame to image")
            return
        # image = cv2.resize(image, (width, height))
        filename = os.path.join(self.save_image_dir_color, f"{index+1:04d}.png")
        cv2.imwrite(filename, image)

    def _save_depth_frame(self, frame: DepthFrame, index):
        width, height = self.resolution
        scale = frame.get_depth_scale()
        data = np.frombuffer(frame.get_data(), dtype=np.uint16)
        data = data.reshape((frame.get_height(), frame.get_width()))
        # data = cv2.resize(data, (width, height))
        data = data.astype(np.float32) * scale
        filename = os.path.join(self.save_image_dir_depth, f"{index+1:04d}.npy")
        np.save(filename, data)

def main():
    frame_saver = FrameSaver()
    print("Press Enter to save a frame, or 'q' to quit.")
    while True:
        key = input(">")
        if key.lower() == 'q':
            break
        elif key == '':
            frame_saver.save_aligned_frames()
            print(f"Saved frame {frame_saver.saved_color_cnt}")

if __name__ == "__main__":
    main()
