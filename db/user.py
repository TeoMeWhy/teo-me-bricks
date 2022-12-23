import argparse
import os

import dotenv
import pandas as pd
from tqdm import tqdm
import sqlalchemy

import db

__all__ = [
    "create_user",
    "delete_user",
    "update_user",
    "user_exists",
]


def create_user(con: sqlalchemy.engine.Engine, user_data: dict):

    fields = ", ".join([i for i in user_data.keys()])
    placeholders = ", ".join(["?" for i in user_data.keys()])
    values = [user_data[i] for i in user_data.keys()]

    query = f"""INSERT INTO tb_user ({fields})
    VALUES ({placeholders});"""

    con.execute(query, values)

    return True


def delete_user(con: sqlalchemy.engine.Engine, key_field: str, value: str):
    query = f"DELETE FROM tb_user WHERE {key_field} = '{value}'"
    con.execute(query)
    return True


def update_user(con: sqlalchemy.engine.Engine, user_data: dict, key_field: str):
    delete_user(con, key_field, user_data[key_field])
    create_user(con, user_data)
    return True


def user_exists(con: sqlalchemy.engine.Engine, key_field: str, value: str):
    query = f"SELECT COUNT(*) FROM tb_user WHERE {key_field} = '{value}';"
    value = con.execute(query).fetchone()[0]
    return value > 0


def single_executer(con: sqlalchemy.engine.Engine, data: dict, op: str, key_field: str):

    if op in ("create", "update"):
        update_user(con, data, key_field)

    elif op == "delete":
        delete_user(con, key_field, data[key_field])

    return None


def batch_executer(
    con: sqlalchemy.engine.Engine, filepath: str, op: str, key_field: str
):

    df = pd.read_csv(filepath, sep=";")
    df = df.astype(str)

    for i in tqdm(df.index):
        data = df.iloc[i].to_dict()
        single_executer(con, data, op, key_field)

    return True


def main():

    dotenv.load_dotenv(".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--filepath", help="Nome do arquivo com os dados")
    parser.add_argument(
        "--op",
        help="Operação que será realizada",
        choices=["create", "delete", "update"],
    )
    parser.add_argument(
        "--keyfield",
        help="Campo chave para as alterações",
        choices=["descUserEmail", "descTwitchNick"],
    )
    args = parser.parse_args()

    con = db.connect(os.getenv("DB_URL"))

    batch_executer(con, args.filepath, args.op, args.keyfield)


if __name__ == "__main__":
    main()
