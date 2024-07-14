# (c) @AbirHasan2005

import os
import asyncio
import traceback
from binascii import Error
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, FloodWait, QueryIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ChatType  # Updated import
from configs import Config
from handlers.database import db
from handlers.add_user_to_db import add_user_to_database
from handlers.send_file import send_media_and_reply
from handlers.helpers import b64_to_str, str_to_b64
from handlers.check_user_status import handle_user_status
from handlers.force_sub_handler import handle_force_sub, get_invite_link
from handlers.broadcast_handlers import main_broadcast_handler
from handlers.save_media import save_media_in_channel, save_batch_media_in_channel

MediaList = {}

Bot = Client(
    name=Config.BOT_USERNAME,
    in_memory=True,
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)


@Bot.on_message(filters.private)
async def _(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)


@Bot.on_message(filters.command("start") & filters.private)
async def start(bot: Client, cmd: Message):

    if cmd.from_user.id in Config.BANNED_USERS:
        await cmd.reply_text("Sorry, You are banned.")
        return
    if Config.UPDATES_CHANNEL is not None:
        back = await handle_force_sub(bot, cmd)
        if back == 400:
            return
    
    usr_cmd = cmd.text.split("_", 1)[-1]
    if usr_cmd == "/start":
        await add_user_to_database(bot, cmd)
        await cmd.reply_text(
            Config.HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Movie Group", url="https://t.me/+ZUyhAwBNBsU0YjA9"),
                        InlineKeyboardButton("Movie Channel", url="https://t.me/+QgSl55NlTiI0NDhl")
                    ],
                    [
                        InlineKeyboardButton("About Bot", callback_data="aboutbot"),
                        InlineKeyboardButton("About Dev", callback_data="aboutdevs")
                    ]
                ]
            )
        )
    else:
        try:
            try:
                file_id = int(b64_to_str(usr_cmd).split("_")[-1])
            except (Error, UnicodeDecodeError):
                file_id = int(usr_cmd.split("_")[-1])
            GetMessage = await bot.get_messages(chat_id=Config.DB_CHANNEL, message_ids=file_id)
            message_ids = []
            if GetMessage.text:
                message_ids = GetMessage.text.split(" ")
                _response_msg = await cmd.reply_text(
                    text=f"**Total Files:** `{len(message_ids)}`",
                    quote=True,
                    disable_web_page_preview=True
                )
            else:
                message_ids.append(int(GetMessage.id))
            for i in range(len(message_ids)):
                await send_media_and_reply(bot, user_id=cmd.from_user.id, file_id=int(message_ids[i]))
        except Exception as err:
            await cmd.reply_text(f"Something went wrong!\n\n**Error:** `{err}`")


@Bot.on_message((filters.document | filters.video | filters.audio) & ~filters.chat(Config.DB_CHANNEL))
async def main(bot: Client, message: Message):

    if message.chat.type == ChatType.PRIVATE:  # Use ChatType.PRIVATE

        await add_user_to_database(bot, message)

        if Config.UPDATES_CHANNEL is not None:
            back = await handle_force_sub(bot, message)
            if back == 400:
                return

        if message.from_user.id in Config.BANNED_USERS:
            await message.reply_text("Sorry, You are banned!\n\nContact [Owner](https://t.me/GamerBhai02)",
                                     disable_web_page_preview=True)
            return

        if Config.OTHER_USERS_CAN_SAVE_FILE is False:
            return

        await message.reply_text(
            text="**Choose an option from below:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Save in Batch", callback_data="addToBatchTrue")],
                [InlineKeyboardButton("Get Sharable Link", callback_data="addToBatchFalse")]
            ]),
            quote=True,
            disable_web_page_preview=True
        )
    elif message.chat.type == ChatType.CHANNEL:  # Use ChatType.CHANNEL
        if (message.chat.id == int(Config.LOG_CHANNEL)) or (message.chat.id == int(Config.UPDATES_CHANNEL)) or message.forward_from_chat or message.forward_from:
            return
        elif int(message.chat.id) in Config.BANNED_CHAT_IDS:
            await bot.leave_chat(message.chat.id)
            return
        else:
            pass

        try:
            forwarded_msg = await message.forward(Config.DB_CHANNEL)
            file_er_id = str(forwarded_msg.id)
            share_link = f"https://t.me/{Config.BOT_USERNAME}?start=AbirHasan2005_{str_to_b64(file_er_id)}"
            CH_edit = await bot.edit_message_reply_markup(message.chat.id, message.id,
                                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                                              "Get Sharable Link", url=share_link)]]))
            if message.chat.username:
                await forwarded_msg.reply_text(
                    f"#CHANNEL_BUTTON:\n\n[{message.chat.title}](https://t.me/{message.chat.username}/{CH_edit.id}) Channel's Broadcasted File's Button Added!")
            else:
                private_ch = str(message.chat.id)[4:]
                await forwarded_msg.reply_text(
                    f"#CHANNEL_BUTTON:\n\n[{message.chat.title}](https://t.me/c/{private_ch}/{CH_edit.id}) Channel's Broadcasted File's Button Added!")
        except FloodWait as sl:
            await asyncio.sleep(sl.value)
            await bot.send_message(
                chat_id=int(Config.LOG_CHANNEL),
                text=f"#FloodWait:\nGot FloodWait of `{str(sl.value)}s` from `{str(message.chat.id)}` !!",
                disable_web_page_preview=True
            )
        except Exception as err:
            await bot.leave_chat(message.chat.id)
            await bot.send_message(
                chat_id=int(Config.LOG_CHANNEL),
                text=f"#ERROR_TRACEBACK:\nGot Error from `{str(message.chat.id)}` !!\n\n**Traceback:** `{err}`",
                disable_web_page_preview=True
            )


