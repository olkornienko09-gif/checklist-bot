import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "checklist.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"items": [], "users": {"user1": "Пользователь 1", "user2": "Пользователь 2"}, "message_id": None, "chat_id": None}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_checklist(data):
    keyboard = []

    for i, item in enumerate(data["items"]):
        u1 = data["users"].get("user1", "Пользователь 1")
        u2 = data["users"].get("user2", "Пользователь 2")
        c1 = "✅" if item["checks"].get("user1", False) else "⬜"
        c2 = "✅" if item["checks"].get("user2", False) else "⬜"

        keyboard.append([
            InlineKeyboardButton(f"{i+1}. {item['title']}", callback_data="noop"),
        ])
        keyboard.append([
            InlineKeyboardButton(f"{c1} {u1}", callback_data=f"check|{i}|user1"),
            InlineKeyboardButton(f"{c2} {u2}", callback_data=f"check|{i}|user2"),
        ])

    keyboard.append([
        InlineKeyboardButton("➕ Добавить задачу", callback_data="add_item"),
        InlineKeyboardButton("✏️ Изменить задачу", callback_data="edit_item"),
    ])
    keyboard.append([
        InlineKeyboardButton("🗑 Удалить задачу", callback_data="delete_item"),
        InlineKeyboardButton("👤 Изменить имена", callback_data="set_names"),
    ])

    text = "📋 *Чеклист*"
    return text, InlineKeyboardMarkup(keyboard)

async def update_message(context, data):
    text, keyboard = build_checklist(data)
    try:
        await context.bot.edit_message_text(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["chat_id"] = update.effective_chat.id
    text, keyboard = build_checklist(data)
    msg = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    data["message_id"] = msg.message_id
    save_data(data)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    action = query.data
if action == "noop":
        return
    if action.startswith("check|"):
        _, idx, slot = action.split("|")
        idx = int(idx)
        current = data["items"][idx]["checks"].get(slot, False)
        data["items"][idx]["checks"][slot] = not current
        save_data(data)
        await update_message(context, data)

    elif action == "add_item":
        context.user_data["action"] = "add"
        await query.message.reply_text("Напиши текст новой задачи:")

    elif action == "edit_item":
        if not data["items"]:
            await query.message.reply_text("Список пуст!")
            return
        items_list = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(data["items"])])
        context.user_data["action"] = "edit_choose"
        await query.message.reply_text(f"Какую задачу изменить? Напиши номер:\n{items_list}")

    elif action == "delete_item":
        if not data["items"]:
            await query.message.reply_text("Список пуст!")
            return
        items_list = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(data["items"])])
        context.user_data["action"] = "delete_choose"
        await query.message.reply_text(f"Какую задачу удалить? Напиши номер:\n{items_list}")

    elif action == "set_names":
        context.user_data["action"] = "set_name1"
        await query.message.reply_text("Напиши имя первого пользователя (для левой галочки):")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action")
    text = update.message.text.strip()
    data = load_data()

    if action == "add":
        data["items"].append({"title": text, "checks": {}})
        context.user_data["action"] = None
        save_data(data)
        await update.message.reply_text(f"✅ Задача «{text}» добавлена!")
        await update_message(context, data)

    elif action == "edit_choose":
        try:
            idx = int(text) - 1
            if 0 <= idx < len(data["items"]):
                context.user_data["action"] = "edit_text"
                context.user_data["edit_idx"] = idx
                await update.message.reply_text(f"Напиши новый текст для задачи «{data['items'][idx]['title']}»:")
            else:
                await update.message.reply_text("Неверный номер!")
        except ValueError:
            await update.message.reply_text("Напиши число!")

    elif action == "edit_text":
        idx = context.user_data.get("edit_idx")
        data["items"][idx]["title"] = text
        context.user_data["action"] = None
        save_data(data)
        await update.message.reply_text("✅ Задача обновлена!")
        await update_message(context, data)

    elif action == "delete_choose":
        try:
            idx = int(text) - 1
            if 0 <= idx < len(data["items"]):
                removed = data["items"].pop(idx)
                context.user_data["action"] = None
                save_data(data)
                await update.message.reply_text(f"🗑 Задача «{removed['title']}» удалена!")
                await update_message(context, data)
            else:
                await update.message.reply_text("Неверный номер!")
        except ValueError:
            await update.message.reply_text("Напиши число!")

    elif action == "set_name1":
        data["users"]["user1"] = text
        context.user_data["action"] = "set_name2"
        save_data(data)
        await update.message.reply_text("Теперь напиши имя второго пользователя:")

    elif action == "set_name2":
        data["users"]["user2"] = text
        context.user_data["action"] = None
        save_data(data)
        await update.message.reply_text("✅ Имена обновлены!")
        await update_message(context, data)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Бот запущен!")
app.run_polling()
