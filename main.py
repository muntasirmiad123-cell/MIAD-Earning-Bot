# MIAD BOT - FINAL SAFE VERSION - GITHUB READY
# pip install python-telegram-bot pymongo

import os
import random
from datetime import datetime, date
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ================= SECRET - GITHUB E KHALI THAKBE =================
# Asol link Render er Environment Variables e bosabi
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = MongoClient(MONGO_URI)
db = client["miad_bot"]
users = db["users"]

# ================= PUBLIC - ADS ID - GITHUB E DITE PARBI =================
ADSGRAM_BLOCK_ID = "PAST YOUR ADSGRAM CODE HERE"
MONETAG_ZONE_ID = "PAST YOUR MONETAG CODE HERE"
MONETAG_LINK = "PAST YOUR MONETAG LINK HERE"

# ================= RATE SETTINGS =================
ADSGRAM_REWARD = 25
MONETAG_REWARD = 10
DAILY_AD_LIMIT = 15
REFER_REWARD = 50
MIN_WITHDRAW_MIAD = 10000
RATE_MIAD_PER_USDT = 100000
WITHDRAW_FEE_PERCENT = 10
COIN_PAYOUT = 1.92
DICE_PAYOUT = 5.0
COIN_WIN_PROB = 0.48

# ================= HELPERS =================
def get_user(user_id, username=""):
    user = users.find_one({"user_id": user_id})
    today_str = str(date.today())
    if not user:
        user = {
            "user_id": user_id, "username": username, "balance": 0,
            "adsgram_today": 0, "monetag_today": 0, "last_reset_date": today_str,
            "checkin_days": 0, "last_checkin": "", "checkin_history": [],
            "refer_count": 0, "refer_earned": 0, "referred_by": None, "refer_rewarded": False,
            "total_ads_watched": 0, "game_history": [], "withdraw_history": [],
            "state": None, "temp_bet": 0, "temp_game": None, "temp_mines": None, "ton_address": ""
        }
        users.insert_one(user)
        return user
    if user.get("last_reset_date") != today_str:
        users.update_one({"user_id": user_id}, {"$set": {"adsgram_today": 0, "monetag_today": 0, "last_reset_date": today_str}})
        user["adsgram_today"] = 0
        user["monetag_today"] = 0
    return users.find_one({"user_id": user_id})

def update_user(user_id, data):
    users.update_one({"user_id": user_id}, {"$set": data})

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Watch Ad", callback_data="watch_ad")],
        [InlineKeyboardButton("Daily Check-in", callback_data="checkin")],
        [InlineKeyboardButton("Refer", callback_data="refer")],
        [InlineKeyboardButton("Game", callback_data="game")],
        [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])

def check_refer_reward(user):
    if user.get("referred_by") and not user.get("refer_rewarded"):
        if user.get("checkin_days", 0) >= 7 and user.get("total_ads_watched", 0) >= 10:
            referrer_id = user["referred_by"]
            ref = users.find_one({"user_id": referrer_id})
            if ref:
                users.update_one({"user_id": referrer_id}, {"$inc": {"balance": REFER_REWARD, "refer_count": 1, "refer_earned": REFER_REWARD}})
                users.update_one({"user_id": user["user_id"]}, {"$set": {"refer_rewarded": True}})
                return True
    return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = users.find_one({"user_id": user.id})
    if context.args and not existing:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                users.update_one({"user_id": user.id}, {"$set": {"referred_by": referrer_id}}, upsert=True)
        except:
            pass
    get_user(user.id, user.username)
    await update.message.reply_text(
        f"Welcome {user.first_name} to MIAD Bot!\n\nEarn MIAD Coin by watching Ads, Check-in, and Playing Games.\n\nChoose from menu:",
        reply_markup=main_menu()
    )

async def show_balance(query, user_id):
    u = get_user(user_id)
    text = f"Your Balance\n\nBalance: {u['balance']} MIAD\nTotal Ads: {u['total_ads_watched']}\nCheck-in: {u['checkin_days']} days\nRefer: {u['refer_count']} users | Earned: {u['refer_earned']} MIAD\n\nUSDT Value: {u['balance']/RATE_MIAD_PER_USDT:.4f} USDT"
    await query.edit_message_text(text, reply_markup=back_btn())

async def do_checkin(query, user_id):
    u = get_user(user_id)
    today = str(date.today())
    if u.get("last_checkin") == today:
        await query.answer("You already checked in today!", show_alert=True)
        return
    new_days = u["checkin_days"] + 1
    update_user(user_id, {"last_checkin": today, "checkin_days": new_days, "checkin_history": u["checkin_history"] + [today]})
    updated = get_user(user_id)
    check_refer_reward(updated)
    await query.answer(f"Check-in Done! Total: {new_days} days", show_alert=True)

async def watch_ad_menu(query):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Adsgram Ad - {ADSGRAM_REWARD} MIAD (15/Day)", callback_data="ad_adsgram")],
        [InlineKeyboardButton(f"Monetag Ad - {MONETAG_REWARD} MIAD (15/Day)", callback_data="ad_monetag")],
        [InlineKeyboardButton("Back", callback_data="back")],
    ])
    await query.edit_message_text("Which Ad do you want to watch?", reply_markup=kb)

async def give_ad_reward(query, user_id, ad_type):
    u = get_user(user_id)
    if ad_type == "adsgram":
        if u["adsgram_today"] >= DAILY_AD_LIMIT:
            await query.answer("Today's Adsgram limit is over!", show_alert=True)
            return
        # ADSGRAM VERIFY HERE - Use ADSGRAM_BLOCK_ID
        new_bal = u["balance"] + ADSGRAM_REWARD
        update_user(user_id, {"balance": new_bal, "adsgram_today": u["adsgram_today"]+1, "total_ads_watched": u["total_ads_watched"]+1})
        check_refer_reward(get_user(user_id))
        await query.answer(f"+{ADSGRAM_REWARD} MIAD! Balance: {new_bal}", show_alert=True)
    if ad_type == "monetag":
        if u["monetag_today"] >= DAILY_AD_LIMIT:
            await query.answer("Today's Monetag limit is over!", show_alert=True)
            return
        # MONETAG VERIFY HERE - Use MONETAG_ZONE_ID / MONETAG_LINK
        new_bal = u["balance"] + MONETAG_REWARD
        update_user(user_id, {"balance": new_bal, "monetag_today": u["monetag_today"]+1, "total_ads_watched": u["total_ads_watched"]+1})
        check_refer_reward(get_user(user_id))
        await query.answer(f"+{MONETAG_REWARD} MIAD! Balance: {new_bal}", show_alert=True)

async def show_refer(query, user_id, bot_username):
    u = get_user(user_id)
    link = f"https://t.me/{bot_username}?start={user_id}"
    text = f"Refer & Earn 50 MIAD\n\nYour Link:\n`{link}`\n\nCondition:\n- Invited user must Check-in for 7 days\n- Must watch minimum 10 Ads\n- Then you will get 50 MIAD\n\nYour Refer: {u['refer_count']} users\nRefer Earned: {u['refer_earned']} MIAD"
    await query.edit_message_text(text, reply_markup=back_btn(), parse_mode="Markdown")

async def game_menu(query):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Coin Flip (1.92x)", callback_data="game_coin")],
        [InlineKeyboardButton("Dice (5x)", callback_data="game_dice")],
        [InlineKeyboardButton("Mines", callback_data="game_mines")],
        [InlineKeyboardButton("Back", callback_data="back")],
    ])
    await query.edit_message_text("Choose a Game:\n\nSelect game first, then select bet amount.", reply_markup=kb)

async def ask_bet(query, user_id, game):
    update_user(user_id, {"temp_game": game, "state": "waiting_bet"})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("100 MIAD", callback_data="bet_100"), InlineKeyboardButton("500 MIAD", callback_data="bet_500")],
        [InlineKeyboardButton("1000 MIAD", callback_data="bet_1000"), InlineKeyboardButton("Back", callback_data="back")],
    ])
    await query.edit_message_text(f"{game} - How much MIAD do you want to bet?\n\nBalance: {get_user(user_id)['balance']} MIAD", reply_markup=kb)

async def play_coin(query, user_id, bet):
    u = get_user(user_id)
    if u["balance"] < bet:
        await query.answer("Low balance!", show_alert=True)
        return
    win = random.random() < COIN_WIN_PROB
    result = random.choice(["Head", "Tail"])
    if win:
        win_amt = int(bet * COIN_PAYOUT)
        profit = win_amt - bet
        new_bal = u["balance"] - bet + win_amt
        msg = f"Coin Flip: {result}\n\nWIN! +{profit} MIAD\nPayout: {COIN_PAYOUT}x\nBalance: {new_bal}"
    else:
        new_bal = u["balance"] - bet
        msg = f"Coin Flip: {result}\n\nLOSS! -{bet} MIAD\nBalance: {new_bal}"
    update_user(user_id, {"balance": new_bal, "game_history": u["game_history"] + [{"game": "coin", "bet": bet, "win": win}]})
    await query.edit_message_text(msg, reply_markup=back_btn())

async def play_dice(query, user_id, bet):
    u = get_user(user_id)
    if u["balance"] < bet:
        await query.answer("Low balance!", show_alert=True)
        return
    dice = random.randint(1, 6)
    win = (dice == 6)
    if win:
        win_amt = int(bet * DICE_PAYOUT)
        new_bal = u["balance"] - bet + win_amt
        msg = f"Dice: {dice}\n\nWIN! +{win_amt-bet} MIAD (5x)\nBalance: {new_bal}"
    else:
        new_bal = u["balance"] - bet
        msg = f"Dice: {dice}\n\nLOSS! -{bet} MIAD\nBalance: {new_bal}"
    update_user(user_id, {"balance": new_bal, "game_history": u["game_history"] + [{"game": "dice", "bet": bet, "win": win}]})
    await query.edit_message_text(msg, reply_markup=back_btn())

async def play_mines_start(query, user_id, bet):
    u = get_user(user_id)
    if u["balance"] < bet:
        await query.answer("Low balance!", show_alert=True)
        return
    mines = random.sample(range(9), 3)
    update_user(user_id, {"temp_mines": {"mines": mines, "revealed": [], "bet": bet, "multiplier": 1.0}})
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("?", callback_data=f"mine_{i}") for i in range(3)],
                               [InlineKeyboardButton("?", callback_data=f"mine_{i}") for i in range(3,6)],
                               [InlineKeyboardButton("?", callback_data=f"mine_{i}") for i in range(6,9)],
                               [InlineKeyboardButton("Cashout", callback_data="mine_cashout")]])
    await query.edit_message_text(f"Mines - Bet: {bet} MIAD\n\nOpen safe tiles, multiplier will increase. If you hit a mine, you lose everything!", reply_markup=kb)

