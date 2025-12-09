import os
import re
import json
import uvicorn
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles # ไว้สำหรับทำ Link Download
from pydantic import BaseModel

from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from groq import AsyncGroq
from dotenv import load_dotenv
from urllib.parse import quote

# Import ฟังก์ชันสร้างไฟล์ที่เราแยกไว้
from document_generator import generate_document_stream, generate_document_auto

load_dotenv()

# ================= CONFIGURATION =================
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
COLLECTION_NAME = "demo_collection_railway_v2"

# 📂 1. ฐานข้อมูลฟอร์ม (Master Data)
FORM_MASTER_DATA = [
    {
        "id": "RO.01", 
        "name": "คำร้องทั่วไป (General Request)", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-01.pdf",
        "keywords": ["คำร้องทั่วไป", "ro01", "ro.01", "general", "อื่นๆ", "เรื่องทั่วไป", "สทน.01"]
    },
    {
        "id": "RO.03", 
        "name": "หนังสือรับรองของผู้ปกครอง", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-03.pdf",
        "keywords": ["ผู้ปกครอง", "ro03", "ro.03", "หนังสือรับรอง", "ยินยอม", "parent", "สทน.03"]
    },
    {
        "id": "RO.04", 
        "name": "ใบมอบฉันทะ", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-04.pdf",
        "keywords": ["มอบฉันทะ", "ro04", "ro.04", "แทน", "คนอื่นรับแทน", "authorization", "สทน.04"]
    },
    {
        "id": "RO.08", 
        "name": "คำร้องขอคืนเงินค่าลงทะเบียน", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-08.pdf",
        "keywords": ["คืนเงิน", "ro08", "ro.08", "refund", "ค่าลงทะเบียน", "จ่ายเกิน", "ขอคืนเงิน", "สทน.08"]
    },
    {
        "id": "กค.18", 
        "name": "ใบแจ้งความจำนงโอนเงิน", 
        "url": "https://regis.kmutt.ac.th/service/form/18.pdf",
        "keywords": ["กค18", "กค.18", "โอนเงินเข้าบัญชี", "รับเงินโอน"]
    },
    {
        "id": "RO.11", 
        "name": "คำร้องขอเลื่อนรับพระราชทานปริญญาบัตร", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-11.pdf",
        "keywords": ["รับปริญญา", "ro11", "ro.11", "เลื่อนรับ", "ไม่รับปริญญา", "สทน.11"]
    },
    {
        "id": "RO.12", 
        "name": "คำร้องขอลาพักการศึกษา", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-12Updated.pdf",
        "keywords": ["ลาพัก", "ro12", "ro.12", "ดรอปเรียน", "drop", "พักการเรียน", "รักษาสถานภาพ", "สทน.12"]
    },
    {
        "id": "RO.13", 
        "name": "คำร้องขอลาออก", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-13Updated.pdf",
        "keywords": ["ลาออก", "ro13", "ro.13", "resignation", "ออก", "quit", "สทน.13"]
    },
    {
        "id": "RO.14", 
        "name": "คำร้องขอเปลี่ยนแปลงข้อมูลประวัติ", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-14.pdf",
        "keywords": ["เปลี่ยนชื่อ", "ro14", "ro.14", "เปลี่ยนนามสกุล", "แก้ประวัติ", "ที่อยู่ผิด", "คำนำหน้า", "สทน.14"]
    },
    {
        "id": "RO.15", 
        "name": "คำร้องขอทำบัตรนักศึกษาใหม่", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-15_160718.pdf",
        "keywords": ["บัตรหาย", "ro15", "ro.15", "บัตรนักศึกษา", "ทำบัตรใหม่", "บัตรชำรุด", "สทน.15"]
    },
    {
        "id": "RO.16", 
        "name": "คำร้องขอลาป่วย/ลากิจ", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-16.pdf",
        "keywords": ["ลาป่วย", "ro16", "ro.16", "ลากิจ", "ป่วย", "ใบรับรองแพทย์", "หยุดเรียน", "sick", "สทน.16"]
    },
    {
        "id": "RO.18", 
        "name": "คำร้องลงทะเบียนต่ำกว่า/เกินกว่าหน่วยกิต", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-18Updated.pdf",
        "keywords": ["หน่วยกิตเกิน", "ro18", "ro.18", "หน่วยกิตต่ำ", "ลงทะเบียน", "ลงน้อย", "credits", "สทน.18"]
    },
    {
        "id": "RO.19", 
        "name": "คำร้องลงทะเบียนวิชาสอบซ้อน", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-19.pdf",
        "keywords": ["สอบซ้อน", "ro19", "ro.19", "เวลาสอบชน", "exam conflict", "สทน.19"]
    },
    {
        "id": "RO.20", 
        "name": "คำร้องลงทะเบียนวิชานอกหลักสูตร", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-20.pdf",
        "keywords": ["นอกหลักสูตร", "ro20", "ro.20", "วิชาเลือกเสรี", "free elective", "สทน.20"]
    },
    {
        "id": "RO.21", 
        "name": "คำร้องลงทะเบียนเรียนแบบบุคคลภายนอก", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-21.pdf",
        "keywords": ["บุคคลภายนอก", "ro21", "ro.21", "visitor", "คนนอก", "สทน.21"]
    },
    {
        "id": "RO.22", 
        "name": "คำร้องขอสมัครสอบโดยไม่ต้องเข้าเรียน / ผ่อนผัน", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-22.pdf",
        "keywords": ["ขาดเรียน", "ro22", "ro.22", "ผ่อนผัน", "ไม่ได้เข้าเรียน", "สมัครสอบ", "สทน.22"]
    },
    {
        "id": "RO.23", 
        "name": "คำร้องขอเปลี่ยน/เทียบรายวิชา", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-23.pdf",
        "keywords": ["เทียบวิชา", "ro23", "ro.23", "เปลี่ยนวิชา", "transfer", "เทียบโอน", "สทน.23"]
    },
    {
        "id": "RO.25", 
        "name": "ใบลงทะเบียนเรียน", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-25.pdf",
        "keywords": ["ใบลงทะเบียน", "ro25", "ro.25", "register", "regis", "สทน.25"]  
    },
    {
        "id": "RO.26", 
        "name": "ใบเพิ่ม-ลด-ถอน-เปลี่ยนกลุ่ม", 
        "url": "https://regis.kmutt.ac.th/service/form/RO-26Updated.pdf",
        "keywords": ["เพิ่มวิชา", "ro26", "ro.26", "ถอนวิชา", "เปลี่ยนเซค", "เปลี่ยน sec", "add/drop", "ลดวิชา", "ถอน w", "ติด w", "สทน.26"]
    },
]

