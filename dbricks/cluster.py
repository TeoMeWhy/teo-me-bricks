import datetime
import argparse
import json
import os

import dotenv
import pandas as pd
import requests
import sqlalchemy
from tqdm import tqdm

__all__ = [
    "ClusterClient",
    "ClusterIntegraton",
]


class ClusterClient:
    def __init__(self, host: str, token: str):

        self.host = host
        self.token = token
        self.url = f"https://{host}/api/2.0/clusters/"
        self.header = {"Authorization": f"Bearer {token}"}

    def get(self, cluster_id):
        url = f"{self.url}get"
        data = {"cluster_id": cluster_id}
        resp = requests.get(url, headers=self.header, json=data)
        return resp

    def create(self, cluster_config):
        url = f"{self.url}create"
        resp = requests.post(url, headers=self.header, json=cluster_config)
        return resp

    def edit(self, cluster_id, cluster_config):
        url = f"{self.url}edit"
        cluster_config["cluster_id"] = cluster_id
        resp = requests.post(url, headers=self.header, json=cluster_config)
        return resp

    def start(self, cluster_id):
        url = f"{self.url}start"
        data = {"cluster_id": cluster_id}
        resp = requests.post(url, headers=self.header, json=data)
        return resp

    def delete(self, cluster_id):
        url = f"{self.url}delete"
        data = {"cluster_id": cluster_id}
        resp = requests.post(url, headers=self.header, json=data)
        return resp

    def hard_delete(self, cluster_id):
        url = f"{self.url}permanent-delete"
        data = {"cluster_id": cluster_id}
        resp = requests.post(url, headers=self.header, json=data)
        return resp

    def list(self):
        url = f"{self.url}/list"
        resp = requests.get(url, headers=self.header)
        return resp


class ClusterIntegraton:
    def __init__(self, cluster_client: ClusterClient, con: sqlalchemy.engine.Engine):
        self.cluster_client = cluster_client
        self.con = con

    def read_template(self, path):
        with open(path, "r") as open_file:
            template = json.load(open_file)
        return template

    def create_new_cluster(
        self,
        cluster_name: str,
        template_path: str,
    ):

        print("Criando cluster...")
        if self.cluster_exists(cluster_name):
            print(f"O cluster {cluster_name} já existe. Procure removê-lo.")
            return False

        config = self.read_template(template_path)
        config["cluster_name"] = config["cluster_name"].format(
            cluster_name=cluster_name
        )

        resp = self.cluster_client.create(config)
        data = resp.json()
        data["descClusterName"] = config["cluster_name"]
        data["idCluster"] = data["cluster_id"]
        del data["cluster_id"]

        df = pd.DataFrame([data])
        df.to_sql("tb_cluster", con=self.con, if_exists="append", index=False)

        print("Ok")
        return resp

    def edit_cluster(
        self,
        cluster_name: str,
        template_name: str,
    ):

        print("Editando cluster...")
        if not self.cluster_exists(cluster_name=cluster_name):
            print(f"O cluster {cluster_name} não já existe. Procure criá-lo.")
            return False

        config = self.read_template(template_name)
        config["cluster_name"] = config["cluster_name"].format(
            cluster_name=cluster_name
        )

        query = f"SELECT cluster_id FROM cluster WHERE cluster_name ='{cluster_name}'"
        cluster_id = self.con.execute(query).fetchall()[0][0]

        print("Ok.")
        resp = self.cluster_client.edit(cluster_id, config)
        return resp

    def cluster_exists(self, cluster_name: str):
        query = (
            f"SELECT COUNT(*) FROM tb_cluster WHERE descClusterName='{cluster_name}';"
        )
        value = self.con.execute(query).fetchall()[0][0]
        return value > 0

    def get_clusters_ids_databricks(self, ignore_jobs=True):
        data = self.cluster_client.list().json()

        if ignore_jobs:
            return [
                c["cluster_id"]
                for c in data["clusters"]
                if c["cluster_source"] != "JOB"
            ]
        else:
            return [c["cluster_id"] for c in data["clusters"]]

    def get_clusters_ids_db(self):
        query = "SELECT idCluster FROM tb_cluster"
        cluster_ids = pd.read_sql(query, self.con)["idCluster"].tolist()
        return cluster_ids

    def auto_hard_delete(self, ignore_jobs=True):
        cluster_ids_databricks = self.get_clusters_ids_databricks(
            ignore_jobs=ignore_jobs
        )
        cluster_ids_db = self.get_clusters_ids_db()

        to_exclude = list(set(cluster_ids_databricks) - set(cluster_ids_db))

        for c in tqdm(to_exclude):
            print(f"Deletando o cluster {c} ...")
            self.cluster_client.hard_delete(c)
            print("Ok")

    def on_off_cluster(self, cluster_id, start_on, stop_on):

        hour = datetime.datetime.now().hour

        if start_on < hour < stop_on:
            print(f"Ligando o cluster {cluster_id} ...")
            self.cluster_client.start(cluster_id)
            print("Ok.")
        else:
            print(f"Desligando o cluster {cluster_id} ...")
            self.cluster_client.delete(cluster_id)
            print("Ok.")

    def auto_on_off(self):
        query = "SELECT * FROM tb_cluster WHERE flAutoOnOff = 1"
        df = pd.read_sql(query, self.con)
        for i in df.index:
            line = df.iloc[i]
            self.on_off_cluster(line["idCluster"], line["vlStartOn"], line["vlStopOn"])
