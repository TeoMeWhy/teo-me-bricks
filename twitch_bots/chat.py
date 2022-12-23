import os
import sys

import dotenv
import pandas as pd
from twitchio.ext import commands

sys.path.insert(
    0,
    ".",
)

from db import db
from db import user


class Bot(commands.Bot):
    def __init__(self, token, channel, nick, db_url):
        super().__init__(token=token, prefix="!", initial_channels=[channel], nick=nick)
        self.db_url = db_url

    async def event_ready(self):
        txt = f"{self.nick} acabou de logar no canal {self.connected_channels[-1].name}"
        print(txt)
        print(f"Id do bot: {self.user_id}")

    @commands.command()
    async def email(self, ctx: commands.Context):

        user_data = {
            "descTwitchNick": ctx.author.name.lower(),
            "descUserEmail": ctx.message.raw_data.split(" ")[-1],
            "descGroup": "twitch",
        }

        con = db.connect(self.db_url)

        if user.user_exists(
            con=con, key_field="descUserEmail", value=user_data["descUserEmail"]
        ):
            await ctx.author.send(
                "Este email já tem acesso ao Databricks. Tente recuperar sua senha ou entre em contato o streamer."
            )
            return None

        query = f"SELECT * FROM tb_user WHERE descTwitchNick = '{user_data['descTwitchNick']}'"

        db_data = pd.read_sql_query(query, con)

        if db_data.shape[0] > 0:
            insert_data = db_data.iloc[0].to_dict()
            insert_data.update(user_data)

        else:
            insert_data = user_data

        user.update_user(con, user_data=insert_data, key_field="descTwitchNick")
        await ctx.author.send("Email atualizado com sucesso!")


def main():

    dotenv.load_dotenv(".env")

    bot = Bot(
        token=os.getenv("TWITCH_CHAT_TOKEN"),
        channel=os.getenv("TWITCH_CHANNEL"),
        nick=os.getenv("TWITCH_BOT_NICK"),
        db_url=os.getenv("DB_URL"),
    )
    bot.run()


if __name__ == "__main__":
    main()
