import sqlite3 as sql
import os
import hashlib
import secrets
from classes import Users
from flask import g

def get_db():
    if g:
        db=get_db()
    else:        
        db = sql.connect('database.db')
        return db

def get_users():
    con=get_db()
    cur=con.cursor()
    cur.execute("SELECT * from Users")
    users = cur.fetchall()
    return users

def validate_user(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE Item SET (is_authenticated=1, is_active=1) WHERE user_id=?", [user_id])
    con.commit()

def get_user(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * from Users WHERE user_id=?", [user_id])
    i = cur.fetchone()
    return (User(*i) if i else i)

def insert_user(username, email, password, full_name, address):
    alg = hashlib.sha256()
    alg.update(bytes(password, 'utf8'))
    hashed_password = alg.hexdigest()
    con = get_db()
    cur = con.cursor()
    r = secrets.choice(range(10000,9999999))
    while get_user(r) != None:
        r = secrets.choice(range(10000,9999999))
    cur.execute("INSERT INTO Users VALUES (?, ?, ?, ?, ?, ?, 0, 0)", [r, email, username, hashed_password, full_name, address])
    con.commit()
