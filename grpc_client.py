# grpc_client.py

import grpc
import cv2
import numpy as np
from io import BytesIO
import video_service_pb2
import video_service_pb2_grpc

class GRPCClient:
    def __init__(self):
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = video_service_pb2_grpc.VideoServiceStub(self.channel)

    def stream_video_data(self):
        for response in self.stub.StreamVideo(video_service_pb2.Empty()):
            image_bytes = response.data
            x = response.x
            y = response.y
            img_array = np.asarray(bytearray(image_bytes), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            yield img, x, y