# เตรียม Text สำหรับ Prompt
FORM_LIST_TEXT = ""
for item in FORM_MASTER_DATA:
    FORM_LIST_TEXT += f"- {item['name']} (รหัส: {item['id']})\n"

# ================= PYDANTIC MODELS =================
class UserRequest(BaseModel):
    message: str

class GenerateRequest(BaseModel):
    form_type: str
    student_id: str
    form_data: Dict[str, Any]

class SourceItem(BaseModel):
    doc: str
    page: int
    url: str

class ChatResponse(BaseModel):
    reply: str
    sources: List[SourceItem]

# ================= AI FUNCTIONS (2 บุคลิก) =================

# 1. บุคลิก "ที่ปรึกษา" (Advisor) - ตอบคำถามทั่วไป
async def get_advisor_response(context: str, question: str, client: AsyncGroq) -> str:
    system_prompt =f'''
        คุณคือ "น้องผู้ช่วย มจธ." (KMUTT Assistant) ผู้เชี่ยวชาญด้านงานทะเบียนและเอกสารคำร้อง
        หน้าที่ของคุณคือ: ให้คำแนะนำที่ถูกต้อง กระชับ และเป็นมิตรกับนักศึกษา (เหมือนรุ่นพี่แนะนำรุ่นน้อง)

        📚 **คลังข้อมูลรหัสเอกสารที่คุณต้องใช้ (Knowledge Base):**
        {FORM_LIST_TEXT}

        ⚡ **กฎการตอบคำถาม (Strict Rules):**
        1. **ห้ามมั่วรหัส:** ต้องตอบรหัสเอกสาร (RO.xx) ให้ตรงกับบริบทเท่านั้น ห้ามเดาเอง
        2. **จับคู่คำศัพท์ (Keyword Mapping):** นักศึกษาอาจใช้คำพูดทั่วไป ให้แปลงเป็นรหัสเอกสารดังนี้:
           - "ดรอป", "ถอนวิชา", "ติด W" -> คือเรื่องการถอนรายวิชา (ใช้ RO.26 หรือระบบ New ACIS)
           - "พักการเรียน", "ดรอปเรียน (ทั้งเทอม)" -> คือการลาพักการศึกษา (ใช้ RO.12)
           - "ป่วย", "ไม่สบาย", "ลากิจ", "หยุดเรียน" -> ใช้ RO.16
           - "ลงเกิน", "หน่วยกิตไม่พอ", "ลงหน่วยกิตต่ำ" -> ใช้ RO.18
           - "สอบชน", "เวลาสอบทับกัน" -> ใช้ RO.19
           - "คืนเงิน", "จ่ายเงินเกิน" -> ใช้ RO.08 คู่กับ กค.18
        3. **ถ้าไม่แน่ใจ:** ให้ตอบว่า "ขออภัยครับ ข้อมูลไม่ชัดเจน แนะนำให้ติดต่อสำนักงานทะเบียนโดยตรง" (อย่าแต่งเรื่องเอง)

        📝 **รูปแบบการตอบ (Response Format):**
        - เริ่มต้นด้วยคำตอบสั้นๆ ว่าต้องทำอะไร
        - บอกขั้นตอนเป็นข้อๆ 1, 2, 3
        - **สำคัญ:** ต้องปิดท้ายด้วยชื่อฟอร์มและลิงก์ดาวน์โหลดเสมอ (ถ้ามีในบริบท)

        ตัวอย่างการตอบที่ดี:
        "สำหรับการขอลาพักการศึกษา (Drop ทั้งเทอม) ต้องทำดังนี้ครับ:
        1. ยื่นเรื่องผ่านระบบ New ACIS
        2. ใช้แบบฟอร์ม **สทน. 12 (RO.12)** ประกอบการยื่น
        ⬇️ ดาวน์โหลดที่นี่: https://regis.kmutt.ac.th/service/form/RO-12Updated.pdf"
    '''
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"

