import sys

import pandas as pd
import requests
import sqlalchemy
from tqdm import tqdm

sys.path.insert(0, '../')

from db import user as db_user

__all__ = [
    "UserClient",
    "UserIntegration"
]


class UserClient:
    def __init__(self, host, token) -> None:

        self.host = host
        self.token = token
        self.url = f"https://{host}/api/2.0/preview/scim/v2/Users"
        self.header = {"Authorization": f"Bearer {token}"}

    def create_user(self, user_email, groups=[]):

        groups = [{"value": str(i)} for i in groups]

        data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": user_email,
            "groups": groups,
            "entitlements": [],
        }

        resp = requests.post(self.url, json=data, headers=self.header)
        return resp

    def update_user(self, user_id, user_name, groups=[]):

        url = self.url + f"/{user_id}"

        groups = [{"value": str(i)} for i in groups]

        data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": user_name,
            "groups": groups,
            "entitlements": [],
        }

        resp = requests.put(url, json=data, headers=self.header)
        return resp


    def get_user(self, user_id):
        url = self.url + f"/{user_id}"
        resp = requests.get(url, headers=self.header)
        return resp

    def delete_user(self, user_id):
        url = self.url + f"/{user_id}"
        resp = requests.delete(url, headers=self.header)
        return resp

    def deactivate_user(self, user_id):
        url = self.url + f"/{user_id}"
        data = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "path": "active", "value": [{"value": "false"}]}
            ],
        }
        resp = requests.patch(url, json=data, headers=self.header)
        return resp

    def activate_user(self, user_id):
        url = self.url + f"/{user_id}"
        data = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "path": "active", "value": [{"value": "true"}]}
            ],
        }
        resp = requests.patch(url, json=data, headers=self.header)
        return resp

    def get_users(self, **kwargs):
        resp = requests.get(self.url, params=kwargs, headers=self.header)
        return resp

class UserIntegration:

    def __init__(self, user_client:UserClient, con:sqlalchemy.engine.Engine) -> None:
        self.user_client = user_client
        self.con = con

    def format_user_data(self, user_data):
        columns = [
            "descUserEmail", 
            "descTwitchNick", 
            "flTwitchSub", 
            "descGroup", 
            "descDatabricksStatus", 
            "idDatabricks",
        ]

        user_data = {k:user_data[k] for k in columns}
        return user_data

    def get_all_databricks_users(self):
        full_data = []
        startIndex = 1
        count = 100
        while True:
            
            try:
                resp = self.user_client.get_users(startIndex=startIndex, count=count)
                data = resp.json()
                
                if len(data['Resources']) == 0:
                    break

                startIndex += count
                full_data.extend(data['Resources'])
            except KeyError as err:
                return full_data, resp

        return full_data, resp

    def create_user(self, user_data: dict):
        email = user_data["descUserEmail"]
        group = user_data["idGroup"]

        resp = self.user_api.create_user(user_email=email, groups=[group])
        data = resp.json()

        try:
            user_data["descDatabricksStatus"] = int(data["active"])
            user_data["idDatabricks"] = data['id']

            user_data = self.format_user_data(user_data)
            db_user.update_user(self.con, user_data, "descUserEmail")
            return data
        
        except KeyError:
            print("Usuário já existe, procure ativá-lo")
            return data


    def create_users(self):
        query = '''
        SELECT *
        FROM tb_user AS t1

        LEFT JOIN tb_group AS t2
        on t2.descGroup = t1.descGroup

        WHERE idDatabricks IS NULL
        AND (t1.flTwitchSub=1 OR t2.flSubRequire=0)
        ;'''

        df = pd.read_sql_query(query, self.con)
        for i in tqdm(df.index):
            data = df.iloc[i].to_dict()
            self.create_user(self.con, self.user_client, data)


    def delete_users(self):
        query = '''
        SELECT DISTINCT t1.idDatabricks AS idDatabricks 
        FROM tb_databricks_users AS t1
        LEFT JOIN tb_user as t2
        ON t1.idDatabricks = t2.idDatabricks
        WHERE t2.idDatabricks IS NULL
        '''

        values = pd.read_sql_query(query, self.con)['idDatabricks'].tolist()
        for v in tqdm(values):
            self.user_client.delete_user(v)
        return None


    def update_user(self,user_data:dict):
        user_name = user_data["descUserEmail"]
        user_id = user_data["idDatabricks"]
        groups = [user_data["idGroup"]]
        resp = self.user_client.update_user(user_id, user_name, groups)
        return resp


    def update_users(self):
        query = '''
        SELECT *
        FROM tb_user AS t1

        LEFT JOIN tb_group AS t2
        on t2.descGroup = t1.descGroup

        LEFT JOIN tb_databricks_users AS t3
        ON t1.idDatabricks = t3.idDatabricks

        WHERE t1.idDatabricks IS NOT NULL
        AND (t1.descGroup <> t3.descGroup OR t3.descGroup is null)
        ;'''

        df = pd.read_sql_query(query, self.con)
        for i in tqdm(df.index):
            data = df.iloc[i].to_dict()
            resp = self.update_user(self.user_client, data)


    def activate_user(self, user_data: dict):
        user_id = user_data["idDatabricks"]
        resp = self.user_client.activate_user(user_id)

        try:
            data = resp.json()
            user_data["descDatabricksStatus"] = int(data["active"])

            user_data = self.format_user_data(user_data)
            db_user.update_user(self.con, user_data, "descUserEmail")
            return data

        except KeyError:
            return data
        
        except AttributeError:
            return resp


    def activate_users(self):
        query = '''
        SELECT *
        FROM tb_user AS t1

        LEFT JOIN tb_group AS t2
        on t2.descGroup = t1.descGroup

        WHERE t1.idDatabricks IS NOT NULL
        AND (t1.flTwitchSub=1 OR t2.flSubRequire=0)
        AND descDatabricksStatus=0;
        '''
        df = pd.read_sql_query(query, self.con)
        for i in tqdm(df.index):
            data = df.iloc[i].to_dict()
            self.activate_user(self.con, self.user_client, data)


    def deactivate_user(self, user_data: dict):
        user_id = user_data["idDatabricks"]
        resp = self.user_client.deactivate_user(user_id)

        try:
            data = resp.json()
            user_data["descDatabricksStatus"] = int(data["active"])
            user_data = self.format_user_data(user_data)
            db_user.update_user(self.con, user_data, "descUserEmail")
            return data

        except KeyError:
            return data

        except AttributeError:
            return resp


    def deactivate_users(self):
        query = '''
        SELECT *
        FROM tb_user AS t1

        LEFT JOIN tb_group AS t2
        on t2.descGroup = t1.descGroup

        WHERE t1.idDatabricks IS NOT NULL
        AND (t1.flTwitchSub=0 AND t2.flSubRequire=1)
        AND descDatabricksStatus=1;
        '''
        df = pd.read_sql_query(query, self.con)
        for i in tqdm(df.index):
            data = df.iloc[i].to_dict()
            self.deactivate_user(self.con, self.user_client, data)


    def update_databricks_table(self):

        data, _ = self.get_all_databricks_users()

        df = pd.DataFrame(data)
        columns = ["id","userName","groups"]
        
        df = df[columns].explode("groups")
        df['descGroup'] = df['groups'].apply(lambda x: x['display'] if type(x)==dict else None)

        del df['groups']

        df = df.rename(columns={"id":"idDatabricks", "userName":"descUserEmail"})

        df.to_sql('tb_databricks_users', self.con, index=False, if_exists='replace')
        
        return data
