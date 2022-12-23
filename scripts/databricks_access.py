import os

import dotenv
import time
import datetime

import sys

sys.path.insert(0, ".")

from db import db
import dbricks


def syncDB(user_integration: dbricks.user.UserIntegration):
    print("Atualizando tabela de usuários do Databricks...")
    user_integration.update_databricks_table()
    print("Ok.")

    print("\nDeletando usuários do Databricks...")
    user_integration.delete_users()
    print("Ok.")

    print("Atualizando tabela de usuários do Databricks...")
    user_integration.update_databricks_table()
    print("Ok.")


def main():

    dotenv.load_dotenv(".env")

    con = db.connect(os.getenv("DB_URL"))

    user_client = dbricks.user.UserClient(
        host=os.getenv("DATABRICKS_HOST"), token=os.getenv("DATABRICKS_TOKEN")
    )

    user_integration = dbricks.user.UserIntegration(user_client, con)

    while True:

        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute

        print("\n=========================================")
        print(now)

        if hour == 23 and 30 <= minute <= 40:
            syncDB(user_integration)

        print("\nCriando usuários no Databricks...")
        user_integration.create_users()
        print("Ok.")

        print("\nAtivando usuários inativos...")
        user_integration.activate_users()
        print("Ok.")

        print("\nDesativando usuários não Subs...")
        user_integration.deactivate_users()
        print("Ok.")

        print("\nAtualizando grupos...")
        user_integration.update_users()
        print("Ok.")

        time.sleep(60 * 5)


if __name__ == "__main__":
    main()
