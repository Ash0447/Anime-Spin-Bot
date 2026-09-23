import json
import random
import asyncio
import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from character_generator import load_universes, build_character
from battle_engine import simulate_battle

# --- Dummy Web Server for Render ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Anime Spin Battle Bot is awake and running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# --- Bot Data Loading ---
ALL_UNIVERSES = load_universes("universes.json")
ACTIVE_BATTLES = {}

# --- Database Methods ---
def load_json(filename):
    try:
        with open(filename, 'r') as f: return json.load(f)
    except: return {}

def save_json(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

def init_player(user_id, name):
    players = load_json('players.json')
    str_id = str(user_id)
    if str_id not in players:
        players[str_id] = {"name": name, "wins": 0, "losses": 0, "bounty": 0}
        save_json('players.json', players)
    return players[str_id]

def update_bounty(user_id, won):
    players = load_json('players.json')
    str_id = str(user_id)
    if won:
        players[str_id]["wins"] += 1
        players[str_id]["bounty"] += random.randint(50, 150)
    else:
        players[str_id]["losses"] += 1
        players[str_id]["bounty"] = max(0, players[str_id]["bounty"] - random.randint(20, 50))
    save_json('players.json', players)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    players = load_json('players.json')
    
    if str(user.id) in players:
        await update.message.reply_text("⚔️ You have already started your journey! Head over to the main group and use /battle to fight.")
        return

    init_player(user.id, user.first_name)
    welcome_text = (
        "✨ <b>Welcome to Anime Spin Battle!</b> ✨\n\n"
        "Step into the arena where fate decides your power! Test your luck, spin the wheel of destiny, "
        "and clash against rivals to become the ultimate champion.\n\n"
        "<i>Are you ready to forge your legacy?</i>"
    )
    keyboard = [[InlineKeyboardButton("Continue ➡️", callback_data="start_continue")]]
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    instructions = (
        "📜 <b>How to Play:</b>\n\n"
        "🔹 Use /myinfo to view your stats and bounty.\n"
        "🔹 Use /battle <i>[by replying to a user]</i> in groups to challenge them.\n\n"
        "💬 <b>Join the Main Chat:</b> https://t.me/AnimeSpinBattle"
    )
    await query.edit_message_text(text=instructions, parse_mode='HTML', disable_web_page_preview=True)

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = init_player(user.id, user.first_name)
    total_games = player['wins'] + player['losses']
    win_rate = (player['wins'] / total_games * 100) if total_games > 0 else 0.0
    
    info_text = (
        f"👤 <b>Player:</b> {player['name']}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
        f"📊 <b><u>Battle Stats</u></b>\n"
        f"🏆 <b>Wins:</b> {player['wins']}\n"
        f"💀 <b>Losses:</b> {player['losses']}\n"
        f"📈 <b>Win Rate:</b> {win_rate:.1f}%\n\n"
        f"💰 <b>Bounty:</b> {player['bounty']} 🪙"
    )
    await update.message.reply_text(info_text, parse_mode='HTML')

# --- Battle System ---
async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        await update.message.reply_text("⚔️ Battles can only be fought in groups!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ You must reply to the user you want to battle!")
        return

    challenger = update.effective_user
    opponent = update.message.reply_to_message.from_user

    if challenger.id == opponent.id or opponent.is_bot:
        await update.message.reply_text("⚠️ Invalid target.")
        return

    init_player(challenger.id, challenger.first_name)
    init_player(opponent.id, opponent.first_name)

    battle_id = f"{challenger.id}_{opponent.id}_{update.message.message_id}"
    ACTIVE_BATTLES[battle_id] = {
        "p1_id": challenger.id, "p1_name": challenger.first_name,
        "p2_id": opponent.id, "p2_name": opponent.first_name
    }

    keyboard = [[
        InlineKeyboardButton("✅ Accept", callback_data=f"acc_{battle_id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"dec_{battle_id}")
    ]]
    await update.message.reply_text(
        f"⚔️ <b>{opponent.first_name}</b>, you have been challenged by <b>{challenger.first_name}</b>!",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
    )

async def battle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, battle_id = query.data.split('_', 1)
    
    if battle_id not in ACTIVE_BATTLES:
        await query.answer("This battle has expired.", show_alert=True)
        return
        
    b_data = ACTIVE_BATTLES[battle_id]
    
    if query.from_user.id != b_data['p2_id']:
        await query.answer("This challenge is not for you!", show_alert=True)
        return
        
    if action == "dec":
        await query.edit_message_text(f"❌ Match declined by {b_data['p2_name']}.")
        del ACTIVE_BATTLES[battle_id]
        return

    await query.answer()
    await query.edit_message_text("🎡 <b>Spinning Universe...</b>", parse_mode='HTML')
    await asyncio.sleep(2)
    
    universe_key = random.choice(list(ALL_UNIVERSES.keys()))
    universe_data = ALL_UNIVERSES[universe_key]
    
    await query.edit_message_text(f"🌌 <b>Universe: {universe_data['name']}</b>\nGenerating characters...", parse_mode='HTML')
    await asyncio.sleep(2)

    p1 = build_character(universe_data)
    p2 = build_character(universe_data)

    build_text = (
        f"🌌 <b>{universe_data['name']} Arena</b>\n\n"
        f"👤 <b>{b_data['p1_name']}</b> [{p1['loadout']['rank']}]\n"
        f"🗡️ {p1['loadout']['weapon']} | 🌀 {p1['loadout']['technique']}\n"
        f"💥 Power: <code>{p1['combat_rating']}</code>  ❤️ HP: {p1['stats']['hp']}\n\n"
        f"👤 <b>{b_data['p2_name']}</b> [{p2['loadout']['rank']}]\n"
        f"🗡️ {p2['loadout']['weapon']} | 🌀 {p2['loadout']['technique']}\n"
        f"💥 Power: <code>{p2['combat_rating']}</code>  ❤️ HP: {p2['stats']['hp']}\n\n"
        f"⚔️ <i>Calculating battle...</i>"
    )
    await query.edit_message_text(build_text, parse_mode='HTML')
    await asyncio.sleep(3)

    logs = simulate_battle(p1, p2, b_data['p1_name'], b_data['p2_name'])
    
    p1_won = p1["stats"]["hp"] > 0
    winner_name = b_data['p1_name'] if p1_won else b_data['p2_name']
    
    update_bounty(b_data['p1_id'], won=p1_won)
    update_bounty(b_data['p2_id'], won=(not p1_won))

    summary_logs = "\n".join(logs[-8:])
    
    final_output = (
        f"{build_text.replace('⚔️ <i>Calculating battle...</i>', '<b><u>Match Highlights:</u></b>')}\n"
        f"{summary_logs}\n\n"
        f"🏆 <b>WINNER: {winner_name}</b> 🏆\n"
        f"Bounties have been updated!"
    )
    
    await query.edit_message_text(final_output, parse_mode='HTML')
    del ACTIVE_BATTLES[battle_id]

# --- App Entry ---
if __name__ == '__main__':
    # 1. Start the web server in a parallel thread to satisfy Render's port requirement
    Thread(target=run_web).start()
    
    # 2. Start the Telegram Bot
    TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Remember to insert your token here before deploying
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('myinfo', myinfo))
    app.add_handler(CommandHandler('battle', battle))
    app.add_handler(CallbackQueryHandler(start_button, pattern="^start_continue$"))
    app.add_handler(CallbackQueryHandler(battle_callback, pattern="^(acc|dec)_"))
    
    print("Bot is polling...")
    app.run_polling()
