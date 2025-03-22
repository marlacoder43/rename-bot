from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import asyncio

from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID  

bot = Client("FileRenameBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

# ✅ /start komandasi
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Salom! Menga fayl yuboring va uni nomini yoki rasmini o‘zgartiring!")

# ✅ Fayl yuklash (500MB dan oshsa rad etadi)
@bot.on_message(filters.document | filters.video | filters.audio)
async def file_handler(client, message):
    file = message.document or message.video or message.audio
    file_name = file.file_name if file else "File"
    
    if file.file_size > 524288000:
        await message.reply_text("❌ Fayl hajmi 500MB dan katta! Kichikroq fayl yuboring.")
        return

    progress_msg = await message.reply_text(f"📥 `{file_name}` yuklanmoqda...")

    file_path = await client.download_media(file.file_id)
    ext = os.path.splitext(file_name)[1]  

    new_file_path = os.path.join(os.path.dirname(file_path), file_name)
    os.rename(file_path, new_file_path)

    await progress_msg.edit_text(f"✅ `{file_name}` yuklandi!")

    file_index = str(len(user_data) + 1)
    user_data[file_index] = {"file_path": new_file_path, "thumbnail": None, "extension": ext, "file_name": file_name}

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Nomini o‘zgartirish", callback_data=f"rename|{file_index}")],
        [InlineKeyboardButton("🖼 Rasmini o‘zgartirish", callback_data=f"change_thumb|{file_index}")]
    ])

    await message.reply_text(f"📂 **Fayl:** `{file_name}`", reply_markup=buttons)

# ✅ Fayl yuborish funksiyasi (kanalga va foydalanuvchiga)
async def send_file_and_delete(client, chat_id, file_data):
    file_path = file_data["file_path"]
    file_name = file_data["file_name"]
    thumb_path = file_data.get("thumbnail")

    progress_msg = await client.send_message(chat_id, "📤 Fayl yuborilmoqda... ⏳")

    await asyncio.sleep(1)

    # ✅ Faylni kanalga yuborish
    await client.send_document(
        CHANNEL_ID,  
        document=file_path,
        caption="📂 **Yangi fayl!**",
        file_name=file_name,  
        thumb=thumb_path,
        force_document=True  
    )

    # ✅ Faylni foydalanuvchiga yuborish
    await client.send_document(
        chat_id,  
        document=file_path,
        caption="📂 **Faylingiz tayyor!**",
        file_name=file_name,  
        thumb=thumb_path,
        force_document=True  
    )

    await progress_msg.delete()

    # 🗑 Yuklangan fayllarni o‘chirish
    os.remove(file_path)
    if thumb_path:
        os.remove(thumb_path)

# ✅ Fayl nomini o‘zgartirish
@bot.on_callback_query(filters.regex(r"^rename\|"))
async def rename_file(client, callback_query):
    file_index = callback_query.data.split("|")[1]
    user_data[file_index]["rename"] = True

    await callback_query.message.reply_text("✍ Yangi fayl nomini yozing (fayl kengaytmasiz):")

# ✅ Foydalanuvchi yangi nomni kiritganda
@bot.on_message(filters.text)
async def process_text(client, message):
    for file_index, data in user_data.items():
        if "rename" in data and data["rename"]:
            old_path = data["file_path"]
            file_extension = data["extension"]  

            new_name = message.text + file_extension  
            new_path = os.path.join(os.path.dirname(old_path), new_name)

            os.rename(old_path, new_path)
            data["file_path"] = new_path
            data["file_name"] = new_name
            data.pop("rename", None)

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 Ha", callback_data=f"change_thumb|{file_index}")],
                [InlineKeyboardButton("❌ Yo‘q", callback_data=f"no_thumb|{file_index}")]
            ])
            await message.reply_text(f"✅ **Fayl nomi o‘zgartirildi:** `{new_name}`\n\n📸 **Rasmni ham o‘zgartirasizmi?**", reply_markup=buttons)
            break

# ✅ Rasm yuklashni so‘rash
@bot.on_callback_query(filters.regex(r"^change_thumb\|"))
async def ask_for_thumb(client, callback_query):
    file_index = callback_query.data.split("|")[1]
    user_data[file_index]["waiting_for_thumb"] = True
    await callback_query.message.reply_text("🖼 Iltimos, yangi rasm (thumbnail) yuklang:")

# ✅ Rasm yuklash
@bot.on_message(filters.photo)
async def save_thumbnail(client, message):
    file_path = await client.download_media(message.photo.file_id)

    for file_index, data in user_data.items():
        if "waiting_for_thumb" in data and data["waiting_for_thumb"]:
            data["thumbnail"] = file_path
            data.pop("waiting_for_thumb", None)

            await send_file_and_delete(client, message.chat.id, data)
            break

# ❌ Agar foydalanuvchi rasmni o‘zgartirmasa
@bot.on_callback_query(filters.regex(r"^no_thumb\|"))
async def skip_thumbnail(client, callback_query):
    file_index = callback_query.data.split("|")[1]
    if file_index in user_data:
        await send_file_and_delete(client, callback_query.message.chat.id, user_data[file_index])

bot.run()
