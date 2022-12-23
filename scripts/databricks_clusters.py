import os
import sys
import time
import dotenv

sys.path.append(".")

import dbricks.cluster as cluster
import db.db as db


def main():

    dotenv.load_dotenv(".env")

    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

    con = db.connect(os.getenv("DB_URL"))

    cluster_client = cluster.ClusterClient(host=DATABRICKS_HOST, token=DATABRICKS_TOKEN)

    cluster_integration = cluster.ClusterIntegraton(cluster_client, con)

    while True:

        cluster_integration.auto_hard_delete()
        cluster_integration.auto_on_off()
        time.sleep(60 * 2)


if __name__ == "__main__":
    main()
