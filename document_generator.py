import os
import json
from docxtpl import DocxTemplate
from io import BytesIO  # <--- พระเอกของเรา (ตัวจัดการไฟล์ในแรม)

# ... (ส่วน TEMPLATE_MAP เหมือนเดิม) ...
TEMPLATE_DIR = "templates"
TEMPLATE_MAP = {
    "RO-01": os.path.join(TEMPLATE_DIR, "RO-01_General.docx"),
    "RO-03": os.path.join(TEMPLATE_DIR, "RO-03_Parent.docx"),
    "RO-13": os.path.join(TEMPLATE_DIR, "RO-13_Resignation.docx"),
    "RO-16": os.path.join(TEMPLATE_DIR, "RO-16_Sick_Leave.docx")
}

def generate_document_stream(llm_json_string):
    """
    สร้างไฟล์ลงใน RAM (BytesIO) โดยไม่บันทึกลง Disk
    """
    # 1. แปลง JSON
    try:
        data = json.loads(llm_json_string)
    except json.JSONDecodeError:
        print("❌ Error: JSON ผิดรูปแบบ")
        return None

    # 2. เช็ก Template
    form_type = data.get("form_type", "").upper()
    if form_type not in TEMPLATE_MAP:
        print(f"❌ Error: ไม่พบ Template '{form_type}'")
        return None

    template_path = TEMPLATE_MAP[form_type]
    if not os.path.exists(template_path):
        print(f"❌ Error: ไฟล์ Template หาย ({template_path})")
        return None

    # 3. สร้างไฟล์ใน Memory 🧠
    try:
        doc = DocxTemplate(template_path)
        doc.render(data)
        
        # สร้าง "ไฟล์จำลอง" ใน RAM
        file_stream = BytesIO()
        
        # สั่ง Save ลงใน RAM แทนที่จะลง Disk
        doc.save(file_stream)
        
        # รีเซ็ตเข็มอ่านไฟล์ไปที่จุดเริ่มต้น (สำคัญมาก! ถ้าไม่ทำจะได้ไฟล์เปล่า)
        file_stream.seek(0)
        
        print(f"✅ สร้างไฟล์ใน Memory สำเร็จ: {form_type}")
        return file_stream  # ส่งคืนก้อนข้อมูล
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
