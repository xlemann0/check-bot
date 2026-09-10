import asyncio
from datetime import datetime
import io
import random
import string
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import qrcode

TOKEN = "8946349098:AAHduOCoODfeBI3adUa8gJ4MRqVfO3cujxQ"
SUPER_ADMIN_ID = 5874144878

# Bot username'ingiz
BOT_USERNAME = "TTJ_DavomatBot"

CURRENT_QR_CODE = ""
CURRENT_QR_DATE = ""

def generate_daily_qr_text():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

bot = Bot(token=TOKEN)
dp = Dispatcher()

admins = {SUPER_ADMIN_ID}
attendance_today = {}
registered_students = {}

class AdminStates(StatesGroup):
    waiting_for_student_id = State()
    waiting_for_student_name = State()
    waiting_for_student_course = State()
    waiting_for_student_room = State()
    waiting_for_student_phone = State()
    waiting_for_remove_student = State()
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()
    waiting_for_broadcast = State()

def generate_qr_buffer(text: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def get_admin_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="1️⃣ Kunlik QR-kodni olish")],
            [types.KeyboardButton(text="7️⃣ Statistika")],
            [types.KeyboardButton(text="8️⃣ Skaner qilganlar"), types.KeyboardButton(text="9️⃣ Skaner qilmaganlar")],
            [types.KeyboardButton(text="2️⃣ Talaba qo'shish"), types.KeyboardButton(text="3️⃣ Talabani o'chirish")],
            [types.KeyboardButton(text="4️⃣ Admin qo'shish"), types.KeyboardButton(text="5️⃣ Adminni o'chirish")],
            [types.KeyboardButton(text="6️⃣ Xabar yollash")],
        ],
        resize_keyboard=True,
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = command.args

    if args and args.startswith("qr_"):
        if user_id in admins:
            await message.answer("Siz adminsiz, davomat qilish shart emas 😊")
            return
        if user_id not in registered_students:
            await message.answer("❌ Siz yotoqxona ro'yxatidan o'tmagansiz! Admin bilan bog'laning.")
            return

        expected_arg = f"qr_{CURRENT_QR_CODE}"
        if args != expected_arg:
            await message.answer(
                "❌ **Bu QR-kod o'z kuchini yo'qotgan (eskirgan)!**\n"
                "Iltimos, adminning bugungi yangi QR-kodini skaner qiling.",
                parse_mode="Markdown"
            )
            return

        if user_id in attendance_today:
            await message.answer("⚠️ Siz bugun allaqachon davomatdan o'tgansiz!")
            return

        student_data = registered_students[user_id]
        current_time = datetime.now()

        attendance_today[user_id] = {
            "name": student_data["name"],
            "course": student_data.get("course", "Nomaʼlum"),
            "room": student_data.get("room", "Nomaʼlum"),
            "time": current_time.strftime("%H:%M:%S"),
        }

        await message.answer(
            f"✅ **Davomatingiz muvaffaqiyatli qabul qilindi!**\n"
            f"👤 {student_data['name']} | 🚪 Xona: {student_data.get('room', '-')}",
            parse_mode="Markdown"
        )
        return

    if user_id in admins:
        await message.answer(
            "Salomat, Admin! Boshqaruv paneliga xush kelibsiz.",
            reply_markup=get_admin_keyboard(),
        )
        return

    if user_id not in registered_students:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💬 Adminga murojaat qilish", url="https://t.me/xlemann")]]
        )
        await message.answer(
            "❌ Siz adminlar tomonidan hali ro'yxatdan o'tkazilmagansiz!\n"
            "Botdan foydalanish uchun administratorga murojaat qiling.",
            reply_markup=keyboard,
        )
        return

    # Talabalar uchun Web App (Kamerani ochuvchi) tugma
    web_app_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📷 Kamerani ochish va Skaner qilish",
                web_app=WebAppInfo(url="https://t.me/TTJ_DavomatBot/dilshod")
            )
        ]]
    )
    await message.answer(
        "Xush kelibsiz! Davomat qilish uchun quyidagi tugmani bosing va kamerani oching:",
        reply_markup=web_app_keyboard,
    )