# 2. บุคลิก "นักแกะข้อมูล" (Extractor) - สร้าง JSON เท่านั้น
async def get_extractor_response(question: str, client: AsyncGroq) -> str:
    # โพย Schema (ใส่ให้ครบทุกฟอร์มที่รองรับ)
    schemas = """
    [RO-01] {"form_type": "RO-01","request_subject": "","recipient": "","student_name": "","student_id": "","faculty": "","department": "","class_level": "","semester_gpa": "","cumulative_gpa": "","advisor_name": "","student_tel": "","student_email": "","request_details":"แต่งภาษาทางการ"}
    [RO-03] {"form_type": "RO-03","request_subject": "","recipient": "","student_name": "","student_id": "","faculty": "","department": "","class_level": "","address_no": "","address_moo": "","address_soi": "","address_road": "","address_subdistrict": "","address_district": "","address_province": "","address_postal_code": "","phone_home": "","phone_mobile": "","Parental_certification":"แต่งภาษาทางการ","date_day": "","date_month": "","date_year": ""}
    [RO-13] {"form_type": "RO-13","recipient": "","enclosure_2": "","student_name": "","faculty": "","department": "","class_level": "","advisor_name": "","student_tel": "","student_email": "","reason_study_at_location": "","reason_other_details": "แต่งภาษาทางการ","date_day": "","date_month": "","date_year": ""}
    [RO-16] {"form_type": "RO-16","recipient": "","enclosure_1": "","enclosure_2": "","student_name": "","student_id": "","faculty": "","department": "","class_level": "","advisor_name": "","student_tel": "","student_email": "","leave_days": "","date_from": "","date_to": "","leave_reason":"แต่งภาษาทางการ","date_day": "","date_month": "","date_year": ""}
    """
    system_prompt = f"""
    คุณคือ Data Extractor
    หน้าที่: แปลงคำพูดผู้ใช้เป็น JSON เพื่อกรอกฟอร์ม
    กฎ: 
    1. ห้ามตอบเป็นประโยคสนทนา ให้ตอบ JSON Block เดียวเท่านั้น
    2. ถ้าข้อมูลไม่ครบ ให้ใส่ค่าว่าง ""
    3. แต่งประโยคในช่อง reason/details ให้เป็นภาษาทางการ
    4. ในช่อง date_month ให้ใช้ตัวเลขเช่น 03 แทนเดือนมีนาคม
    
    Schemas:
    {schemas}
    """
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.1, # ค่าต่ำเพื่อให้โครงสร้างแม่นยำ
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        return "{}"

# ================= APP SETUP =================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# เปิดให้เข้าถึงโฟลเดอร์ output ได้ผ่าน Browser (สำหรับโหลดไฟล์)
os.makedirs("output", exist_ok=True)
app.mount("/download", StaticFiles(directory="output"), name="download")