@Bot.on_callback_query()
async def button(bot: Client, cmd: CallbackQuery):
    cb_data = cmd.data
    if "aboutbot" in cb_data:
        await cmd.message.edit(
            text=Config.ABOUT_BOT_TEXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Source Code", url="https://github.com/AbirHasan2005/PyroFilesStoreBot")], [InlineKeyboardButton("Go Back", callback_data="goback")]])
        )
    elif "aboutdevs" in cb_data:
        await cmd.message.edit(
            text=Config.ABOUT_DEV_TEXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Source Code", url="https://github.com/AbirHasan2005/PyroFilesStoreBot")], [InlineKeyboardButton("Go Back", callback_data="goback")]])
        )
    elif "goback" in cb_data:
        await cmd.message.edit(
            text=Config.HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Movie Group", url="https://t.me/+ZUyhAwBNBsU0YjA9"),
                        InlineKeyboardButton("Movie Channel", url="https://t.me/+QgSl55NlTiI0NDhl")
                    ],
                    [
                        InlineKeyboardButton("About Bot", callback_data="aboutbot"),
                        InlineKeyboardButton("About Dev", callback_data="aboutdevs")
                    ]
                ]
            )
        )
    elif "refreshmeh" in cb_data:
        if Config.UPDATES_CHANNEL:
            if Config.UPDATES_CHANNEL.startswith("-100"):
                channel_chat_id = int(Config.UPDATES_CHANNEL)
            else:
                channel_chat_id = Config.UPDATES_CHANNEL
            try:
                user = await bot.get_chat_member(channel_chat_id, cmd.message.chat.id)
                if user.status == "kicked":
                    await cmd.message.edit(
                        text="Sorry Sir, You are Banned to use me. Contact my [Support Group](https://t.me/linux_repo).",
                        disable_web_page_preview=True
                    )
                    return
            except UserNotParticipant:
                invite_link = await get_invite_link(channel_chat_id)
                await cmd.message.edit(
                    text="**You still didn't join my Updates Channel Sir, Please Join to get my services.**\n\n"
                         "Due to Overload, Only Channel Subscribers can use the Bot!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🤖 Join Updates Channel", url=invite_link.invite_link)
                            ],
                            [
                                InlineKeyboardButton("🔄 Refresh / Try Again",
                                                     url=f"https://t.me/{Config.BOT_USERNAME}?start=AbirHasan2005")
                            ]
                        ]
                    ),
                    disable_web_page_preview=True
                )
                return
            except Exception:
                await cmd.message.edit(
                    text="Something went Wrong. Contact my [Support Group](https://t.me/linux_repo).",
                    disable_web_page_preview=True
                )
                return
            await cmd.message.edit(
                text=Config.HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("Movie Group", url="https://t.me/+ZUyhAwBNBsU0YjA9"),
                            InlineKeyboardButton("Movie Channel", url="https://t.me/+QgSl55NlTiI0NDhl")
                        ],
                        [
                            InlineKeyboardButton("About Bot", callback_data="aboutbot"),
                            InlineKeyboardButton("About Dev", callback_data="aboutdevs")
                        ]
                    ]
                )
            )
    elif "addToBatchTrue" in cb_data:
        message_id = cmd.message.reply_to_message.message_id
        user_id = cmd.from_user.id
        if user_id in MediaList:
            MediaList[user_id].append(message_id)
        else:
            MediaList[user_id] = [message_id]
        await cmd.message.edit("File Saved in Batch!\n\nUse /done to get batch link!")
    elif "addToBatchFalse" in cb_data:
        await save_media_in_channel(bot, cmd, MediaList)


@Bot.on_message(filters.private & filters.command("broadcast") & filters.user(Config.BOT_OWNER) & filters.reply)
async def broadcast_handler_open(_, m: Message):
    await main_broadcast_handler(m, db)


@Bot.on_message(filters.private & filters.command("status") & filters.user(Config.BOT_OWNER))
async def sts(_, m: Message):
    total_users = await db.total_users_count()
    await m.reply_text(
        text=f"**Total Users in DB:** `{total_users}`",
        quote=True
    )