@dp.message(F.text == "1️⃣ Kunlik QR-kodni olish")
async def admin_get_qr(message: types.Message):
    if message.from_user.id not in admins:
        return

    global CURRENT_QR_CODE, CURRENT_QR_DATE
    today_date = datetime.now().strftime("%Y-%m-%d")

    CURRENT_QR_CODE = generate_daily_qr_text()
    CURRENT_QR_DATE = today_date

    deep_link = f"https://t.me/{BOT_USERNAME}?start=qr_{CURRENT_QR_CODE}"
    qr_io = generate_qr_buffer(deep_link)
    photo = types.BufferedInputFile(qr_io.getvalue(), filename="qrcode.png")

    await message.answer_photo(
        photo=photo,
        caption=(
            f"📸 **Bugungi ({today_date}) maxsus QR-kod!**\n\n"
            f"⚠️ *Eslatma:* Bu kod faqat bugun amal qiladi va xonadagi talabalarga ko'rsatish uchun mo'ljallangan."
        ),
        parse_mode="Markdown"
    )

@dp.message(F.text == "7️⃣ Statistika")
async def admin_statistics(message: types.Message):
    if message.from_user.id not in admins:
        return

    total_students = len(registered_students)
    scanned_count = len(attendance_today)
    not_scanned_count = total_students - scanned_count

    await message.answer(
        f"📊 **Yotoqxona Davomat Statistikasi**\n\n"
        f"👥 Jami ro'yxatdagi talabalar: **{total_students} ta**\n"
        f"✅ Skaner qilganlar (Kelganlar): **{scanned_count} ta**\n"
        f"❌ Skaner qilmaganlar: **{not_scanned_count} ta**",
        parse_mode="Markdown"
    )

@dp.message(F.text == "8️⃣ Skaner qilganlar")
async def admin_scanned_list(message: types.Message):
    if message.from_user.id not in admins:
        return
    if not attendance_today:
        await message.answer("⚠️ Hozircha hech kim skaner qilmadi.")
        return

    text_list = []
    for s_id, data in attendance_today.items():
        text_list.append(f"👤 {data['name']} | 🎓 {data['course']} | 🚪 Xona: {data['room']} | ⏰ {data['time']}")

    response = f"✅ **Skaner qilganlar ({len(attendance_today)} ta):**\n\n" + "\n".join(text_list)
    if len(response) > 4096:
        response = response[:4096]
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "9️⃣ Skaner qilmaganlar")
async def admin_not_scanned_list(message: types.Message):
    if message.from_user.id not in admins:
        return

    not_scanned = []
    for s_id, data in registered_students.items():
        if s_id not in attendance_today:
            not_scanned.append(f"👤 {data['name']} | 🎓 {data['course']} | 🚪 Xona: {data['room']} | 📞 {data['phone']}")

    if not not_scanned:
        await message.answer("✅ Hamma ro'yxatdagi talabalar davomatdan o'tdi!")
    else:
        response = f"❌ **Skaner qilmaganlar ({len(not_scanned)} ta):**\n\n" + "\n".join(not_scanned)
        if len(response) > 4096:
            response = response[:4096]
        await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "2️⃣ Talaba qo'shish")
