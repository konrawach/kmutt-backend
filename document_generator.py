import os
import json
from docxtpl import DocxTemplate
from io import BytesIO

# ---------------------------------------------------------
# 1. ตั้งค่า Template
# ---------------------------------------------------------
TEMPLATE_DIR = "templates"

TEMPLATE_MAP = {
    "RO-01": os.path.join(TEMPLATE_DIR, "RO-01_General.docx"),
    "RO-03": os.path.join(TEMPLATE_DIR, "RO-03_Parent.docx"),
    "RO-13": os.path.join(TEMPLATE_DIR, "RO-13_Resignation.docx"),
    "RO-16": os.path.join(TEMPLATE_DIR, "RO-16_Sick_Leave.docx")
}

# ---------------------------------------------------------
# ฟังก์ชัน 1: สร้างไฟล์ลง Disk (สำหรับ Chatbot)
# ---------------------------------------------------------
def generate_document_auto(llm_json_string):
    try:
        data = json.loads(llm_json_string)
    except json.JSONDecodeError:
        print("❌ Error: JSON ผิดรูปแบบ")
        return None

    form_type = data.get("form_type", "").upper()
    
    if form_type not in TEMPLATE_MAP:
        print(f"❌ Error: ไม่พบ Template รหัส '{form_type}'")
        return None

    template_path = TEMPLATE_MAP[form_type]
    if not os.path.exists(template_path):
        print(f"❌ Error: หาไฟล์ Template ไม่เจอ ({template_path})")
        return None

    print(f"✅ กำลังสร้างเอกสาร (Disk): {form_type}")

    # สร้างโฟลเดอร์ output
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    student_id = data.get('student_id', 'unknown')
    output_filename = f"Filled_{form_type}_{student_id}.docx"
    output_path = os.path.join(output_dir, output_filename)

    try:
        doc = DocxTemplate(template_path)
        doc.render(data)
        doc.save(output_path)
        print(f"💾 บันทึกไฟล์สำเร็จ: {output_path}")
        return output_path 
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ---------------------------------------------------------
# ฟังก์ชัน 2: สร้างไฟล์ใน RAM (สำหรับ API Stream)
# ---------------------------------------------------------
def generate_document_stream(llm_json_string):
    try:
        data = json.loads(llm_json_string)
    except json.JSONDecodeError:
        return None

    form_type = data.get("form_type", "").upper()
    if form_type not in TEMPLATE_MAP or not os.path.exists(TEMPLATE_MAP[form_type]):
        return None

    print(f"✅ กำลังสร้างเอกสาร (Stream): {form_type}")

    try:
        doc = DocxTemplate(TEMPLATE_MAP[form_type])
        doc.render(data)
        
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
