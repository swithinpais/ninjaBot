from typing import Callable
from discord.ext import tasks
from data import data

import json
import aiohttp

class BotTasks():
    def __init__(self) -> None:
        return
    @tasks.loop(minutes=1)
    async def resetRateLimit(self):
        data.setHyRequestsMade(0)

    @tasks.loop(seconds=1800)
    async def get_json_file(self):
        async with aiohttp.ClientSession() as session:
                async with session.get("https://raw.githubusercontent.com/skyblockz/pricecheckbot/master/scammer.json") as r:
                    r = (await r.json())
                    with open("scammers.json", "w") as f:
                        json.dump(r, f)


    def get_all_tasks(self):
        return [func for func in dir(self) if callable(getattr(self, func)) and not func.startswith("__")]

    def start_all_tasks(self):
        method_list = self.get_all_tasks()
        for method in method_list:
            try:
                f:Callable = getattr(self, method)
                f.start()
            except Exception:
                pass
