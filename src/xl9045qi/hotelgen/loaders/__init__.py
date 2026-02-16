from . import mssql as msql
from . import mongo

LOADERS = [msql.MssqlDatabaseLoader, mongo.MongoDatabaseLoader]