@Bot.on_message(filters.private & filters.command("ban_user") & filters.user(Config.BOT_OWNER))
async def ban(c: Client, m: Message):
    
    if len(m.command) == 1:
        await m.reply_text(
            f"Use this command to ban any user from the bot.\n\n"
            f"Usage:\n\n"
            f"`/ban_user user_id ban_duration ban_reason`\n\n"
            f"Eg: `/ban_user 1234567 28 You misused me.`\n"
            f"This will ban user with id `1234567` for `28` days for the reason `You misused me`.",
            quote=True
        )
        return

    try:
        user_id = int(m.command[1])
        ban_duration = int(m.command[2])
        ban_reason = ' '.join(m.command[3:])
        ban_log_text = f"Banning user {user_id} for {ban_duration} days for the reason {ban_reason}."
        try:
            await c.send_message(
                user_id,
                f"You are banned to use this bot for **{ban_duration}** day(s) for the reason __{ban_reason}__ \n\n"
                f"**Message from the admin**"
            )
            ban_log_text += '\n\nUser notified successfully!'
        except:
            traceback.print_exc()
            ban_log_text += f"\n\nUser notification failed! \n\n`{traceback.format_exc()}`"

        await db.ban_user(user_id, ban_duration, ban_reason)
        print(ban_log_text)
        await m.reply_text(
            ban_log_text,
            quote=True
        )
    except:
        traceback.print_exc()
        await m.reply_text(
            f"An error occurred while banning the user.\n\n`{traceback.format_exc()}`",
            quote=True
        )


@Bot.on_message(filters.private & filters.command("unban_user") & filters.user(Config.BOT_OWNER))
async def unban(c: Client, m: Message):
    
    if len(m.command) != 2:
        await m.reply_text(
            f"Use this command to unban any user.\n\n"
            f"Usage:\n\n"
            f"`/unban_user user_id`\n\n"
            f"Eg: `/unban_user 1234567`.\n"
            f"This will unban user with id `1234567`.",
            quote=True
        )
        return

    try:
        user_id = int(m.command[1])
        ban_log_text = f"Unbanning user {user_id}."
        try:
            await c.send_message(
                user_id,
                f"Your ban was lifted!\n\n"
                f"**Message from the admin**"
            )
            ban_log_text += '\n\nUser notified successfully!'
        except:
            traceback.print_exc()
            ban_log_text += f"\n\nUser notification failed! \n\n`{traceback.format_exc()}`"

        await db.remove_ban(user_id)
        print(ban_log_text)
        await m.reply_text(
            ban_log_text,
            quote=True
        )
    except:
        traceback.print_exc()
        await m.reply_text(
            f"An error occurred while unbanning the user.\n\n`{traceback.format_exc()}`",
            quote=True
        )


@Bot.on_message(filters.private & filters.command("banned_users") & filters.user(Config.BOT_OWNER))
async def _banned_usrs(_, m: Message):
    all_banned_users = await db.get_all_banned_users()
    banned_usr_str = ""
    async for banned_user in all_banned_users:
        banned_usr_str += f"**UserID:** `{banned_user['id']}`\n**Ban Duration:** `{banned_user['ban_status']['ban_duration']}`\n**Ban Reason:** `{banned_user['ban_status']['ban_reason']}`\n\n"
    await m.reply_text(
        f"**Total Banned Users:** `{await db.total_banned_users_count()}`\n\n{banned_usr_str}",
        quote=True
    )


@Bot.on_message(filters.private & filters.command("total_users") & filters.user(Config.BOT_OWNER))
async def get_stats(_, m: Message):
    total_users = await db.total_users_count()
    await m.reply_text(f"Total users: {total_users}", quote=True)


@Bot.on_message(filters.private & filters.command("done"))
async def done(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in MediaList:
        await message.reply_text("No media to process.", quote=True)
        return

    await save_batch_media_in_channel(bot, message, MediaList)


@Bot.on_message(filters.private & filters.command("cancel"))
async def cancel(_, message: Message):
    user_id = message.from_user.id
    if user_id in MediaList:
        del MediaList[user_id]
        await message.reply_text("Cancelled batch media processing.", quote=True)
    else:
        await message.reply_text("No batch media to cancel.", quote=True)


@Bot.on_message(filters.command("batch") & filters.private)
async def batch(_, message: Message):
    user_id = message.from_user.id
    if user_id in MediaList:
        await message.reply_text(f"Current batch: {MediaList[user_id]}", quote=True)
    else:
        await message.reply_text("No media in batch.", quote=True)


@Bot.on_message(filters.private & filters.command("help"))
async def help_handler(_, m: Message):
    await m.reply_text(
        Config.HELP_TEXT,
        quote=True,
        disable_web_page_preview=True
    )


Bot.run()
