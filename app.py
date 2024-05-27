from flask import Flask, render_template, Response, jsonify
import grpc
import video_service_pb2
import video_service_pb2_grpc

app = Flask(__name__)

# gRPC channel and stub setup
channel = grpc.insecure_channel('localhost:50051')
stub = video_service_pb2_grpc.VideoServiceStub(channel)

@app.route('/')
def index():
    return render_template('index.html')

def generate():
    for image_data in stub.StreamVideo(video_service_pb2.Empty()):
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + image_data.data + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/odom_data')
def odom_data():
    try:
        response = stub.GetOdometryData(video_service_pb2.Empty())
        return jsonify({
            'x': response.x,
            'y': response.y
        })
    except grpc.RpcError as e:
        print(f"Error fetching odometry data: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
