import pyrealsense2 as rs
import numpy as np
import cv2

"""
Real-time display aligned RGBD information for d435i 
"""

class Realsense:
    def __init__(self):
        # Initialize the Realsense pipeline
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        # Get device information and configuration
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = self.config.resolve(pipeline_wrapper)
        self.device = pipeline_profile.get_device()
        device_product_line = str(self.device.get_info(rs.camera_info.product_line))

        found_rgb = False
        for s in self.device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                break
        if not found_rgb:
            raise Exception("depth camera with rgb information is required")

        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

        # Start streaming
        self.profile = self.pipeline.start(self.config)

        # Get the depth scale of the depth sensor
        depth_sensor = self.profile.get_device().first_depth_sensor()
        self.depth_scale = depth_sensor.get_depth_scale()
        print("Depth scale: ", self.depth_scale)

        # Create an alignment object
        self.align_to = rs.stream.color
        self.align = rs.align(self.align_to)

    def run(self):
        try:
            while True:
                # Get color and depth frames
                frames = self.pipeline.wait_for_frames()

                # Align the depth frame to the color frame
                aligned_frames = self.align.process(frames)

                # Get the aligned frames
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                # Verify if the frames are valid
                if not aligned_depth_frame or not color_frame:
                    continue

                depth_image = np.asanyarray(aligned_depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Render the images
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
                images = np.hstack((color_image, depth_colormap))

                cv2.namedWindow('Align RGBD', cv2.WINDOW_NORMAL)
                cv2.imshow('Align RGBD', images)
                key = cv2.waitKey(1)
                # Close the window when 'q' or 'esc' is pressed
                if key & 0xFF == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    break
        finally:
            self.pipeline.stop()

def main():
    realsense = Realsense()
    realsense.run()
    
if __name__ == "__main__":
    main()
  