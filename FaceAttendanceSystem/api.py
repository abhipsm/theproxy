from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from camera import CameraManager
from database import db
import threading
import cv2
import time

import base64
import numpy as np
from datetime import datetime

app = Flask(__name__)
CORS(app)

camera_manager = CameraManager()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "db_connected": db.is_connected})

@app.route('/api/start_scanner', methods=['POST'])
def start_scanner():
    students = db.get_all_students()
    if students:
        camera_manager.load_known_faces(students)
    return jsonify({"status": "success"})

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"status": "error", "message": "No image provided"}), 400
        
    image_data = data['image']
    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
        
    try:
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        students = camera_manager.process_frame_for_attendance(frame)
        
        # Mark attendance for students who are recorded
        for student in students:
            if student.get('status') == 'recorded' and student.get('id'):
                date_str = datetime.now().strftime("%Y-%m-%d")
                time_str = datetime.now().strftime("%H:%M:%S")
                record_status = db.record_attendance(student['id'], date_str, time_str)
                if record_status == "already_marked":
                    student['status'] = 'already_marked'
                
        return jsonify({"status": "success", "results": students})
    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/capture_registration', methods=['POST'])
def capture_registration():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"status": "error", "message": "No image provided"}), 400
        
    image_data = data['image']
    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
        
    try:
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        success, encoding_or_msg = camera_manager.process_registration_frame(frame)
        if success:
            # Remove the base64 image data before saving to database to prevent schema/size errors
            if 'image' in data:
                del data['image']
            res = db.register_student(data, encoding_or_msg)
            if res:
                return jsonify({"status": "success", "message": "Registered successfully"})
            return jsonify({"status": "error", "message": "DB save failed"}), 500
        return jsonify({"status": "error", "message": encoding_or_msg}), 400
    except Exception as e:
        print(f"Error capturing registration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    admin_data = db.verify_admin(data.get('username'), data.get('password'))
    if admin_data:
        return jsonify({"status": "success", "data": admin_data})
    if data.get('username') == 'main_admin' and data.get('password') == 'main_pass':
        return jsonify({"status": "success", "data": {"role": "main_admin"}})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/api/students', methods=['GET'])
def get_students():
    return jsonify(db.get_all_students() or [])

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    if db.delete_student(student_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Failed to delete student"}), 500

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    return jsonify(db.get_attendance_by_department("dummy") or [])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=True)
