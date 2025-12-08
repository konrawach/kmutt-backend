FROM python:3.10-slim

# 1. ติดตั้ง LibreOffice และ wget (เพื่อโหลดฟอนต์)
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-thai-tlwg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. 🛠️ ดาวน์โหลดฟอนต์ TH Sarabun New (4 สไตล์) มาลงเอง
# สร้างโฟลเดอร์เก็บฟอนต์
RUN mkdir -p /usr/share/fonts/truetype/thaifonts

# สั่งดาวน์โหลดทีละไฟล์ (เพื่อให้ได้ชื่อ TH Sarabun New เป๊ะๆ)
RUN wget -q -O /usr/share/fonts/truetype/thaifonts/THSarabunNew.ttf https://github.com/kaitas/thaifonts/raw/master/THSarabunNew.ttf && \
    wget -q -O /usr/share/fonts/truetype/thaifonts/THSarabunNew-Bold.ttf https://github.com/kaitas/thaifonts/raw/master/THSarabunNew%20Bold.ttf && \
    wget -q -O /usr/share/fonts/truetype/thaifonts/THSarabunNew-Italic.ttf https://github.com/kaitas/thaifonts/raw/master/THSarabunNew%20Italic.ttf && \
    wget -q -O /usr/share/fonts/truetype/thaifonts/THSarabunNew-BoldItalic.ttf https://github.com/kaitas/thaifonts/raw/master/THSarabunNew%20BoldItalic.ttf

# อัปเดต Cache ฟอนต์
RUN fc-cache -f -v

# 3. ตั้งค่า Workspace และลง Library ตามปกติ
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
