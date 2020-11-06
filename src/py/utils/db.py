import peewee as pee
import numpy as np
import base64
import json
import time
import shutil

db = pee.SqliteDatabase("images.db")
db.connect()

def backup(path="images.db"):
    with db.atomic("EXCLUSIVE"):
        out_path = "backups/backup-{}.db".format(int(time.time()))
        shutil.copy(path, out_path)

class IdField(pee.TextField):
    def db_value(self, value):
        return str(value)

    def python_value(self, value):
        return int(value)

class ColorsField(pee.TextField):
    def db_value(self, value):
        return base64.b64encode(value).decode("utf-8")

    def python_value(self, value):
        raw = base64.b64decode(value)
        arr = np.frombuffer(raw, dtype="float")
        return arr.reshape((8, 4))

class TagsField(pee.TextField):
    def db_value(self, value):
        arr = [" ".join(tag) for tag in value]
        return "-".join(arr)

    def python_value(self, value):
        arr = [tag.split(" ") for tag in value.split("-")]
        return arr

class JsonField(pee.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is None:
            return None

        return json.loads(value)

class BaseModel(pee.Model):
    class Meta:
        database = db

class Image(BaseModel):
    id_ = IdField(unique=True, primary_key=True)
    path = pee.TextField(unique=True)
    colors = ColorsField()
    tags = TagsField()
    metadata = JsonField(null=True)

db.create_tables([Image])
