import io
import json
import logging
from datetime import datetime
import os
from telegram import __version__ as TG_VER
from mesa import auto_parse, now, Time, Object, Weather
from astropy.coordinates.name_resolve import NameResolveError
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from peewee import Model, SqliteDatabase, CharField, DateField, DateTimeField, TextField

db = SqliteDatabase('requests.db')


class Request(Model):
    created_on = DateTimeField()
    created_by = CharField()
    operation = CharField()
    inputs = TextField()
    output = TextField()

    class Meta:
        database = db


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

START, JD_ASK, SIDEREAL_TIME_ASK, SIDEREAL_LOCATION_ASK, TWILIGHT_TIME_ASK, TWILIGHT_LOCATION_ASK, MOON_TIME_ASK, \
    MOON_LOCATION_ASK, RISESET_TIME_ASK, RISESET_LOCATION_ASK, RISESET_OBJECT_ASK, E2H_TIME_ASK, E2H_LOCATION_ASK, \
    E2H_OBJECT_ASK, VIS_TIME_ASK, VIS_LOCATION_ASK, VIS_OBJECT_ASK, WEATHER_LOCATION_ASK = range(18)

reply_keyboard = [
    ["JD", "Sidereal", "Twilight", "Moon", "Rise/Set"],
    ["Equatorial to Horizontal", "Visibility"],
    ["Weather"],
    ["Done"],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def saver(update, operation, inputs, output):
    record = Request(
        created_on=datetime.utcnow(),
        created_by=update.message.from_user['id'],
        operation=operation,
        inputs=inputs,
        output=output
    )
    record.save()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for input."""
    await update.message.reply_text(
        "Hi! It is Mesa. How can I help you?",
        reply_markup=markup,
    )

    return START


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Give me a location (Latitude ,Longitude): You can share your `location`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return WEATHER_LOCATION_ASK


async def weather_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            latitude, longitude = map(float, update.message.text.split())
            wthr = Weather()
            wthr_data = wthr.get(longitude, latitude)
            await update.message.reply_text(
                f"{wthr_data['description'].title()}\n"
                f"*Temperature:* {wthr_data['temp']} °C\n"
                f"*Dew Point:* {wthr_data['dew']} °C\n"
                f"*Pressure*: {wthr_data['pressure']} hPa\n"
                f"*Humidity*: {wthr_data['humidity']} %\n"
                f"*Wind:*\n"
                f" - Speed: {wthr_data['wind']['speed']} m/s\n"
                f" - Direction: {wthr_data['wind']['deg']} °\n",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            saver(update, "Weather",
                  json.dumps({"latitude": latitude, "longitude": longitude}),
                  f"{json.dumps(wthr_data)}")
            return ConversationHandler.END
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return WEATHER_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        wthr = Weather()
        wthr_data = wthr.get(longitude, latitude)
        await update.message.reply_text(
            f"{wthr_data['description'].title()}\n"
            f"*Temperature*: {wthr_data['temp']} °C\n"
            f"*Dew Point*: {wthr_data['dew']} °C\n"
            f"*Pressure*: {wthr_data['pressure']} hPa\n"
            f"*Humidity*: {wthr_data['humidity']} %\n"
            f"*Wind:*\n"
            f" - Speed: {wthr_data['wind']['speed']} m/s\n"
            f" - Direction: {wthr_data['wind']['deg']} °\n",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )

        saver(update, "Weather",
              json.dumps({"latitude": latitude, "longitude": longitude}),
              f"{json.dumps(wthr_data)}")
        return ConversationHandler.END


async def visibility(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return VIS_TIME_ASK


async def visibility_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return VIS_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return VIS_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return VIS_TIME_ASK


async def visibility_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        try:
            if update.message.text.lower() == "cancel":
                await update.message.reply_html(
                    f"Canceled",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return ConversationHandler.END
            latitude, longitude = map(float, update.message.text.split())
            context.user_data["loc"] = [latitude, longitude]
            await update.message.reply_text(
                "Now give me a coordinate (Ra ,Dec) or name of an object\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return VIS_OBJECT_ASK
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return VIS_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        context.user_data["loc"] = [latitude, longitude]
        await update.message.reply_text(
            "Now give me a coordinate (Ra ,Dec) or name of an object\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return VIS_OBJECT_ASK


async def visibility_get_sky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    coords = [each.strip() for each in update.message.text.split("\n")]
    skys = []
    for coord in coords:
        try:
            skys.append([coord.strip(), Object.from_name(coord.strip())])
        except NameResolveError:
            try:
                ra, dec = map(float, coord.strip().split())
                skys.append(["Coord", Object(ra, dec)])
            except:
                pass

    plt.title("MYRaf Object Visibility")
    for obj in skys:
        data = obj[1].visibility(context.user_data["tm"], *context.user_data["loc"], 0)
        if obj[0] == "Coord":
            label = f"Coord {obj[1].ra} {obj[1].dec}"
        else:
            label = obj[0]
        plt.plot(data[0], data[1], label=label)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.xticks(rotation=45)
    plt.xlabel("Time (UTC)")
    plt.ylabel("Altitude (°)")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    saver(update, "Visibility",
          json.dumps({"time": str(context.user_data['tm'].dt), "lat": context.user_data['loc'][0],
                      "lon": context.user_data['loc'][1],
                      "ra": obj[1].ra, "dec": obj[1].dec}),
          f"Image")
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf.read())
    return ConversationHandler.END


async def e2h(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return E2H_TIME_ASK


async def e2h_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return E2H_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return E2H_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return E2H_TIME_ASK


async def e2h_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            latitude, longitude = map(float, update.message.text.split())
            context.user_data["loc"] = [latitude, longitude]
            await update.message.reply_text(
                "Now give me a coordinate (Ra ,Dec) or name of an object\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return E2H_OBJECT_ASK
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return E2H_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        context.user_data["loc"] = [latitude, longitude]
        await update.message.reply_text(
            "Now give me a coordinate (Ra ,Dec) or name of an object\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return E2H_OBJECT_ASK


async def e2h_get_sky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    try:
        sky = Object.from_name(update.message.text.strip())
        rs = sky.eq2hor(context.user_data["tm"], *context.user_data["loc"], 0)
        await update.message.reply_html(
            f"<b>Alt:</b> <pre>{rs['alt']}</pre>\n"
            f"<b>Az:</b> <pre>{rs['az']}</pre>\n",
            reply_markup=ReplyKeyboardRemove(),
        )
        saver(update, "E2H",
              json.dumps({"time": str(context.user_data['tm'].dt), "lat": context.user_data['loc'][0],
                          "lon": context.user_data['loc'][1]}),
              f"{json.dumps(rs)}")

        return ConversationHandler.END
    except NameResolveError:
        try:
            ra, dec = map(float, update.message.text.strip().split())
            sky = Object(ra, dec)
            rs = sky.eq2hor(context.user_data["tm"], *context.user_data["loc"], 0)
            await update.message.reply_html(
                f"<b>Alt:</b> <pre>{rs['alt']}</pre>\n"
                f"<b>Az:</b> <pre>{rs['az']}</pre>\n",
                reply_markup=ReplyKeyboardRemove(),
            )

            saver(update, "E2H",
                  json.dumps({"time": str(context.user_data['tm'].dt), "lat": context.user_data['loc'][0],
                              "lon": context.user_data['loc'][1]}),
                  f"{json.dumps(rs)}")

            return ConversationHandler.END
        except:
            await update.message.reply_text(
                f"Cannot pars coordinates.\n"
                "Please provide two floats (Ra ,Dec) or name of an object\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return RISESET_OBJECT_ASK


async def rise_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return RISESET_TIME_ASK


async def rise_set_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return RISESET_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return RISESET_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return RISESET_TIME_ASK


async def rise_set_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            latitude, longitude = map(float, update.message.text.split())
            context.user_data["loc"] = [latitude, longitude]
            await update.message.reply_text(
                "Now give me a coordinate (Ra ,Dec) or name of an object\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return RISESET_OBJECT_ASK
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return RISESET_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        context.user_data["loc"] = [latitude, longitude]
        await update.message.reply_text(
            "Now give me a coordinate (Ra ,Dec) or name of an object\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return RISESET_OBJECT_ASK


async def rise_set_get_sky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    try:
        sky = Object.from_name(update.message.text.strip())
        rs = sky.rise_set(context.user_data["tm"], *context.user_data["loc"], 0)
        await update.message.reply_html(
            f"<b>Rise:</b> <pre>{rs['rise']}</pre>\n"
            f"<b>Set:</b> <pre>{rs['set']}</pre>\n",
            reply_markup=ReplyKeyboardRemove(),
        )

        saver(update, "Object",
              json.dumps({"time": str(context.user_data['tm'].dt), "lat": context.user_data['loc'][0],
                          "lon": context.user_data['loc'][1]}),
              f"{json.dumps(rs)}")

        return ConversationHandler.END
    except NameResolveError:
        try:
            ra, dec = map(float, update.message.text.strip().split())
            sky = Object(ra, dec)
            rs = sky.rise_set(context.user_data["tm"], *context.user_data["loc"], 0)
            await update.message.reply_html(
                f"<b>Rise:</b> <pre>{rs['rise']}</pre>\n"
                f"<b>Set:</b> <pre>{rs['set']}</pre>\n",
                reply_markup=ReplyKeyboardRemove(),
            )

            saver(update, "Object",
                  json.dumps({"time": str(context.user_data['tm'].dt), "lat": context.user_data['loc'][0],
                              "lon": context.user_data['loc'][1]}),
                  f"{json.dumps(rs)}")

            return ConversationHandler.END
        except:
            await update.message.reply_text(
                f"Cannot pars coordinates.\n"
                "Please provide two floats (Ra ,Dec) or name of an object\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return RISESET_OBJECT_ASK


async def moon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return MOON_TIME_ASK


async def moon_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return MOON_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return MOON_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return MOON_TIME_ASK


async def moon_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            latitude, longitude = map(float, update.message.text.split())
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return SIDEREAL_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude

    mn = context.user_data["tm"].moon(longitude, latitude, 0)

    await update.message.reply_html(
        f"<b>Rise:</b> <pre>{mn['rise']}</pre>\n"
        f"<b>Set:</b> <pre>{mn['set']}</pre>\n"
        f"<b>Phase:</b> <pre>{mn['phase']}</pre>",
        reply_markup=ReplyKeyboardRemove(),
    )

    saver(update, "Moon",
          json.dumps({"time": str(context.user_data['tm'].dt), "lat": latitude, "lon": longitude}),
          f"{json.dumps(mn)}")

    return ConversationHandler.END


async def twilight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return TWILIGHT_TIME_ASK


async def twilight_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return TWILIGHT_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me a location (Latitude ,Longitude): You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return TWILIGHT_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return TWILIGHT_TIME_ASK


async def twilight_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            latitude, longitude = map(float, update.message.text.split())
        except:
            await update.message.reply_text(
                f"Cannot pars location.\n"
                "Please provide two floats (Latitude ,Longitude) or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return SIDEREAL_LOCATION_ASK
    else:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude

    tw = context.user_data["tm"].twilight(longitude, latitude, 0)

    await update.message.reply_html(
        f"<pre>Morning: {tw['morning']}</pre>\n"
        f"<pre>Evening: {tw['evening']}</pre>",
        reply_markup=ReplyKeyboardRemove(),
    )

    saver(update, "Twilight",
          json.dumps({"time": str(context.user_data['tm'].dt), "lat": latitude, "lon": longitude}),
          f"{json.dumps(tw)}")

    return ConversationHandler.END


async def sidereal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "First give me datetime: You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return SIDEREAL_TIME_ASK


async def sidereal_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        context.user_data["tm"] = tm
        await update.message.reply_text(
            "Now give me longitude: You can share your `location`\n"
            "write cancel to cancel",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
        return SIDEREAL_LOCATION_ASK

    else:
        try:
            tm = Time(auto_parse(text))
            context.user_data["tm"] = tm

            await update.message.reply_text(
                "Now give me longitude: You can share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return SIDEREAL_LOCATION_ASK

        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return SIDEREAL_TIME_ASK


async def sidereal_get_location_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location is None:
        if update.message.text.lower() == "cancel":
            await update.message.reply_html(
                f"Canceled",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        try:
            longitude = float(update.message.text)
        except:
            await update.message.reply_text(
                f"Cannot pars longitude.\n"
                "Please provide a float or share your `location`\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
            return SIDEREAL_LOCATION_ASK
    else:
        longitude = update.message.location.longitude

    sr = context.user_data["tm"].sidereal(longitude)

    await update.message.reply_html(
        f"<pre>{sr}</pre>",
        reply_markup=ReplyKeyboardRemove(),
    )

    saver(update, "Sidereal",
          json.dumps({"time": str(context.user_data['tm'].dt), "lon": longitude}),
          f"{json.dumps(sr)}")

    return ConversationHandler.END


async def jd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"I'll need a datetime value. You can write `now`\n"
        "write cancel to cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown"
    )
    return JD_ASK


async def jd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text.lower() == "cancel":
        await update.message.reply_html(
            f"Canceled",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if text.lower().strip() == "now":
        tm = Time(now())
        jd = tm.jd()

        await update.message.reply_html(
            f"<b>JD:</b> <pre>{round(jd['jd'], 10)}</pre>\n"
            f"<b>MJD:</b> <pre>{round(jd['mjd'], 10)}</pre>",
            # f"<pre>{tabulate(data, tablefmt='simple_grid', floatfmt=('.10f', '.10f'))}</pre>",
            reply_markup=ReplyKeyboardRemove(),
        )

        saver(update, "JD",
              json.dumps({"time": str(tm.dt)}),
              f"{json.dumps(jd)}")

        return ConversationHandler.END
    else:
        try:
            tm = Time(auto_parse(text))
            jd = tm.jd()

            await update.message.reply_html(
                f"<b>JD:</b> <pre>{round(jd['jd'], 10)}</pre>\n"
                f"<b>MJD:</b> <pre>{round(jd['mjd'], 10)}</pre>",
                reply_markup=ReplyKeyboardRemove(),
            )

            saver(update, "JD",
                  json.dumps({"time": str(tm.dt)}),
                  f"{json.dumps(jd)}")

            return ConversationHandler.END
        except ValueError:
            await update.message.reply_text(
                f"Cannot pars datetime.\n"
                "I'll need a datetime value. You can write `now`.\n"
                "write cancel to cancel",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="markdown"
            )
    return JD_ASK


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""
    user_data = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    await update.message.reply_text(
        f"See ya...",
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(os.environ['TELEGRAMAPI']).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("jd", jd),
            CommandHandler("sidereal", sidereal),
            CommandHandler("twilight", twilight),
            CommandHandler("moon", moon),
            CommandHandler("object", rise_set),
            CommandHandler("equatorial", e2h),
            CommandHandler("visibility", visibility),
            CommandHandler("weather", weather),

        ],
        states={
            START: [
                MessageHandler(
                    filters.Regex("JD"), jd
                ),
                MessageHandler(
                    filters.Regex("Sidereal"), sidereal
                ),
                MessageHandler(
                    filters.Regex("Twilight"), twilight
                ),
                MessageHandler(
                    filters.Regex("Moon"), moon
                ),
                MessageHandler(
                    filters.Regex("Rise/Set"), rise_set
                ),
                MessageHandler(
                    filters.Regex("Equatorial to Horizontal"), e2h
                ),
                MessageHandler(
                    filters.Regex("Visibility"), visibility
                ),
                MessageHandler(
                    filters.Regex("Weather"), weather
                )
            ],
            JD_ASK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    jd_calc,
                )
            ],
            SIDEREAL_TIME_ASK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    sidereal_calc,
                )
            ],
            SIDEREAL_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    sidereal_get_location_calc,
                )
            ],
            TWILIGHT_TIME_ASK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    twilight_get_time,
                )
            ],
            TWILIGHT_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    twilight_get_location,
                )
            ],
            MOON_TIME_ASK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    moon_get_time,
                )
            ],
            MOON_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    moon_get_location,
                )
            ],
            RISESET_TIME_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    rise_set_get_time,
                )
            ],
            RISESET_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    rise_set_get_location,
                )
            ],
            RISESET_OBJECT_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    rise_set_get_sky,
                )
            ],
            E2H_TIME_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    e2h_get_time,
                )
            ],
            E2H_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    e2h_get_location,
                )
            ],
            E2H_OBJECT_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    e2h_get_sky,
                )
            ],

            #

            VIS_TIME_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    visibility_get_time,
                )
            ],
            VIS_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    visibility_get_location,
                )
            ],
            VIS_OBJECT_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    visibility_get_sky,
                )
            ],
            WEATHER_LOCATION_ASK: [
                MessageHandler(
                    filters.TEXT | filters.LOCATION & ~filters.COMMAND,
                    weather_get_location,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    with db:
        db.create_tables([Request])
    main()