# โหลด Model แบบ Global (เพื่อให้เร็ว ไม่ต้องโหลดใหม่ทุกรอบ)
print("⏳ Initializing Models...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
    sparse_embedding=sparse_embeddings,
    retrieval_mode=RetrievalMode.HYBRID,
    vector_name="dense_vector",
    sparse_vector_name="sparse_vector",
)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)
print("✅ Models Ready!")

# ================= ENDPOINTS =================

@app.get("/")
def read_root():
    return {"status": "Server is running 🚀"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: UserRequest):
    print(f"📩 ข้อความเข้า: {req.message}")
    
    # ---------------------------------------------------------
    # 🚦 STEP 1: ROUTER - เช็คเจตนาผู้ใช้
    # ---------------------------------------------------------
    trigger_words = ["สร้างไฟล์", "เจนไฟล์", "กรอกให้หน่อย", "ร่างคำร้อง", "ทำเอกสาร", "ออกใบ"]
    user_wants_file = any(word in req.message.lower() for word in trigger_words)

    if user_wants_file:
        # === 🅰️ โหมดสร้างไฟล์ ===
        print("⚙️ Detect: สร้างไฟล์")
        
        # 1. ให้ AI แกะ JSON
        json_data_str = await get_extractor_response(req.message, groq_client)
        
        # 2. สร้างไฟล์ .docx (บันทึกลง Disk)
        # ใช้ฟังก์ชัน generate_document_auto จาก document_generator.py
        file_path = generate_document_auto(json_data_str)
        
        if file_path:
            filename = os.path.basename(file_path)
            # สร้างลิงก์สำหรับดาวน์โหลด (สมมติรันบน localhost)
            # ถ้าขึ้น Server จริง ต้องเปลี่ยน localhost เป็น Domain ของคุณ
            base_url = os.getenv("APP_URL", "http://localhost:8000") 
            download_url = f"{base_url}/download/{filename}"
            
            return ChatResponse(
                reply=f"✅ ผมร่างเอกสารให้เรียบร้อยแล้วครับ!\n\n📂 **ดาวน์โหลดไฟล์ Word ได้ที่นี่:**\n{download_url}\n\n(คุณสามารถนำไปแก้ไขจัดหน้าต่อได้เลยครับ)",
                sources=[]
            )
        else:
            return ChatResponse(reply="ขออภัยครับ ผมไม่แน่ใจว่าต้องใช้ฟอร์มไหน หรือข้อมูลไม่เพียงพอ", sources=[])

    else:
        # === 🅱️ โหมดตอบคำถาม (RAG) ===
        print("💬 Detect: ตอบคำถาม")
        
        # 1. ค้นหาใน Vector DB
        search_results = vector_store.similarity_search(req.message, k=3)
        
        # 2. รวม Context + หาลิงก์ PDF ต้นฉบับ
        context_text = ""
        sources = []
        
        # (Logic เดิมของคุณที่ใช้ FORM_MASTER_DATA เช็คคีย์เวิร์ด)
        for item in FORM_MASTER_DATA:
            for kw in item["keywords"]:
                if kw in req.message.lower():
                    context_text += f"\n[ระบบแนะนำ]: ผู้ใช้ถามถึง '{item['name']}' ({item['id']})\n"
                    # เพิ่ม Source อัตโนมัติ
                    if not any(s.url == item["url"] for s in sources):
                        sources.append(SourceItem(doc=item["name"], page=1, url=item["url"]))
                    break

        for doc in search_results:
            context_text += f"{doc.page_content}\n\n"
            # ... (Logic ดึง Source จาก Metadata ของคุณ) ...

        # 3. ให้ AI ตอบ
        answer = await get_advisor_response(context_text, req.message, groq_client)
        
        return ChatResponse(reply=answer, sources=sources)

# --- Endpoint สำหรับ Generate ไฟล์แบบ Stream (ถ้าจะใช้แยก) ---
@app.post("/generate-document")
async def generate_document(req: GenerateRequest):
    print(f"🖨️ Generate Request: {req.form_type}")
    file_stream = generate_document_stream(json.dumps(req.form_data))
    
    if not file_stream:
        raise HTTPException(status_code=500, detail="สร้างไฟล์ไม่สำเร็จ")

    filename = f"Filled_{req.form_type}_{req.student_id}.docx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        file_stream, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
