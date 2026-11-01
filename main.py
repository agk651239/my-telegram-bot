from pyrogram import Client, idle
import asyncio
import aiohttp
import logging
from aiohttp import web
from config import *
from database import * 
from helpers import *

# लॉगिंग सेटअप
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# बोट क्लाइंट सेटअप
# यहाँ plugins=dict(root="plugins") जोड़ा गया है, यही बोट को बताता है कि 
# सारे कमांड्स plugins फोल्डर से लोड करने हैं।
app = Client(
    "bot_session", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    in_memory=True,
    plugins=dict(root="plugins")
)

# --- प्रीमियम स्टेबिलिटी (वेब-सर्वर SSL सपोर्ट के साथ) ---
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running successfully!"))
    
    protocol = "https" if HAS_SSL else "http"
    logging.info(f"🌐 वेब-सर्वर {protocol}://0.0.0.0:{PORT} पर शुरू हो रहा है।")
    
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(PORT)).start()

async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(60)
            try:
                protocol = "https" if HAS_SSL else "http"
                async with session.get(f"{protocol}://localhost:{PORT}") as resp:
                    logging.info(f"Pinged server, status: {resp.status}")
            except Exception as e:
                logging.error(f"❌ Ping Failed: {e}")

# --- बैकग्राउंड टास्क: डेली रिपोर्ट (हर 24 घंटे में) ---
async def send_daily_report():
    while True:
        await asyncio.sleep(86400)
        try:
            total_users = await db.users.count_documents({})
            total_files = await db.files.count_documents({})
            report_text = (
                f"📅 **Daily Report**\n\n"
                f"📊 **Total Users:** `{total_users}`\n"
                f"📂 **Total Files Indexed:** `{total_files}`\n"
                f"🟢 **Bot Status:** Online & Running"
            )
            await app.send_message(LOG_CHANNEL, report_text)
        except Exception as e:
            logging.error(f"Daily Report Error: {e}")

# --- गुमशुदा वेरिएबल्स (Missing Keys) की चेतावनी भेजने का फंक्शन ---
async def send_missing_keys_alert():
    if missing_keys and ADMIN_ID:
        try:
            keys_str = ", ".join(missing_keys)
            alert_text = (
                f"⚠️ **कॉन्फ़िगरेशन चेतावनी / Missing Keys Alert**\n\n"
                f"रेंडर में निम्नलिखित पर्यावरण चर (Environment Variables) गायब या अनकॉफ़िगर हैं:\n"
                f"`{keys_str}`"
            )
            await app.send_message(ADMIN_ID, alert_text)
        except Exception:
            pass

# --- स्टार्टअप सीक्वेंस ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    loop.run_until_complete(create_indexes())
    
    try:
        app.start()
        print("✅ Bot is online!")
        
        loop.run_until_complete(send_missing_keys_alert())
        
        try:
            resolved_log_channel = LOG_CHANNEL
            if isinstance(LOG_CHANNEL, str):
                if "t.me/" in LOG_CHANNEL:
                    resolved_log_channel = "@" + LOG_CHANNEL.strip("/").split("t.me/")[-1]
                elif not LOG_CHANNEL.startswith("@") and not LOG_CHANNEL.startswith("-") and not LOG_CHANNEL.isdigit():
                    resolved_log_channel = "@" + LOG_CHANNEL
                elif LOG_CHANNEL.lstrip('-').isdigit():
                    resolved_log_channel = int(LOG_CHANNEL)
            
            loop.run_until_complete(app.send_message(resolved_log_channel, "🟢 **Bot Restarted & Log Channel Connected Successfully!**"))
        except Exception as e:
            print(f"⚠️ Log Channel Startup Warning: {e}")

        loop.create_task(keep_alive())
        loop.create_task(send_daily_report())
        idle()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        app.stop()
