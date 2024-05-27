import grpc
from concurrent import futures
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
import video_service_pb2
import video_service_pb2_grpc
import threading

class VideoStreamerServicer(video_service_pb2_grpc.VideoServiceServicer):
    def __init__(self, node):
        self.node = node
        self.image_data = None
        self.odom_data = None
        self.lock = threading.Lock()
        self.node.create_subscription(Image, 'video_source/raw', self.image_callback, 10)
        self.odom_sub = self.node.create_subscription(Odometry, '/odom', self.odom_callback, 10)

    def image_callback(self, msg):
        try:
            # Convert the ROS Image message to a numpy array
            np_arr = np.frombuffer(msg.data, dtype=np.uint8).reshape((msg.height, msg.width, -1))

            # Compress the image using JPEG compression with specified quality
            compression_params = [int(cv2.IMWRITE_JPEG_QUALITY), 15]  # Quality parameter (0-100, lower means higher compression)
            _, compressed_image = cv2.imencode('.jpg', np_arr, compression_params)
            with self.lock:
                self.image_data = compressed_image.tobytes()
        except Exception as e:
            self.node.get_logger().error(f"Error converting and compressing image data: {e}")

    def odom_callback(self, msg: Odometry):
        try:
            with self.lock:
                self.odom_data = msg
            self.node.get_logger().info(f"Odometry data received: x={self.odom_data.pose.pose.position.x}, y={self.odom_data.pose.pose.position.y}")
        except Exception as e:
            self.node.get_logger().error(f"Error extracting odometry data: {e}")

    def StreamVideo(self, request, context):
        try:
            while True:
                with self.lock:
                    if self.image_data:
                        # Create and yield the protobuf message
                        yield video_service_pb2.ImageData(data=self.image_data)
                rclpy.spin_once(self.node, timeout_sec=1.0)  # To achieve frequency > 1 Hz
        except Exception as e:
            self.node.get_logger().error(f"Error streaming video: {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)

    def GetOdometryData(self, request, context):
        try:
            with self.lock:
                if self.odom_data:
                    return video_service_pb2.OdometryData(
                        x=self.odom_data.pose.pose.position.x,
                        y=self.odom_data.pose.pose.position.y
                    )
                else:
                    raise ValueError("Odometry data not available")
        except Exception as e:
            self.node.get_logger().error(f"Error getting odometry data: {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)

def serve():
    rclpy.init()
    node = Node('video_streamer_node')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    video_service_pb2_grpc.add_VideoServiceServicer_to_server(VideoStreamerServicer(node), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("Server stopping...")
    finally:
        server.stop(0).wait()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    serve()
