# AllDebrid API plugin By Ryuk

import os

from app import bot
from app.core import Message
from app.utils.aiohttp_tools import SESSION
from app.utils.helpers import post_to_telegraph as post_tgh

# Your Alldbrid App token
KEY = os.environ.get("DEBRID_TOKEN")


TEMPLATE = """
<b>Name</b>: <i>{name}</i>
Status: <i>{status}</i>
ID: {id}
Size: {size}
{uptobox}"""


# Get response from api and return json or the error
async def get_json(endpoint: str, query: dict):
    if not KEY:
        return "API key not found."
    api = "https://api.alldebrid.com/v4" + endpoint
    params = {"agent": "bot", "apikey": KEY, **query}
    async with SESSION.get(url=api, params=params) as ses:
        try:
            json = await ses.json()
            return json
        except Exception as e:
            return str(e)


# Unlock Links or magnets
@bot.add_cmd("unrestrict")
async def debrid(bot: bot, message: Message):
    if not message.flt_input:
        return await message.reply("Give a magnet or link to unrestrict.")
    for i in message.text_list[1:]:
        link = i
        if link.startswith("http"):
            if "-save" not in message.flags:
                endpoint = "/link/unlock"
                query = {"link": link}
            else:
                endpoint = "/user/links/save"
                query = {"links[]": link}
        else:
            endpoint = "/magnet/upload"
            query = {"magnets[]": link}
        unrestrict = await get_json(endpoint=endpoint, query=query)
        if not isinstance(unrestrict, dict) or "error" in unrestrict:
            await message.reply(unrestrict, quote=True)
            continue
        if "-save" in message.flags:
            await message.reply("Link Successfully Saved.", quote=True)
            continue
        if not link.startswith("http"):
            data = unrestrict["data"]["magnets"][0]
        else:
            data = unrestrict["data"]
        name = data.get("filename", data.get("name", ""))
        id = data.get("id")
        size = round(int(data.get("size", data.get("filesize", 0))) / 1000000)
        ready = data.get("ready", "True")
        ret_str = (
            f"""Name: **{name}**\nID: `{id}`\nSize: **{size} mb**\nReady: __{ready}__"""
        )
        await message.reply(ret_str, quote=True)


# Get Status via id or Last 5 torrents
@bot.add_cmd("torrents")
async def torrents(bot: bot, message: Message):
    endpoint = "/magnet/status"
    query = {}

    if "-s" in message.flags and "-l" in message.flags:
        return await message.reply("can't use two flags at once", quote=True)

    if "-s" in message.flags:
        if not (input_ := message.flt_input):
            return await message.reply("ID required with -s flag", quote=True)
        query = {"id": input_}

    json = await get_json(endpoint=endpoint, query=query)

    if not isinstance(json, dict) or "error" in json:
        return await message.reply(json, quote=True)

    data = json["data"]["magnets"]

    if not isinstance(data, list):
        data = [data]

    ret_str_list = []
    limit = 1
    if "-l" in message.flags:
        limit = int(message.flt_input)

    for i in data[0:limit]:
        status = i.get("status")
        name = i.get("filename")
        id = i.get("id")
        downloaded = ""
        uptobox = ""
        if status == "Downloading":
            downloaded = f"""<i>{round(int(i.get("downloaded",0))/1000000)}</i>/"""
        size = f"""{downloaded}<i>{round(int(i.get("size",0))/1000000)}</i> mb"""
        if link := i.get("links"):
            uptobox = (
                "<i>UptoBox</i>: \n[ "
                + "\n".join(
                    [
                        f"""<a href={z.get("link","")}>{z.get("filename","")}</a>"""
                        for z in link
                    ]
                )
                + " ]"
            )
        ret_str_list.append(
            ret_val := TEMPLATE.format(
                name=name, status=status, id=id, size=size, uptobox=uptobox
            )
        )

    ret_str = "<br>".join(ret_str_list)
    if len(ret_str) < 4096:
        await message.reply(ret_str, quote=True)
    else:
        await message.reply(
            post_tgh("Magnets", ret_str.replace("\n", "<br>")),
            disable_web_page_preview=True,
            quote=True,
        )


# Delete a Magnet
@bot.add_cmd("del_t")
async def delete_torrent(bot: bot, message: Message):
    endpoint = "/magnet/delete"
    if not (id := message.flt_input):
        return await message.reply("Enter an ID to delete")
    for i in message.text_list[1:]:
        json = await get_json(endpoint=endpoint, query={"id": i})
        await message.reply(str(json), quote=True)
