import pyrealsense2 as rs
import numpy as np
import cv2
import os
import re
import threading

"""
Real-time display and save aligned Realsense RGBD information for d435i 
"""

class Realsense:
    def __init__(self, save_path=None):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        
        # Get device information and configuration
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = self.config.resolve(pipeline_wrapper)
        self.device = pipeline_profile.get_device()

        found_rgb = False
        for s in self.device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                print("Connected camera!")
                break
        if not found_rgb:
            raise Exception("depth camera with rgb is required")

        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

        # Start streaming
        self.profile = self.pipeline.start(self.config)

        # Create an alignment object
        self.align_to = rs.stream.color
        self.align = rs.align(self.align_to)

        """ The following section is the added code for saving information """
        # Set default save path
        if save_path is None:
            self.save_path = os.path.join(os.getcwd(), "data/realsense/0827/scene1")
        else:
            self.save_path = save_path
        os.makedirs(self.save_path, exist_ok=True)

        # Create RGB and Depth folders
        self.rgb_path = os.path.join(self.save_path, "image")
        self.depth_path = os.path.join(self.save_path, "depth")
        os.makedirs(self.rgb_path, exist_ok=True)
        os.makedirs(self.depth_path, exist_ok=True)

        # Find the maximum index of existing files
        self.image_counter = self.find_max_image_counter()

    def find_max_image_counter(self):
        pattern = re.compile(r"(\d+)")
        max_counter = 0

        for filename in os.listdir(self.rgb_path):
            match = pattern.search(filename)
            if match:
                number = int(match.group(1))
                if number > max_counter:
                    max_counter = number

        for filename in os.listdir(self.depth_path):
            match = pattern.search(filename)
            if match:
                number = int(match.group(1))
                if number > max_counter:
                    max_counter = number

        return max_counter + 1

    def save_rgbd(self, color_image, depth_image):
        color_path = os.path.join(self.rgb_path, f"{self.image_counter:04d}.png")
        cv2.imwrite(color_path, color_image)

        depth_path = os.path.join(self.depth_path, f"{self.image_counter:04d}.npy")
        np.save(depth_path, depth_image)

        print(f"Saved RGB image to {color_path}")
        print(f"Saved Depth image to {depth_path}")

        self.image_counter += 1

    def run(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)

        aligned_depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not aligned_depth_frame or not color_frame:
            return None, None

        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        images = np.hstack((color_image, depth_colormap))

        cv2.namedWindow('Align RGBD', cv2.WINDOW_NORMAL)
        cv2.imshow('Align RGBD', images)

        return color_image, depth_image

def main():
    realsense = Realsense()
    print("Press Enter to save a frame, or 'q' to quit.")
    
    while True:
        rgb, depth = realsense.run()
        if rgb is None or depth is None:
            break

        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter key
            # Start a new thread to save RGBD images
            threading.Thread(target=realsense.save_rgbd, args=(rgb.copy(), depth.copy())).start()
            print("Saving frame...")

        if key == ord('q') or key == 27:  # 'q' or Esc key
            cv2.destroyAllWindows()
            break

if __name__ == "__main__":
    main()