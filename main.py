import asyncio
import logging
import os
from decimal import Decimal
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from db import init_db_sync, add_address, remove_address, list_addresses
from btc import get_balances_btc, fetch_balance_btc, satoshi_to_btc

# ---------- базовая настройка ----------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


# ---------- обработчики команд ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет!\n"
        "/add <addr> — добавить адрес\n"
        "/remove <addr> — удалить адрес\n"
        "/portfolio — показать баланс портфеля\n"
        "Для одиночного адреса можешь использовать /balance <addr>."
    )

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Формат: /add <btc‑адрес>")
        return
    addr = context.args[0]
    ok = await add_address(update.effective_user.id, addr)
    msg = "✅ Адрес добавлен." if ok else "⚠️ Этот адрес уже есть в портфеле."
    await update.message.reply_text(msg)

async def remove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Формат: /remove <btc‑адрес>")
        return
    addr = context.args[0]
    ok = await remove_address(update.effective_user.id, addr)
    msg = "🗑️ Удалил." if ok else "🤷 Адрес не найден в твоём списке."
    await update.message.reply_text(msg)

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Формат: /balance <btc‑адрес>")
        return

    address = context.args[0]
    await update.message.reply_text("⏳ Смотрю…")
    try:
        satoshis = await asyncio.to_thread(fetch_balance_btc, address)
        await update.message.reply_text(
            f"Баланс адреса `{address}`:\n{ satoshi_to_btc(satoshis)}",
            parse_mode="Markdown",
        )
    except requests.HTTPError as e:
        await update.message.reply_text(f"⛔️ Ошибка API: {e.response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Что‑то пошло не так: {e}")

async def portfolio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Считаю портфель…")
    addrs = await list_addresses(update.effective_user.id)
    if not addrs:
        await update.message.reply_text("У тебя пока нет адресов. Добавь через /add.")
        return

    balances = await get_balances_btc(addrs)
    lines = []
    total_sat = 0
    for addr, bal in balances.items():
        if isinstance(bal, Exception):
            lines.append(f"⚠️ {addr[:10]}… — ошибка API")
        else:
            total_sat += bal
            lines.append(f"`{addr[:10]}…` — {satoshi_to_btc(bal)}")

    lines.append("—" * 25)
    lines.append(f"**Итого:** {satoshi_to_btc(total_sat)}")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown"
    )

# ---------- точка входа ----------
def main() -> None:
    # один раз инициализируем БД в отдельном (коротком) цикле
    init_db_sync()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_cmd))
    application.add_handler(CommandHandler("remove", remove_cmd))
    application.add_handler(CommandHandler("balance", balance_cmd))
    application.add_handler(CommandHandler("portfolio", portfolio_cmd))

    logging.info("Bot is polling…")
    application.run_polling()     # ← БЛОКИРУЕТ поток до Ctrl‑C

if __name__ == "__main__":
    main()
