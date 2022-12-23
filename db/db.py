import argparse
import os

import dotenv
import pandas as pd
from tqdm import tqdm
import sqlalchemy

__all__ = [
    "connect",
]


def connect(url: str):

    try:
        return sqlalchemy.create_engine(url)

    except Exception as err:
        print(f"Deu ruim na conexão: {err}")
