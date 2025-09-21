# detector
VPS

### 1. تحديث النظام
```bash
sudo apt update && sudo apt upgrade -y

2. تثبيت بايثون ومكتبات أساسية

sudo apt install python3 python3-pip python3-venv ffmpeg -y

3. إنشاء بيئة افتراضية وتشغيلها

python3 -m venv venv
source venv/bin/activate

4. تثبيت المكتبات المطلوبة

pip install pyTelegramBotAPI opennsfw2 pillow requests

5. إضافة الكود

ارفع ملف kf.py إلى السيرفر (مثلاً باستخدام scp أو رفعه إلى GitHub ثم استنساخه).

6. تشغيل البوت

python3 kf.py


---

💾 متطلبات السيرفر

أقل شيء 1GB RAM.

مساحة تخزين: ~ 200MB كافية لتشغيل البوت (بدون مشاكل).

اتصال إنترنت مستقر.



---

📊 الأوامر

/start → تشغيل البوت + رسالة ترحيب.

/stats → تقرير يومي للمشرفين فقط.



---

👨‍💻 معرفات وقناة المطور على تلغرام

المطور: SB_SAHAR@

قناة التحديثات: SYR_SB@
