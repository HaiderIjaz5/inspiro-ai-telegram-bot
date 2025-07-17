import os
import requests
from io import BytesIO
from keep_alive import keep_alive

from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 🔐 Load secrets from environment
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
STABILITY_KEY = os.environ["STABILITY_KEY"]
keep_alive()  # Starts the web server for UptimeRobot

# 🧠 Keep track of each user's selected mode
user_modes = {}  # user_id: "chat" or "imagine"

# 🚀 /start with keyboard
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💬 Chat Mode", "🎨 Image Mode"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome to your AI Bot!\nChoose a mode to begin:",
        reply_markup=reply_markup
    )

# 🔄 Mode switch when user clicks a button
async def handle_mode_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text == "💬 Chat Mode":
        user_modes[user_id] = "chat"
        await update.message.reply_text("💬 You're now in *Chat Mode*. Just type your message!", parse_mode="Markdown")

    elif text == "🎨 Image Mode":
        user_modes[user_id] = "imagine"
        await update.message.reply_text("🎨 You're now in *Image Mode*. Send a prompt to generate an image.", parse_mode="Markdown")

    else:
        await handle_user_input(update, context)

# 🧠 Handles all non-command messages
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    mode = user_modes.get(user_id)

    if not mode:
        return await update.message.reply_text("❗ Please select a mode first by using /start.")

    context.args = text.split()
    if mode == "chat":
        await chat(update, context)
    elif mode == "imagine":
        await imagine(update, context)

# 💬 Chat Mode with progress simulation
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        return await update.message.reply_text("🧠 Please type something to chat.")

    await update.message.chat.send_action(ChatAction.TYPING)
    thinking_msg = await update.message.reply_text("🤔 Thinking...")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            await thinking_msg.edit_text(reply)
        else:
            await thinking_msg.edit_text(f"❌ Chat Error: {response.status_code}\n{response.text}")

    except Exception as e:
        await thinking_msg.edit_text(f"⚠️ Error during chat: {str(e)}")

# 🎨 Image Generation Mode (Stable Diffusion 3.5 Large)
async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        return await update.message.reply_text("🖼️ Please type a prompt to generate an image.")

    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    loading_msg = await update.message.reply_text("🎨 Generating your image...")

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "Authorization": f"Bearer {STABILITY_KEY}",
        "Accept": "image/*"  # ✅ Must be exactly this
    }

    # ✅ Send as multipart/form-data using files=
    files = {
        'prompt': (None, prompt),
        'output_format': (None, 'png'),
        'model': (None, 'sd3.5-large'),  # You can also try sd3.5-large-turbo
        'aspect_ratio': (None, '1:1'),
        'style_preset': (None, 'photographic'),
        'seed': (None, '0')
    }

    try:
        response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:
            image = BytesIO(response.content)
            image.name = "generated.png"
            await loading_msg.delete()
            await update.message.reply_photo(photo=image)
        else:
            await loading_msg.edit_text(f"❌ Stability API Error:\n{response.status_code}\n{response.text}")
    except Exception as e:
        await loading_msg.edit_text(f"⚠️ Error during image generation: {str(e)}")

# 🛠 Main setup
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mode_switch))

    print("🤖 Smart AI Bot is running...")
    app.run_polling()
