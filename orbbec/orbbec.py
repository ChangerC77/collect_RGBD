import sys
import os
import json
import time
import numpy as np
import cv2
from pyorbbecsdk import Pipeline, Config, OBSensorType, OBAlignMode, FrameSet, OBFormat, OBError
from utils import frame_to_bgr_image
import png

"""
Real-time display aligned RGBD information
"""

class DataRecorder:
    def __init__(self, folder, record_length=40, resolution=(720, 1280)):
        self.folder = folder
        self.record_length = record_length
        self.resolution = resolution
        self.pipeline = Pipeline()
        self.config = Config()
        self.file_name = 0
        self.align_mode = "HW"
        self.enable_sync = True
        self._make_directories()
        self._configure_pipeline()
        
    # def _make_directories(self):
    #     if not os.path.exists(self.folder + "rgb/"):
    #         os.makedirs(self.folder + "rgb/")
    #     if not os.path.exists(self.folder + "depth/"):
    #         os.makedirs(self.folder + "depth/")

    def _configure_pipeline(self):
        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            try:
                color_profile = profile_list.get_video_stream_profile(self.resolution[0], self.resolution[1], OBFormat.RGB, 30)
            except OBError as e:
                print(e)
                color_profile = profile_list.get_default_video_stream_profile()

            self.config.enable_stream(color_profile)
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
            assert profile_list is not None
            try:
                depth_profile = profile_list.get_video_stream_profile(self.resolution[0], 0, OBFormat.Y16, 30)
            except OBError as e:
                print("Error: ", e)
                depth_profile = profile_list.get_default_video_stream_profile()

            assert depth_profile is not None
            self.config.enable_stream(depth_profile)
        except Exception as e:
            print(e)
            return

        device = self.pipeline.get_device()
        device_info = device.get_device_info()
        device_pid = device_info.get_pid()

        if self.align_mode == 'HW':
            if device_pid == 0x066B:
                self.config.set_align_mode(OBAlignMode.SW_MODE)
            else:
                self.config.set_align_mode(OBAlignMode.HW_MODE)
        elif self.align_mode == 'SW':
            self.config.set_align_mode(OBAlignMode.SW_MODE)
        else:
            self.config.set_align_mode(OBAlignMode.DISABLE)

        if self.enable_sync:
            try:
                self.pipeline.enable_frame_sync()
            except Exception as e:
                print(e)

    def start_recording(self):
        try:
            self.pipeline.start(self.config)
            intrinsics = self.pipeline.get_camera_param().rgb_intrinsic
        except Exception as e:
            print(e)
            return
        
        T_start = time.time()
        flag = True
        while True:
            try:
                frames: FrameSet = self.pipeline.wait_for_frames(100)
                if frames is None:
                    continue
                color_frame = frames.get_color_frame()
                if color_frame is None:
                    continue
                color_image = frame_to_bgr_image(color_frame)
                if color_image is None:
                    print("failed to convert frame to image")
                    continue
                depth_frame = frames.get_depth_frame()
                if depth_frame is None:
                    continue

                depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
                depth_data = depth_data.reshape((self.resolution[1], self.resolution[0]))

                if flag:
                    camera_parameters = {
                        'fx': intrinsics.fx, 'fy': intrinsics.fy,
                        'ppx': intrinsics.cx, 'ppy': intrinsics.cy,
                        'height': intrinsics.height, 'width': intrinsics.width,
                        'depth_scale': depth_frame.get_depth_scale()
                    }
                    with open(self.folder + 'intrinsics.json', 'w') as fp:
                        json.dump(camera_parameters, fp)
                    flag = False

                if time.time() - T_start > 5:
                    filecad = f"{self.folder}/rgb/{int(self.file_name):06d}.png"
                    filedepth = f"{self.folder}/depth/{int(self.file_name):06d}.npy"
                    # cv2.imwrite(filecad, color_image)
                    # np.save(filedepth, depth_data)
                    self.file_name += 1

                if time.time() - T_start > self.record_length + 5:
                    self.pipeline.stop()
                    break

                cv2.imshow('COLOR IMAGE', color_image)
                depth_image = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                depth_image = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)
                depth_image = cv2.addWeighted(color_image, 0.5, depth_image, 0.5, 0)
                cv2.imshow("SyncAlignViewer", depth_image)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.pipeline.stop()
                    break
            except KeyboardInterrupt:
                break
        self.pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        folder = sys.argv[1] + "/"
    except:
        print("Usage: DataRecorder.py <foldername>")
        exit()

    recorder = DataRecorder(folder)
    recorder.start_recording()
