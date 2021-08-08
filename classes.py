import sqlite3
from flask_login import UserMixin
from flask import g
import sqlite3 as sql
import dataclasses
import itertools

def get_db():
	if g:
		import main
		db = main.get_db()
	else:
		db = sql.connect("database.db")
	return db

sql_equiv = {
	int: 'INT',
	str: 'TEXT',
	bool: 'BOOLEAN',
	float: 'FLOAT'
}

class Model(object):
	fields = []
	def __init_subclass__(cls):
		cls.__table_name__ = str(cls.__qualname__)
		fields = list(filter(lambda x: not(x.startswith("__") and x.endswith("__")) and not x in list(Model.__dict__.keys()), list(cls.__dict__.keys())))
		cls.__fields__ = fields
		fields = [ (i, getattr(cls, i)) for i in fields]
		extra = None
		t = ()
		if hasattr(cls, "__data_customization__"):
			t,extra  = cls.__data_customization__()
		cls.dataclass = dataclasses.make_dataclass(cls.__table_name__ + "_Data", fields, bases=t, namespace=extra)
		cls.create_table()

	@classmethod
	def create_table(cls):
		separate = [i+" {}".format(sql_equiv[getattr(cls,i)]) for i in cls.__fields__]
		separate[0] += " PRIMARY KEY"
		columns = ", ".join(separate)
		statement = "CREATE TABLE IF NOT EXISTS {} ( ".format(cls.__table_name__) + columns + ");"
		db = get_db()
		cur = db.cursor()
		cur.execute(statement)
		db.commit()

	@classmethod
	def get_all(cls) -> list:
		db = get_db()
		cur = db.cursor()
		cur.execute("SELECT * FROM {}".format(cls.__table_name__))
		data = []
		for i in cur.fetchall():
			data.append(cls.dataclass(*i))
		return data

	@classmethod
	def get_filtered(cls, predicate) -> list:
		org = cls.get_all()
		filtered = list(filter(predicate, org))
		return filtered
	
	@classmethod
	def get_first(cls, predicate):
		org = cls.get_all()
		filtered = list(filter(predicate, org))
		return filtered[0] if filtered else filtered 
	
	@classmethod
	def create_record(cls, *args, **kwargs):
		return cls.dataclass(*args, **kwargs)

	@classmethod
	def append_record(cls, data):
		db = get_db()
		cur = db.cursor()
		print("INSERT INTO {} VALUES (".format(cls.__table_name__) + ", ".join("?"* len(dataclasses.fields(cls.dataclass))) + ");")
		print(dataclasses.astuple(data))
		cur.execute("INSERT INTO {} VALUES (".format(cls.__table_name__) + ", ".join("?"* len(dataclasses.fields(cls.dataclass))) + ");", dataclasses.astuple(data))
		db.commit()
	
	@classmethod
	def update_record(cls, data):
		db = get_db()
		cur = db.cursor()
		id_column = cls.__fields__[0]
		values = ", ".join([i+"=?" for i in cls.__fields__]) 
		print("UPDATE {} SET {} WHERE {}".format(cls.__table_name__, values, id_column + "=?"))
		cur.execute("UPDATE {} SET {} WHERE {}".format(cls.__table_name__, values, id_column + "=?"), dataclasses.astuple(data) + (getattr(data, id_column),))
		db.commit()

class Users(Model):
	user_id= int
	email= str
	username= str
	#No plain text passwords here
	password= str
	full_name= str
	address= str
	is_authenticated= bool
	is_active= bool

	@classmethod
	def __data_customization__(cls):
		return ((UserMixin, ),{
			'is_active': lambda self: bool(self.is_active),
			'is_authenticated': lambda self: bool(self.is_authenticated),
			'is_anonymous': lambda self: False,
			'get_id': lambda self: self.user_id,
			'__eq__': lambda self, other: (self.get_id() == other.get_id()) if isinstance(other, UserMixin) else False,
			"__ne__": lambda self, other: not self.__eq__(other)
		})
	
class ShoppingCart(Model):
	cart_id=int
	user_id=int

class CartItem(Model):
	cartitem_id=int
	cart_id=int
	item_id=int
	qty=int

class Reviews(object):
	review_id=int
	author_id=int
	body=str
	rating=int

class Items(Model):
	item_id=int
	name=str
	description=str
	cost=float
	is_available=bool

class Bills(Model):
	bill_id  = int
	customer_id = int

class BillItems(Model):
	billitem_id=int
	item_id=int
	qty=int
	bill_id=int