async def add_student_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    await message.answer("🆔 Talabaning **Telegram ID** raqamini yuboring:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_student_id)

@dp.message(AdminStates.waiting_for_student_id, F.text)
async def get_student_id(message: types.Message, state: FSMContext):
    try:
        s_id = int(message.text.strip())
        await state.update_data(student_id=s_id)
        await message.answer("✍️ Talabaning **Ism va Familiyasini** kiriting:", parse_mode="Markdown")
        await state.set_state(AdminStates.waiting_for_student_name)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqamli Telegram ID kiriting:")

@dp.message(AdminStates.waiting_for_student_name, F.text)
async def get_student_name(message: types.Message, state: FSMContext):
    await state.update_data(student_name=message.text.strip())
    await message.answer("🎓 Talabaning **kursini** kiriting (masalan: `1-kurs`):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_student_course)

@dp.message(AdminStates.waiting_for_student_course, F.text)
async def get_student_course(message: types.Message, state: FSMContext):
    await state.update_data(student_course=message.text.strip())
    await message.answer("🚪 Talabaning **xona raqamini** kiriting (masalan: `312-xona`):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_student_room)

@dp.message(AdminStates.waiting_for_student_room, F.text)
async def get_student_room(message: types.Message, state: FSMContext):
    await state.update_data(student_room=message.text.strip())
    await message.answer("📞 Talabaning **telefon raqamini** kiriting:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_student_phone)

@dp.message(AdminStates.waiting_for_student_phone, F.text)
async def get_student_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    s_id = data["student_id"]

    registered_students[s_id] = {
        "name": data["student_name"],
        "course": data["student_course"],
        "room": data["student_room"],
        "phone": message.text.strip(),
    }

    await message.answer("✅ Talaba muvaffaqiyatli ro'yxatga qo'shildi!", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "3️⃣ Talabani o'chirish")
async def remove_student_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    await message.answer("🗑 O'chirmoqchi bo'lgan talabaning **Telegram ID** raqamini yuboring:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_remove_student)

@dp.message(AdminStates.waiting_for_remove_student, F.text)
async def save_remove_student(message: types.Message, state: FSMContext):
    try:
        s_id = int(message.text.strip())
        if s_id in registered_students:
            registered_students.pop(s_id)
            if s_id in attendance_today:
                attendance_today.pop(s_id)
            await message.answer("✅ Talaba ro'yxatdan o'chirildi.", reply_markup=get_admin_keyboard())
        else:
            await message.answer("❌ Bu ID bo'yicha talaba topilmadi. Qaytadan ID yuboring:")
            return
        await state.clear()
    except ValueError:
        await message.answer("❌ Faqat raqam yuboring:")

@dp.message(F.text == "4️⃣ Admin qo'shish")
async def add_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("⚠️ Bu amalni faqat Super Admin bajarishi mumkin!")
        return
    await message.answer("🆔 Yangi adminning **Telegram ID** raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_new_admin_id)

@dp.message(AdminStates.waiting_for_new_admin_id, F.text)
async def save_new_admin(message: types.Message, state: FSMContext):
    try:
        new_id = int(message.text.strip())
        admins.add(new_id)
        await message.answer(f"✅ `{new_id}` muvaffaqiyatli admin qilindi.", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
        await state.clear()
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting:")

@dp.message(F.text == "5️⃣ Adminni o'chirish")
async def remove_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("⚠️ Bu amalni faqat Super Admin bajarishi mumkin!")
        return

    admin_list_text = "\n".join([f"• `{a}`" for a in admins])
    await message.answer(f"🗑 **Hozirgi adminlar:**\n{admin_list_text}\n\nO'chirish uchun ID yuboring:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_remove_admin_id)

@dp.message(AdminStates.waiting_for_remove_admin_id, F.text)
async def save_remove_admin(message: types.Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        if target_id == SUPER_ADMIN_ID:
            await message.answer("❌ Super Adminni o'chirib bo'lmaydi!")
            return
        if target_id in admins:
            admins.remove(target_id)
            await message.answer("✅ Admin huquqi olib tashlandi.", reply_markup=get_admin_keyboard())
        else:
            await message.answer("❌ Bunday ID li admin topilmadi.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Faqat raqam yuboring:")

@dp.message(F.text == "6️⃣ Xabar yollash")
async def broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    await message.answer("📢 Talabalarga yubormoqchi bo'lgan e'lon matnini yozing:")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast, F.text)
async def send_broadcast(message: types.Message, state: FSMContext):
    count = 0
    for student_id in registered_students.keys():
        try:
            await bot.send_message(student_id, f"📢 **E'lon:**\n\n{message.text}")
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ E'lon {count} ta talabaga muvaffaqiyatli yuborildi!", reply_markup=get_admin_keyboard())
    await state.clear()

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = 10000
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
