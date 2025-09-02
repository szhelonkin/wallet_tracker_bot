import asyncio
import logging
import os
import json
from decimal import Decimal
import requests
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import locale
from datetime import datetime

from db import init_db_sync, add_address, remove_address, list_addresses, filter_btc_addresses, filter_eth_addresses, is_addr_eth
from btc import get_balances_btc, fetch_balance_btc, satoshi_to_btc
from eth import fetch_balance_eth, get_balances_eth
from pendle import fetch_pendle_position
from cg import get_prices
from euler import single_vault_position
from rpc_manager import get_balances_concurrent, get_vault_positions_concurrent

# ---------- базовая настройка ----------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
locale.setlocale(locale.LC_ALL, '')

COMMANDS = [
    BotCommand("portfolio", "Показать баланс портфеля"),
    BotCommand("add",       "Добавить BTC ETH‑адрес"),
    BotCommand("remove",    "Удалить адрес"),
    BotCommand("addrlist",      "Список адресов"),
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
        "/addrlist - список адресов"
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

async def addrlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = []
    addrs = await list_addresses(update.effective_user.id)
    for addr in addrs:
    	lines.append(addr)
    if len(lines) == 0:
    	lines = ["У тебя пока нет адресов. Добавь через /add."]
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown"
    )

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
    try:
        await update.message.reply_text("⏳ Считаю портфель…")
        addrs = await list_addresses(update.effective_user.id)
        if not addrs:
            await update.message.reply_text("У тебя пока нет адресов. Добавь через /add.")
            return

        btc_addrs = filter_btc_addresses(addrs)
        balances = await get_balances_btc(btc_addrs)
        lines = ["*💼 Портфель*"]
        lines.append("*Биткоин*") 
        total_sat = 0
        for addr, bal in balances.items():
            if isinstance(bal, Exception):
                lines.append(f"⚠️ {addr[:10]}… — ошибка API")
            else:
                total_sat += bal
                lines.append(f"`{addr[:10]}…` — {satoshi_to_btc(bal):.4f} ฿")

        prices = get_prices("bitcoin,ethereum,tether", "usd,rub")
        total_btc = satoshi_to_btc(total_sat)
        price_btc_usd = Decimal(prices["bitcoin"]['usd'])
        price_btc_rub = Decimal(prices["bitcoin"]['rub'])
        total_usd = total_btc * price_btc_usd
        total_rub = total_btc * price_btc_rub

        lines.append(f"Цена  {format_num(price_btc_usd)} $  {format_num(price_btc_rub)} ₽")
        lines.append("────────────────────────")
        lines.append(f"*BTC:*  {total_btc:.2f} ฿  {format_num(total_usd)} $  {format_num(total_rub)} ₽")

        eth_addrs = filter_eth_addresses(addrs)
        # Use concurrent balance fetching for much faster performance
        eth_balances = await get_balances_concurrent(eth_addrs)
        lines.append("")
        lines.append("*Эфир*")
        total_eth = 0
        for addr, bal in eth_balances.items():
            if isinstance(bal, Exception):
                lines.append(f"⚠️ {addr[:10]}… — ошибка API")
            else:
                total_eth += bal
                lines.append(f"`{addr[:10]}…` — {bal:.4f} Ξ")
        price_eth_usd = Decimal(prices["ethereum"]['usd'])
        price_eth_rub = Decimal(prices["ethereum"]['rub'])
        total_usd_eth = total_eth * price_eth_usd
        total_rub_eth = total_eth * price_eth_rub

        lines.append(f"Цена  {format_num(price_eth_usd)} $  {format_num(price_eth_rub)} ₽")
        lines.append("────────────────────────")
        lines.append(f"*ETH:*  {total_eth:.2f} Ξ  {format_num(total_usd_eth)} $  {format_num(total_rub_eth)} ₽")

        lines.append("")
        lines.append("*DeFi*")
        lines.append("Compound USDT")
        with open('./cache_compound.json', 'r') as file:
            data_compound = json.load(file)
        now = datetime.now()
        file_time = datetime.strptime(data_compound["time"], "%Y-%m-%d %H:%M:%S.%f")
        diff = now - file_time
        diff_secons = diff.seconds
        total_usdt = 0
        for addr in eth_addrs:
            supplied_usdt = Decimal(data_compound["addresses"][addr]["supplied"])
            total_usdt += supplied_usdt
            if diff_secons > 36000:
                lines.append(f"⚠️ `{addr[:10]}…` — {supplied_usdt:.0f} ₮")
            else:
                lines.append(f"`{addr[:10]}…` — {supplied_usdt:.0f} ₮")
        price_usdt_usd = Decimal(prices["tether"]['usd'])
        price_usdt_rub = Decimal(prices["tether"]['rub'])
        total_usd_usdt = total_usdt * price_usdt_usd
        total_rub_usdt = total_usdt * price_usdt_rub

        lines.append(f"Цена  {price_usdt_usd:.2f} $  {price_usdt_rub:.2f} ₽")
        lines.append("────────────────────────")
        lines.append(f"*USDT:*  {total_usdt:.0f} Ξ  {format_num(total_usd_usdt)} $  {format_num(total_rub_usdt)} ₽")

        lines.append("")
        lines.append("Pendle USD")
        total_usd_pendle = 0
        for addr in eth_addrs:
            try:
                supplied_pendle_usd = fetch_pendle_position(addr)
                total_usd_pendle += supplied_pendle_usd 
                lines.append(f"`{addr[:10]}…` — {supplied_pendle_usd:.0f} $")
            except Exception as e:
                logging.warning(f"Error fetching Pendle position for {addr}: {e}")
                lines.append(f"⚠️ `{addr[:10]}…` — ошибка API")
        total_rub_pendle = total_usd_pendle * price_usdt_rub
        lines.append("────────────────────────")
        lines.append(f"*Pendle USD:*  {format_num(total_usd_pendle)} $  {format_num(total_rub_pendle)} ₽")

        lines.append("")
        lines.append("Euler USD")
        total_eth_euler = 0
        total_usd_euler = 0
        
        # Use concurrent vault position fetching for much faster performance
        if eth_addrs:
            try:
                from euler import ACCOUNT_LENS, ABI
                euler_positions = await get_vault_positions_concurrent(
                    eth_addrs, 
                    "0xD8b27CF359b7D15710a5BE299AF6e7Bf904984C2", 
                    ACCOUNT_LENS,
                    ABI
                )
                
                for addr in eth_addrs:
                    supplied_euler_eth = euler_positions.get(addr, 0)
                    total_eth_euler += supplied_euler_eth
                    total_usd_euler += supplied_euler_eth * price_eth_usd 
                    lines.append(f"`{addr[:10]}…` — {supplied_euler_eth:.0f} Ξ")
            except Exception as e:
                logging.warning(f"Error fetching Euler positions: {e}")
                for addr in eth_addrs:
                    lines.append(f"⚠️ `{addr[:10]}…` — ошибка API")
        
        total_rub_euler = total_usd_euler * price_usdt_rub
        lines.append("────────────────────────")
        lines.append(f"*Euler:*  {total_eth_euler:.2f} Ξ  {format_num(total_usd_euler)} $  {format_num(total_rub_euler)} ₽")

        lines.append("")
        alt_usd = 0
        alt_rub = 0
        alt_usd += total_usd_eth
        alt_rub += total_rub_eth
        alt_usd += total_usd_usdt
        alt_rub += total_rub_usdt
        alt_usd += total_usd_pendle
        alt_rub += total_rub_pendle
        alt_usd += total_usd_euler
        alt_rub += total_rub_euler

        lines.append("────────────────────────")
        lines.append(f"*BTC:*  {format_num(total_usd)} $  {format_num(total_rub)} ₽")
        lines.append("────────────────────────")
        lines.append(f"*Альты:*  {format_num(alt_usd)} $  {format_num(alt_rub)} ₽")

        total_usd += alt_usd
        total_rub += alt_rub
        
        lines.append("────────────────────────")
        lines.append(f"*Итого:*  {format_num(total_usd)} $  {format_num(total_rub)} ₽")

        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in portfolio command: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при расчете портфеля. Попробуйте позже."
        )

# ---------- точка входа ----------
def main() -> None:
    # один раз инициализируем БД в отдельном (коротком) цикле
    init_db_sync()

    application = Application.builder().token(TOKEN).post_init(setup_commands).build()

    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("add", add_cmd))
    application.add_handler(CommandHandler("remove", remove_cmd))
    application.add_handler(CommandHandler("addrlist", addrlist_cmd))
    application.add_handler(CommandHandler("balance", balance_cmd))
    application.add_handler(CommandHandler("portfolio", portfolio_cmd))

    logging.info("Bot is polling…")
    application.run_polling()     # ← БЛОКИРУЕТ поток до Ctrl‑C

if __name__ == "__main__":
    main()
