import os
import sys

import dotenv
import requests
import time
import datetime

import sys

sys.path.insert(0, ".")

from db import db


def get_subs(app_token, app_client, broadcaster_id, **kwargs):
    url = f"https://api.twitch.tv/helix/subscriptions?broadcaster_id={broadcaster_id}&first=100"
    header = {"Authorization": f"Bearer {app_token}", "Client-Id": f"{app_client}"}
    res = requests.get(url, headers=header, params=kwargs)
    return res


def get_all_subs(app_token, app_client, broadcaster_id):

    data = []
    res = get_subs(app_token, app_client, broadcaster_id)

    d = res.json()

    while len(d["data"]) > 0:
        data.extend(d["data"])
        res = get_subs(
            app_token, app_client, broadcaster_id, after=d["pagination"]["cursor"]
        )
        d = res.json()

    return data


def update_subs(sub_list):
    con = db.connect(os.getenv("DB_URL"))
    nicks = ", ".join(f"'{i}'" for i in sub_list)
    query = f"UPDATE tb_user SET flTwitchSub=1 WHERE descTwitchNick IN ({nicks});"
    con.execute(query)
    return True


def update_non_subs(sub_list):
    con = db.connect(os.getenv("DB_URL"))
    nicks = ", ".join(f"'{i}'" for i in sub_list)
    query = f"UPDATE tb_user SET flTwitchSub=0 WHERE descTwitchNick NOT IN ({nicks});"
    con.execute(query)
    return True


def execute():

    dotenv.load_dotenv(".env")

    try:
        all_subs = get_all_subs(
            os.getenv("TWITCH_APP_TOKEN"),
            os.getenv("TWITCH_APP_CLIENT"),
            os.getenv("TWITCH_BROADCASTER_ID"),
        )

        sub_list = [i["user_name"].lower() for i in all_subs]

        update_subs(sub_list)
        update_non_subs(sub_list)
    except Exception as err:
        print(err)


def main():
    while True:

        print("\n=========================================")
        now = datetime.datetime.now()
        print(now)

        execute()
        time.sleep(60 * 5)


if __name__ == "__main__":
    main()
