import asyncio, logging, re, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from planner import TravelPlanner
from llm import LLMClient
from db import get_session, set_session, clear_session, save_trip
from security import contains_sensitive_data, sanitize, is_rate_limited, hash_uid, MAX_IMG_BYTES

log = logging.getLogger("wanderon.bot")

STATES = ["idle", "dest", "source", "dates", "members", "budget", "done"]
IDLE, DEST, SOURCE, DATES, MEMBERS, BUDGET, DONE = range(7)

GUIDE_MENU = [
    [InlineKeyboardButton("🗣 Language phrases",  callback_data="guide_language"),
     InlineKeyboardButton("📱 SIM card guide",    callback_data="guide_sim")],
    [InlineKeyboardButton("🛡 Safety & scams",    callback_data="guide_safety"),
     InlineKeyboardButton("💵 Money & tipping",   callback_data="guide_money")],
    [InlineKeyboardButton("🎭 Culture & etiquette",callback_data="guide_culture"),
     InlineKeyboardButton("🍜 Food guide",        callback_data="guide_food")],
    [InlineKeyboardButton("🚌 Local transport",   callback_data="guide_transport"),
     InlineKeyboardButton("🧳 Packing list",      callback_data="guide_packing")],
]

class WanderOnBot:
    def __init__(self, token, provider, api_key, model, otm="", owm="", er="", serpapi=""):
        self.token = token
        self.llm_provider = provider
        self.llm_model = model
        self.running = False
        self.bot_username = None
        self.llm = LLMClient(provider, api_key, model)
        self.planner = TravelPlanner(self.llm, otm, owm, er, serpapi)
        self.app = Application.builder().token(token).build()
        self._reg()

    def _reg(self):
        a = self.app
        a.add_handler(CommandHandler("start",   self.c_start))
        a.add_handler(CommandHandler("plan",    self.c_plan))
        a.add_handler(CommandHandler("help",    self.c_help))
        a.add_handler(CommandHandler("cancel",  self.c_cancel))
        a.add_handler(CommandHandler("history", self.c_history))
        a.add_handler(CommandHandler("cost",    self.c_cost))
        a.add_handler(CommandHandler("guide",   self.c_guide))
        a.add_handler(CommandHandler("save",    self.c_save))
        a.add_handler(CommandHandler("hotels",  self.c_hotels))
        a.add_handler(CallbackQueryHandler(self.cb))
        a.add_handler(MessageHandler(filters.PHOTO, self.h_photo))
        a.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.h_msg))
        a.add_error_handler(self.h_err)

    async def run(self):
        self.running = True
        await self.app.initialize()
        await self.app.start()
        me = await self.app.bot.get_me()
        self.bot_username = me.username
        log.info(f"@{self.bot_username} online")
        await self.app.updater.start_polling(drop_pending_updates=True)
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        try:
            if self.app.updater.running:
                await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        except Exception as e:
            log.warning(f"stop err: {e}")

    async def h_err(self, update, ctx):
        log.error(f"bot err: {ctx.error}")
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("Something went wrong. Please try again or use /cancel.")

    async def _rl(self, update: Update) -> bool:
        uid = str(update.effective_user.id)
        if is_rate_limited(uid):
            await update.message.reply_text("You are sending messages too fast. Please wait a minute.")
            return False
        return True

    async def c_start(self, u: Update, _):
        await u.message.reply_text(
            "Welcome to WanderOn!\n\n"
            "I am your complete AI travel guide. I use real hotel data from Booking.com and live web search — no hallucinated hotel names.\n\n"
            "I plan:\n"
            "- Day-wise itinerary with real places\n"
            "- Real hotels within your budget with booking links\n"
            "- Complete cost breakdown\n"
            "- Flights & transport options\n"
            "- Local cab apps & fares\n"
            "- Language phrases & SIM guide\n"
            "- Safety, scam alerts & embassy info\n"
            "- Visa & health info\n\n"
            "Send a photo of any place — I will identify it!\n\n"
            "/plan — Start planning\n"
            "/cost — Estimate trip cost\n"
            "/guide — City guide menu\n"
            "/hotels — Search hotels only\n"
            "/help — All commands"
        )

    async def c_help(self, u: Update, _):
        serpapi_note = "Yes (SerpAPI connected — Google Hotels data)" if self.planner.serpapi_key else "No (using Booking.com scrape — still real data)"
        vision_note  = "Yes" if self.planner.vision_ok() else "No (switch to a vision model in Settings)"
        await u.message.reply_text(
            "WanderOn Commands:\n\n"
            "/plan — Complete trip planner\n"
            "/cost — Cost estimator for any destination\n"
            "/guide — City guide (language, SIM, safety, money, culture, food, transport, packing)\n"
            "/hotels — Search real hotels for a destination\n"
            "/history — Your last 5 trips\n"
            "/save — Export current plan\n"
            "/cancel — Cancel current session\n\n"
            f"Real hotel data: Always (Booking.com + web)\n"
            f"Google Hotels (SerpAPI): {serpapi_note}\n"
            f"Image recognition: {vision_note}\n\n"
            "Note: Never share card numbers, UPI IDs, or passwords here."
        )

    async def c_cancel(self, u: Update, _):
        await clear_session(str(u.effective_user.id))
        await u.message.reply_text("Cancelled. Type /plan to start a new trip.")

    async def c_plan(self, u: Update, _):
        uid = str(u.effective_user.id)
        await set_session(uid, STATES[DEST], {})
        await u.message.reply_text(
            "Let's plan your trip!\n\nWhere do you want to go?\nExamples: Paris, Bali, Tokyo, Kodaikanal, New York, Dubai"
        )

    async def c_cost(self, u: Update, _):
        await set_session(str(u.effective_user.id), "cost_dest", {})
        await u.message.reply_text("Cost Estimator\n\nWhich destination do you want to estimate costs for?")

    async def c_hotels(self, u: Update, _):
        await set_session(str(u.effective_user.id), "hotel_dest", {})
        await u.message.reply_text(
            "Hotel Search\n\nWhich city/destination are you looking for hotels in?"
        )

    async def c_guide(self, u: Update, _):
        uid = str(u.effective_user.id)
        session = await get_session(uid)
        dest = session["data"].get("destination", "")
        if not dest:
            await u.message.reply_text("Which destination do you want a guide for?")
            await set_session(uid, "guide_dest", {})
            return
        await u.message.reply_text(
            f"City Guide for {dest}\nWhat would you like to know?",
            reply_markup=InlineKeyboardMarkup(GUIDE_MENU)
        )

    async def c_history(self, u: Update, _):
        import aiosqlite
        from db import get_db_path
        uid = str(u.effective_user.id)
        async with aiosqlite.connect(get_db_path()) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT destination,dates,members,budget,currency FROM trips WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
                (uid,)
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            await u.message.reply_text("No trips yet. Use /plan to start!")
            return
        lines = ["Your recent trips:\n"]
        for r in rows:
            lines.append(f"- {r['destination']} | {r['dates']} | {r['members']} pax | {r['budget']} {r['currency'] or 'INR'}")
        await u.message.reply_text("\n".join(lines))

    async def c_save(self, u: Update, _):
        uid = str(u.effective_user.id)
        session = await get_session(uid)
        plan = session["data"].get("plan", "")
        dest = session["data"].get("destination", "")
        if not plan:
            await u.message.reply_text("No active plan. Use /plan to create one first.")
            return
        header = f"WanderOn Trip Plan — {dest}\n{'='*40}\n\n"
        for chunk in _split(header + plan):
            await u.message.reply_text(chunk)

    async def h_photo(self, u: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await self._rl(u):
            return
        if not self.planner.vision_ok():
            await u.message.reply_text(
                "Image recognition requires a vision-capable model.\n"
                "In Settings, switch to: Groq llama-3.2-vision, GPT-4o, Gemini, or Claude."
            )
            return
        photo = u.message.photo[-1]
        if photo.file_size and photo.file_size > MAX_IMG_BYTES:
            await u.message.reply_text("Image too large (max 5MB).")
            return
        await u.message.reply_text("Analysing your photo...")
        try:
            f = await ctx.bot.get_file(photo.file_id)
            raw = await f.download_as_bytearray()
            b64 = base64.b64encode(bytes(raw)).decode()
            caption = sanitize(u.message.caption or "", 300)
            result = await self.planner.describe_image(b64, "image/jpeg", caption)
            await u.message.reply_text(result)
            uid = str(u.effective_user.id)
            session = await get_session(uid)
            kb = [[InlineKeyboardButton("Plan a trip here!", callback_data="photo_plan")]]
            await u.message.reply_text("Want me to plan a trip to this place?", reply_markup=InlineKeyboardMarkup(kb))
            await set_session(uid, session["state"], {**session["data"], "photo_place": result[:100]})
        except Exception as e:
            log.error(f"photo err [{hash_uid(str(u.effective_user.id))}]: {e}")
            await u.message.reply_text("Could not process that image. Please try again.")

    async def h_msg(self, u: Update, _):
        if not await self._rl(u):
            return
        uid = str(u.effective_user.id)
        text = sanitize(u.message.text)
        if contains_sensitive_data(text):
            await u.message.reply_text(
                "Security notice: Please do not share card numbers, UPI IDs, bank details, or passwords here.\n"
                "I only need travel destinations and budget amounts."
            )
            return
        session = await get_session(uid)
        state = session["state"]
        data  = session["data"]

        if state == "idle":
            await u.message.reply_text("Type /plan to start planning, or /help for all commands.")

        elif state == STATES[DEST]:
            data["destination"] = text[:100]
            await set_session(uid, STATES[SOURCE], data)
            await u.message.reply_text(f"Great choice — {text}!\n\nWhere are you travelling from?\n(City, e.g. Mumbai, Delhi, Chennai, Bangalore)")

        elif state == STATES[SOURCE]:
            data["source"] = text[:100]
            await set_session(uid, STATES[DATES], data)
            await u.message.reply_text(
                "When are you travelling?\n\nExamples:\n"
                "- 15 Jan to 22 Jan\n- December 20 to 27\n- 5 days in March\n- Next weekend (3 days)"
            )

        elif state == STATES[DATES]:
            data["dates"] = text[:100]
            await set_session(uid, STATES[MEMBERS], data)
            kb = [[InlineKeyboardButton(str(n), callback_data=f"m{n}") for n in range(1,5)],
                  [InlineKeyboardButton(str(n), callback_data=f"m{n}") for n in range(5,9)]]
            await u.message.reply_text("How many people are travelling?", reply_markup=InlineKeyboardMarkup(kb))

        elif state == STATES[MEMBERS]:
            data["members"] = text[:10]
            await set_session(uid, STATES[BUDGET], data)
            await u.message.reply_text(
                "What is your total budget?\n\nExamples:\n- 50000 INR\n- 1000 USD\n- 200000 INR\n(Include currency if not INR)"
            )

        elif state == STATES[BUDGET]:
            await self._plan_and_send(u, uid, data, text)

        elif state == STATES[DONE]:
            plan = data.get("plan", "")
            if not plan:
                await u.message.reply_text("Type /plan to start a new trip.")
                return
            await u.message.reply_text("Looking that up for you...")
            try:
                ans = await self.planner.answer_followup(text, plan)
                for chunk in _split(ans):
                    await u.message.reply_text(chunk)
            except Exception as e:
                log.error(f"followup err: {e}")
                await u.message.reply_text("Sorry, could not answer that. Please try again.")

        elif state == "cost_dest":
            data["dest"] = text[:100]
            await set_session(uid, "cost_days", data)
            await u.message.reply_text(f"How many days are you planning for {text}?")

        elif state == "cost_days":
            data["days"] = text[:20]
            await set_session(uid, "cost_members", data)
            kb = [[InlineKeyboardButton(str(n), callback_data=f"cm{n}") for n in range(1,5)]]
            await u.message.reply_text("How many people?", reply_markup=InlineKeyboardMarkup(kb))

        elif state == "cost_members":
            data["members"] = text[:10]
            await self._send_cost(u, uid, data, text)

        elif state == "hotel_dest":
            data["hotel_dest"] = text[:100]
            await set_session(uid, "hotel_dates", data)
            await u.message.reply_text(f"When are you checking in to {text}?\nExample: 15 Jan to 20 Jan, or 5 nights in March")

        elif state == "hotel_dates":
            data["hotel_dates"] = text[:100]
            await set_session(uid, "hotel_budget", data)
            await u.message.reply_text("What is your per-night budget per room?\nExample: 3000 INR, 50 USD")

        elif state == "hotel_budget":
            await self._send_hotels(u, uid, data, text)

        elif state == "guide_dest":
            data["destination"] = text[:100]
            await set_session(uid, STATES[DONE], data)
            await u.message.reply_text(
                f"City Guide for {text}\nWhat would you like to know?",
                reply_markup=InlineKeyboardMarkup(GUIDE_MENU)
            )

    async def _plan_and_send(self, u, uid, data, budget_text):
        data["budget"] = budget_text[:50]
        currency = "INR"
        for c in ["USD","EUR","GBP","AUD","CAD","SGD","THB","JPY","AED","INR"]:
            if c.lower() in budget_text.lower():
                currency = c
                break
        budget_num = re.sub(r"[^\d]","",budget_text) or "0"
        members = int(re.sub(r"\D","",str(data.get("members","2"))) or 2)
        data["currency"] = currency

        await u.message.reply_text(
            f"Planning your trip to {data['destination']}...\n\n"
            "Fetching real hotel data from Booking.com, searching web for live info...\n"
            "This takes about 30-60 seconds. Please wait!"
        )
        try:
            plan, hotel_data = await self.planner.generate_plan(
                data["destination"], data.get("source",""), data["dates"],
                members, budget_num, currency
            )
            await save_trip(uid, data["destination"], data.get("source",""), data["dates"],
                members, budget_num, currency, plan[:200], plan)
            data["plan"] = plan
            await set_session(uid, STATES[DONE], data)

            kb = [[InlineKeyboardButton("New Trip",   callback_data="new_plan"),
                   InlineKeyboardButton("City Guide", callback_data="show_guide"),
                   InlineKeyboardButton("Save Plan",  callback_data="save_plan")]]
            chunks = _split(plan)
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    await u.message.reply_text(chunk, reply_markup=InlineKeyboardMarkup(kb))
                else:
                    await u.message.reply_text(chunk)
        except Exception as e:
            log.error(f"plan err [{hash_uid(uid)}]: {e}")
            await set_session(uid, STATES[IDLE], {})
            await u.message.reply_text(
                f"Something went wrong generating your plan.\n"
                f"Please check your API key in Settings and try /plan again.\n"
                f"Error: {str(e)[:120]}"
            )

    async def _send_cost(self, u, uid, data, members_text):
        members = int(re.sub(r"\D","",members_text) or 2)
        dest  = data.get("dest","")
        days  = int(re.sub(r"\D","",data.get("days","7")) or 7)
        await u.message.reply_text(f"Estimating costs for {dest}... searching web for live prices...")
        try:
            est = await self.planner.estimate_cost(dest, "", days, members)
            await set_session(uid, STATES[IDLE], {})
            for chunk in _split(est):
                await u.message.reply_text(chunk)
        except Exception as e:
            await u.message.reply_text(f"Error estimating costs: {str(e)[:100]}")

    async def _send_hotels(self, u, uid, data, budget_text):
        from search import fetch_hotels, booking_link
        from planner import _parse_dates, _format_hotels
        dest = data.get("hotel_dest","")
        dates_str = data.get("hotel_dates","")
        budget_num = int(re.sub(r"[^\d]","",budget_text) or 0)
        currency = "INR"
        for c in ["USD","EUR","GBP","AED","SGD","INR"]:
            if c.lower() in budget_text.lower():
                currency = c
                break
        check_in, check_out, nights = _parse_dates(dates_str)
        await u.message.reply_text(f"Searching real hotels in {dest}... fetching from Booking.com...")
        try:
            hotel_data = await fetch_hotels(
                dest, check_in, check_out, adults=2,
                total_budget=budget_num * (nights or 3),
                nights=nights, currency=currency,
                serpapi_key=self.planner.serpapi_key
            )
            section = _format_hotels(hotel_data, budget_num * (nights or 3), currency, dest)
            await set_session(uid, STATES[IDLE], {})
            for chunk in _split(section):
                await u.message.reply_text(chunk)
        except Exception as e:
            await u.message.reply_text(f"Error searching hotels: {str(e)[:100]}")

    async def cb(self, u: Update, ctx: ContextTypes.DEFAULT_TYPE):
        q = u.callback_query
        await q.answer()
        uid = str(q.from_user.id)
        d = q.data

        if d.startswith("m") and d[1:].isdigit():
            n = d[1:]
            session = await get_session(uid)
            if session["state"] == STATES[MEMBERS]:
                sdata = session["data"]
                sdata["members"] = n
                await set_session(uid, STATES[BUDGET], sdata)
                await q.message.reply_text(
                    f"{n} traveller{'s' if int(n)>1 else ''} confirmed!\n\n"
                    "What is your total budget?\nExamples: 50000 INR, 1000 USD"
                )

        elif d.startswith("cm") and d[2:].isdigit():
            n = d[2:]
            session = await get_session(uid)
            sdata = session["data"]
            sdata["members"] = n
            await self._send_cost(q.message, uid, sdata, n)

        elif d.startswith("guide_"):
            aspect = d.replace("guide_","")
            session = await get_session(uid)
            dest = session["data"].get("destination","")
            if not dest:
                await q.message.reply_text("Please run /plan first to set a destination.")
                return
            await q.message.reply_text(f"Getting {aspect} guide for {dest}... searching web...")
            try:
                result = await self.planner.city_guide(dest, aspect)
                for chunk in _split(result):
                    await q.message.reply_text(chunk)
            except Exception as e:
                await q.message.reply_text(f"Error: {str(e)[:100]}")

        elif d == "new_plan":
            await set_session(uid, STATES[DEST], {})
            await q.message.reply_text("Where do you want to go next?")

        elif d == "show_guide":
            session = await get_session(uid)
            dest = session["data"].get("destination","your destination")
            await q.message.reply_text(
                f"City Guide for {dest}\nWhat would you like to know?",
                reply_markup=InlineKeyboardMarkup(GUIDE_MENU)
            )

        elif d == "save_plan":
            session = await get_session(uid)
            plan = session["data"].get("plan","")
            dest = session["data"].get("destination","")
            if plan:
                header = f"WanderOn Trip Plan — {dest}\n{'='*40}\n\n"
                for chunk in _split(header + plan):
                    await q.message.reply_text(chunk)
            else:
                await q.message.reply_text("No plan to save. Use /plan first.")

        elif d == "photo_plan":
            session = await get_session(uid)
            place = session["data"].get("photo_place","")
            await set_session(uid, STATES[SOURCE], {"destination": place[:60]})
            await q.message.reply_text("Let's plan a trip there!\n\nWhere are you travelling from?")


def _split(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks
