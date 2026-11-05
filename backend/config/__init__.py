import pymysql

# PyMySQL ko Django ke MySQL backend ke liye "MySQLdb" ki tarah register karta hai.
# Django 5.2 ko mysqlclient 1.4.3+ chahiye aur PyMySQL ka version_info already
# usse bada report karta hai, isliye version badalne ka koi workaround nahi chahiye.
pymysql.install_as_MySQLdb()