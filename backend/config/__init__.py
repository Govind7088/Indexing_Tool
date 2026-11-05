import pymysql

# Django ka MySQL backend mysqlclient 2.2.1+ maangta hai.
# Purane PyMySQL ka version number chhota dikhta hai, isliye version fake karte hain.
if pymysql.version_info < (2, 2, 1):
    pymysql.version_info = (2, 2, 1, 'final', 0)

pymysql.install_as_MySQLdb()