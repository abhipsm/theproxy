import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
            try:
                self.supabase: Client = create_client(url, key)
                self.is_connected = True
            except Exception as e:
                print(f"Failed to connect to Supabase: {e}")
                self.is_connected = False
        else:
            print("Supabase credentials not found in environment.")
            self.is_connected = False

    def verify_admin(self, admin_id, password):
        if not self.is_connected: return False
        # Simplified query, ideally hash passwords!
        try:
            response = self.supabase.table("admins").select("*").eq("admin_id", admin_id).eq("password", password).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error verifying admin: {e}")
            return None

    def create_admin(self, admin_id, password, department):
        if not self.is_connected: return False
        try:
            data = {"admin_id": admin_id, "password": password, "department": department}
            self.supabase.table("admins").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error creating admin: {e}")
            return False

    def register_student(self, student_data, face_encoding_list):
        if not self.is_connected: return False
        try:
            # We store face encoding as a JSON array or text
            student_data['face_encoding'] = face_encoding_list
            response = self.supabase.table("students").insert(student_data).execute()
            return response.data
        except Exception as e:
            print(f"Error registering student: {e}")
            return None

    def get_all_students(self):
        if not self.is_connected: return []
        try:
            response = self.supabase.table("students").select("id, name, face_encoding, class_name").execute()
            return response.data
        except Exception as e:
            print(f"Error getting students: {e}")
            return []

    def delete_student(self, student_id):
        if not self.is_connected: return False
        try:
            self.supabase.table("attendance").delete().eq("student_id", student_id).execute()
            self.supabase.table("students").delete().eq("id", student_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False

    def record_attendance(self, student_id, date, time):
        if not self.is_connected: return False
        try:
            # Check if already marked for today
            existing = self.supabase.table("attendance").select("id").eq("student_id", student_id).eq("date", date).execute()
            if len(existing.data) > 0:
                return "already_marked"
                
            data = {"student_id": student_id, "date": date, "time": time}
            self.supabase.table("attendance").insert(data).execute()
            return "newly_marked"
        except Exception as e:
            print(f"Error recording attendance: {e}")
            return False

    def get_attendance_by_department(self, department):
        if not self.is_connected: return []
        # Complex join logic would go here depending on schema
        try:
            # Mock implementation - typically you'd join students and attendance
            response = self.supabase.table("attendance").select("*, students(*)").execute()
            return response.data
        except Exception as e:
            print(f"Error fetching attendance: {e}")
            return []

db = DatabaseManager()