async def withdraw_menu(query, user_id):
    u = get_user(user_id)
    usdt = u["balance"] / RATE_MIAD_PER_USDT
    text = f"Withdraw\n\nBalance: {u['balance']} MIAD ({usdt:.4f} USDT)\nMin Withdraw: {MIN_WITHDRAW_MIAD} MIAD (0.10 USDT)\nFee: 10% - You will get 0.09 USDT\nNetwork: TON\n\nSend your TON Address:"
    update_user(user_id, {"state": "waiting_ton"})
    await query.edit_message_text(text, reply_markup=back_btn())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    text = update.message.text.strip()
    if u.get("state") == "waiting_ton":
        update_user(user_id, {"ton_address": text, "state": "waiting_amount"})
        await update.message.reply_text(f"TON Address Saved: {text}\n\nNow how much MIAD do you want to withdraw? Type number (Min 10000):")
        return
    if u.get("state") == "waiting_amount":
        try:
            amt = int(text)
            if amt < MIN_WITHDRAW_MIAD:
                await update.message.reply_text("Minimum 10000 MIAD required!")
                return
            if amt > u["balance"]:
                await update.message.reply_text("Low balance!")
                return
            fee = int(amt * WITHDRAW_FEE_PERCENT / 100)
            net_miad = amt - fee
            net_usdt = net_miad / RATE_MIAD_PER_USDT
            new_bal = u["balance"] - amt
            update_user(user_id, {"balance": new_bal, "state": None, "withdraw_history": u["withdraw_history"] + [{"amount": amt, "fee": fee, "net": net_miad, "address": u["ton_address"], "date": str(datetime.now())}]})
            await update.message.reply_text(f"Withdraw Request Done!\n\nWithdraw: {amt} MIAD\nFee (10%): {fee} MIAD\nYou Will Get: {net_miad} MIAD = {net_usdt:.4f} USDT\nAddress: {u['ton_address']}\n\nAdmin will send within 24h.", reply_markup=main_menu())
        except:
            await update.message.reply_text("Please type only number!")
        return

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    bot_username = context.bot.username

    if data == "back":
        await query.edit_message_text("Menu:", reply_markup=main_menu())
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "watch_ad":
        await watch_ad_menu(query)
    elif data == "checkin":
        await do_checkin(query, user_id)
        await query.edit_message_text("Menu:", reply_markup=main_menu())
    elif data == "refer":
        await show_refer(query, user_id, bot_username)
    elif data == "game":
        await game_menu(query)
    elif data == "withdraw":
        await withdraw_menu(query, user_id)
    elif data == "ad_adsgram":
        await give_ad_reward(query, user_id, "adsgram")
    elif data == "ad_monetag":
        await give_ad_reward(query, user_id, "monetag")
    elif data == "game_coin":
        await ask_bet(query, user_id, "coin")
    elif data == "game_dice":
        await ask_bet(query, user_id, "dice")
    elif data == "game_mines":
        await ask_bet(query, user_id, "mines")
    elif data.startswith("bet_"):
        bet = int(data.split("_")[1])
        u = get_user(user_id)
        game = u.get("temp_game")
        if game == "coin":
            await play_coin(query, user_id, bet)
        elif game == "dice":
            await play_dice(query, user_id, bet)
        elif game == "mines":
            await play_mines_start(query, user_id, bet)
    elif data.startswith("mine_"):
        idx = int(data.split("_")[1])
        u = get_user(user_id)
        m = u.get("temp_mines")
        if not m:
            return
        if idx in m["mines"]:
            new_bal = u["balance"] - m["bet"]
            update_user(user_id, {"balance": new_bal, "temp_mines": None})
            await query.edit_message_text(f"BOOM! You hit a mine!\n\nLOSS -{m['bet']} MIAD\nBalance: {new_bal}", reply_markup=back_btn())
        else:
            if idx not in m["revealed"]:
                m["revealed"].append(idx)
                m["multiplier"] += 0.4
                update_user(user_id, {"temp_mines": m})
                await query.answer(f"Safe! Multiplier: {m['multiplier']:.2f}x", show_alert=True)
    elif data == "mine_cashout":
        u = get_user(user_id)
        m = u.get("temp_mines")
        if not m:
            return
        win_amt = int(m["bet"] * m["multiplier"])
        new_bal = u["balance"] - m["bet"] + win_amt
        update_user(user_id, {"balance": new_bal, "temp_mines": None})
        await query.edit_message_text(f"Cashout!\n\nWIN +{win_amt - m['bet']} MIAD\nMultiplier: {m['multiplier']:.2f}x\nBalance: {new_bal}", reply_markup=back_btn())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("MIAD Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
