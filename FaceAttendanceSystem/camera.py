import cv2
import face_recognition
import numpy as np
from datetime import datetime
import time
import math
from ultralytics import YOLO

class CameraManager:
    def __init__(self):
        self.video_capture = None
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.cooldown_dict = {} # student_id: timestamp
        self.COOLDOWN_SECONDS = 300 # 5 minutes cooldown before scanning the same face again
        try:
            self.yolo_model = YOLO("yolov8n.pt")
        except Exception as e:
            self.yolo_model = None
            print("Failed to load YOLO:", e)

    def is_real_human_ml(self, frame, face_location):
        """Passive ML Texture, Contrast, and Glare Analysis for Anti-Spoofing."""
        top, right, bottom, left = face_location
        face_roi = frame[max(0, top):max(0, bottom), max(0, left):max(0, right)]
        if face_roi.size == 0 or face_roi.shape[0] < 10 or face_roi.shape[1] < 10: 
            return False
        
        hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2YCrCb)
        
        y, cr, cb = cv2.split(ycrcb)
        h, s, v = cv2.split(hsv)
        
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        score = 0
        
        # 1. Specular Screen Glare (Phones reflect light heavily)
        glare_ratio = np.sum(v > 230) / float(v.size)
        if glare_ratio > 0.08:
            score += 3 # Obvious phone reflection
        elif glare_ratio > 0.03:
            score += 1
            
        # 2. Blur / Texture (Screens/Photos are often flatter or out of focus)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 12.0:
            score += 3 # Extremely blurry (printed paper)
        elif laplacian_var < 25.0:
            score += 1
            
        # 3. Dynamic Range (2D images compress shadows)
        contrast = np.std(y)
        if contrast < 15.0:
            score += 3 # Completely flat (paper/screen)
        elif contrast < 22.0:
            score += 1
            
        # 4. Unnatural Brightness (Phones emit light, flattening features)
        mean_brightness = np.mean(v)
        brightness_std = np.std(v)
        if mean_brightness > 150 and brightness_std < 20.0:
            score += 2 # Highly unnatural flat brightness
            
        # 5. Blue Light Emission (Phone backlights skew blue)
        b, g, r = cv2.split(face_roi)
        mean_b = np.mean(b)
        mean_r = np.mean(r)
        if mean_b > mean_r + 12:
            score += 3 # Massive blue skew, definitely a screen
        elif mean_b > mean_r + 4:
            score += 1
            
        # If we accumulate a score of 3 or more, it's considered a spoof
        return score < 3

    def start_camera(self):
        if not self.video_capture or not self.video_capture.isOpened():
            self.video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.video_capture.isOpened():
                self.video_capture = cv2.VideoCapture(0)
            time.sleep(1.0) # Warm up camera

    def stop_camera(self):
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

    def load_known_faces(self, students_data):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        for student in students_data:
            if student.get('face_encoding'):
                # Assuming face_encoding is stored as a list of floats in the DB
                encoding = np.array(student['face_encoding'])
                self.known_face_encodings.append(encoding)
                self.known_face_names.append(student.get('name', 'Unknown'))
                self.known_face_ids.append(student.get('id'))

    def process_registration_frame(self, frame):
        """Processes a single frame for registration sent from frontend."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if len(face_locations) != 1:
            return False, "Needs exactly one face in view"
            
        # YOLO Phone Detection
        phone_detected = False
        if getattr(self, 'yolo_model', None):
            try:
                results = self.yolo_model(frame, verbose=False)
                for r in results:
                    for box in r.boxes:
                        if int(box.cls[0]) == 67 and float(box.conf[0]) > 0.4: # 67 is cell phone in COCO
                            phone_detected = True
                            break
            except:
                pass
            
        # Passive Liveness Check
        if not phone_detected and self.is_real_human_ml(frame, face_locations[0]):
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if len(face_encodings) > 0:
                return True, face_encodings[0].tolist()
        else:
            return False, "Liveness failed: Fake Face Detected! Please show a real human face."
            
        return False, "Failed to capture a valid face."

    def process_frame_for_attendance(self, frame):
        """Processes a frame, detects faces, checks cooldowns, and performs ML liveness."""
        # Run YOLO on full frame to detect phones
        phone_detected = False
        if getattr(self, 'yolo_model', None):
            try:
                results = self.yolo_model(frame, verbose=False)
                for r in results:
                    for box in r.boxes:
                        if int(box.cls[0]) == 67 and float(box.conf[0]) > 0.4: # 67 is cell phone
                            phone_detected = True
                            break
            except:
                pass

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize frame for faster processing
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        detected_students = []
        current_time = time.time()
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
            name = "Unknown"
            student_id = None
            
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    student_id = self.known_face_ids[best_match_index]
            
            # Scale back up face locations
            top, right, bottom, left = face_location
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2
            
            # Passive ML Anti-Spoofing on Full-Res Frame
            is_live = self.is_real_human_ml(frame, (top, right, bottom, left))
            if phone_detected:
                is_live = False

            status = "unknown"
            if not is_live:
                status = "spoof"
            elif student_id:
                last_seen = self.cooldown_dict.get(student_id, 0)
                if current_time - last_seen > self.COOLDOWN_SECONDS:
                    status = "recorded"
                    self.cooldown_dict[student_id] = current_time
                else:
                    status = "cooldown"
            
            detected_students.append({
                "id": student_id,
                "name": name,
                "status": status,
                "box": [top, right, bottom, left],
                "time_since_last": current_time - self.cooldown_dict.get(student_id, 0) if student_id else 0
            })
            
        return detected_students
