import MySQLdb.cursors
from localauth import sql_dict

class mysql:
    def __init__(self,**kw):
        """sets up connection"""
        creds=sql_dict['mysql']
        self.db=MySQLdb.connect(creds['server'],creds['user'],creds['pass'],creds['db'])
        self.retdict={}
        self.kvdict={}
        self.sql=None

    def buildretdict(self,sql):
        dict_cursor = self.db.cursor(MySQLdb.cursors.DictCursor)
        dict_cursor.execute(sql)
        self.retdict=dict_cursor.fetchall()

    def close(self):
        self.db.close()

    def buildkvdict(self,sql):
        self.buildretdict(sql)
        for obj in self.retdict:
            self.kvdict[str(obj['mykey'])]=obj['myval']

    def insert(self):
        cursor=self.db.cursor()
        cursor.execute(self.sql)
        self.db.commit()
