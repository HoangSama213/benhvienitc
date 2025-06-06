# app.py
from flask import Flask, render_template, request, jsonify
import os
import datetime

app = Flask(__name__)

# Đường dẫn đến file dữ liệu bệnh nhân và file dữ liệu bệnh
DATA_FILE_PATH = 'BV.txt'
DISEASE_DATA_FILE_PATH = 'du_lieu_benh.txt'

# --- Hàm hỗ trợ tương tác với file BV.txt ---
def save_patient_data(patients_list):
    try:
        with open(DATA_FILE_PATH, 'w', encoding='utf8') as f:
            for patient_info in patients_list:
                # Store name, age, sex, disease_name (original), time_str
                # The condition string will be derived on display
                f.write(' - '.join(patient_info) + '\n')
        return True
    except Exception as e:
        print(f"Lỗi khi lưu dữ liệu vào file: {e}")
        return False

def read_patient_data():
    patients = []
    if not os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, 'w', encoding='utf8') as f:
                pass
            print(f"File '{DATA_FILE_PATH}' không tồn tại, đã tạo file mới.")
        except Exception as e:
            print(f"Không thể tạo file '{DATA_FILE_PATH}': {e}")
            return []
        return []

    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf8') as f:
            for line in f:
                data = line.strip()
                if data:
                    arr = data.split('-')
                    if len(arr) == 5: # Expecting name, age, sex, disease_name, time_str
                        patients.append([part.strip() for part in arr])
                    else:
                        print(f"Dòng dữ liệu không hợp lệ (không đủ 5 phần): {data}")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{DATA_FILE_PATH}'.")
        return []
    except Exception as e:
        print(f"Lỗi khi đọc file '{DATA_FILE_PATH}': {e}")
    return patients

def load_disease_data(file_path):
    disease_map = {}
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file dữ liệu bệnh '{file_path}'.")
        return {}
    try:
        with open(file_path, 'r', encoding='utf8') as f:
            next(f)  # Bỏ qua dòng tiêu đề
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    disease_name = parts[0].strip()
                    emergency_level = int(parts[1].strip())
                    disease_map[disease_name.lower()] = emergency_level
                else:
                    print(f"Dòng dữ liệu bệnh không hợp lệ: {line.strip()}")
    except Exception as e:
        print(f"Lỗi khi đọc file dữ liệu bệnh '{file_path}': {e}")
    return disease_map

EMERGENCY_LEVEL_MAP = {
    0: "khẩn cấp",
    1: "nghiêm trọng",
    2: "trung bình",
    3: "nhẹ",
    4: "nhẹ"
}

DISEASE_DATA = load_disease_data(DISEASE_DATA_FILE_PATH)

@app.route('/')
def index():
    return render_template('benhvienitc.html')

@app.route('/api/patients', methods=['GET'])
def get_patients():
    patients_raw = read_patient_data()
    patients_with_level = []
    for p in patients_raw:
        name, age, sex, disease_name_stored, time_str = p
        # Get the emergency level based on the stored disease name
        emergency_level_num = DISEASE_DATA.get(disease_name_stored.lower())
        condition = EMERGENCY_LEVEL_MAP.get(emergency_level_num, "nhẹ")
        patients_with_level.append({
            "name": name,
            "age": age,
            "sex": sex,
            "disease_name": disease_name_stored, # Keep original disease name for display
            "condition": condition, # Descriptive condition
            "emergency_level": emergency_level_num, # Numerical emergency level
            "time_str": time_str
        })
    return jsonify(patients_with_level), 200

@app.route('/api/patients', methods=['POST'])
def add_patient():
    data = request.get_json()
    name = data.get('name')
    age = data.get('age')
    sex = data.get('sex')
    disease_name = data.get('disease_name')
    time_str = data.get('time_str')

    if not all([name, age, sex, disease_name, time_str]):
        return jsonify({"error": "Vui lòng điền đầy đủ tất cả các trường thông tin."}), 400

    try:
        int(age)
    except ValueError:
        return jsonify({"error": "Tuổi phải là một số nguyên."}), 400
    
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
    except ValueError:
        return jsonify({"error": "Thời gian đến không hợp lệ. Vui lòng nhập theo định dạng HH:MM."}), 400

    emergency_level_num = DISEASE_DATA.get(disease_name.lower())
    condition = EMERGENCY_LEVEL_MAP.get(emergency_level_num, "nhẹ")

    patients = read_patient_data()
    # Store the actual disease name, not the derived condition string
    new_patient_raw = [name, str(age), sex, disease_name, time_str]
    patients.append(new_patient_raw)

    # Sort based on the disease name to get the emergency level
    patients.sort(key=lambda p: (DISEASE_DATA.get(p[3].lower(), 99), p[4])) # p[3] is disease_name, p[4] is time_str

    if save_patient_data(patients):
        return jsonify({
            "message": f"Đã thêm bệnh nhân '{name}' thành công!",
            "condition": condition,
            "emergency_level": emergency_level_num, # Return the level for client-side use
            "disease_name": disease_name # Return the disease name
        }), 201
    else:
        return jsonify({"error": "Lỗi khi thêm bệnh nhân vào file."}), 500

@app.route('/api/patients/<int:index>', methods=['DELETE'])
def delete_patient(index):
    patients = read_patient_data()
    if 0 <= index < len(patients):
        deleted_patient = patients.pop(index)
        if save_patient_data(patients):
            return jsonify({"message": f"Đã xóa bệnh nhân '{deleted_patient[0]}' thành công."}), 200
        else:
            return jsonify({"error": "Lỗi khi lưu dữ liệu sau khi xóa."}), 500
    return jsonify({"error": "Không tìm thấy bệnh nhân để xóa."}), 404

@app.route('/api/patients/clear_all', methods=['DELETE'])
def clear_all_patients():
    try:
        if os.path.exists(DATA_FILE_PATH):
            os.remove(DATA_FILE_PATH)
            return jsonify({"message": "Đã xóa tất cả bệnh nhân thành công"}), 200
        return jsonify({"message": "File dữ liệu không tồn tại để xóa."}), 200
    except Exception as e:
        return jsonify({"error": f"Lỗi khi xóa tất cả bệnh nhân: {e}"}), 500

@app.route('/api/diseases', methods=['GET'])
def get_diseases():
    disease_data = load_disease_data(DISEASE_DATA_FILE_PATH)
    # Convert keys to original case for display if needed, or keep lowercase
    return jsonify([{ "name": name, "level": level } for name, level in disease_data.items()]), 200
 
if __name__ == '__main__':
    if not os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, 'w', encoding='utf8') as f:
                pass
        except Exception as e:
            print(f"Không thể tạo file '{DATA_FILE_PATH}': {e}")

    app.run(debug=True)