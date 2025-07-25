import asyncio
import logging
import os
from decimal import Decimal
import requests
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import locale

from db import init_db_sync, add_address, remove_address, list_addresses
from btc import get_balances_btc, fetch_balance_btc, satoshi_to_btc
from cg import get_prices

# ---------- базовая настройка ----------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
locale.setlocale(locale.LC_ALL, '')

COMMANDS = [
    BotCommand("add",       "Добавить BTC‑адрес"),
    BotCommand("remove",    "Удалить адрес"),
    BotCommand("portfolio", "Показать баланс портфеля"),
    BotCommand("balance",   "Баланс отдельного адреса"),
    BotCommand("help",      "Справка"),
]

def format_num(num):
	return '{:,.0f}'.format(num).replace(',', ' ')

# ---------- обработчики команд ----------
async def setup_commands(application: Application):
    """Однократно публикуем меню для всех пользователей."""
    await application.bot.set_my_commands(COMMANDS)

    # (необязательно) убеждаемся, что в клиенте будет кнопка «Меню»
    from telegram import MenuButtonCommands
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

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
        btc_balnace = satoshi_to_btc(satoshis)
        await update.message.reply_text(
            f"Баланс адреса `{address}`:\n{btc_balnace:.4f} BTC",
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
    lines = ["*💼 Портфель*"] 
    total_sat = 0
    for addr, bal in balances.items():
        if isinstance(bal, Exception):
            lines.append(f"⚠️ {addr[:10]}… — ошибка API")
        else:
            total_sat += bal
            lines.append(f"`{addr[:10]}…` — {satoshi_to_btc(bal):.4f} ฿")

    prices = get_prices("bitcoin", "usd,rub")
    total_btc = satoshi_to_btc(total_sat)
    total_usd = total_btc * Decimal(prices["bitcoin"]['usd'])
    total_rub = total_btc * Decimal(prices["bitcoin"]['rub'])

    lines.append("────────────────────────")
    lines.append(f"*Итого:*  {total_btc:.2f} ฿  {format_num(total_usd)} $  {format_num(total_rub)} ₽")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown"
    )

# ---------- точка входа ----------
def main() -> None:
    # один раз инициализируем БД в отдельном (коротком) цикле
    init_db_sync()

    application = Application.builder().token(TOKEN).post_init(setup_commands).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_cmd))
    application.add_handler(CommandHandler("remove", remove_cmd))
    application.add_handler(CommandHandler("balance", balance_cmd))
    application.add_handler(CommandHandler("portfolio", portfolio_cmd))

    logging.info("Bot is polling…")
    application.run_polling()     # ← БЛОКИРУЕТ поток до Ctrl‑C

if __name__ == "__main__":
    main()
