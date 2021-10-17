from flask_login import UserMixin
from flask import g
import sqlite3 as sql
import dataclasses
import itertools

def get_db():
	"""
	Used to get the database connection object, returns a local version or the one tied to flask depending on whether it is being run.
	"""
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
	"""
	A ORM based class that is used to get or crate a Python-esque version of a table in Mysql.
	Created from scratch using dataclasses. Contains a bunch of useful functions and features that makes accessing MySql tables so much easier in Python

	For each class that extends it, if the name of the class is {name},
	then there is a dataclass created called {name}_Data which contains the class variable names as it's field names and the class variable's values as its type.
	Ex: id = int would be a integer field called id. 

	If you want to add extra fields to the {name}_Data instance or to make it instance another class, override Model#__data_customization__
	"""
	fields = []
	def __init_subclass__(cls):
		"""
		When a class extends Model, a new class with its name suffixed by _Data will be created representing the raw table data in the form of an class.
		That is the role of this function.
		"""
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
		"""
		The function which will create the table in the SQL file (if it doesn't exist) 
		"""
		separate = [i+" {}".format(sql_equiv[getattr(cls,i)]) for i in cls.__fields__]
		if not getattr(cls, "__primary_key__", None) == "":
			separate[0] += " PRIMARY KEY"
		columns = ", ".join(separate)
		statement = "CREATE TABLE IF NOT EXISTS {} ( ".format(cls.__table_name__) + columns + ");"
		db = get_db()
		cur = db.cursor()
		cur.execute(statement)
		db.commit()

	@classmethod
	def get_all(cls, order="", reverse=False) -> list:
		"""
		Returns all the rows in the table in the form a {name}_Data list

		Args:
			order [str]: The field name for which you want the list ordererd by
			reverse [bool]: Should the order be in descending 

		Returns:
			[list] : All the rows in the table in the form of {name}_Data instances
		"""
		order_append = " ORDER BY {}".format(order) + (" DESC" if reverse else "") if len(order) > 0 else ""  
		db = get_db()
		cur = db.cursor()
		cur.execute("SELECT * FROM {}".format(cls.__table_name__) + order_append)
		data = []
		for i in cur.fetchall():
			data.append(cls.dataclass(*i))
		return data


	@classmethod
	def get_filtered(cls, predicate, order="", reverse=False) -> list:
		"""
		Returns the rows which holds the needed data, handled by the predicate. 
		The predicate should be a [{name}_Data -> bool] function which handles a row in the form of a {name}_Data instance and returns whether the instance is needed or not by returning true or false. 
		
		Args:
			predicate [function]: A function which returns true or false based on whether the row is needed in the output or not.
			order [str]: The field name for which you want the list ordered by
			reverse [bool]: Should the order be in descending 

		Returns:
			[list]: The filtered rows in the table in the form of {name}_Data instances.
		"""
		org = cls.get_all(order, reverse)
		filtered = list(filter(predicate, org))
		return filtered
	
	@classmethod
	def get_first(cls, predicate, order="", reverse=False):
		"""
		Returns the first row ( when ordered chronologically by creation date ) of all the rows which return true after bring passed into the predicate. 
		The predicate should be a [{name}_Data -> bool] function which handles a row in the form of a {name}_Data instance and returns whether the instance is needed or not by returning true or false.

		Args:
			[predicate (function)]: A function which returns true or false based on whether the row is needed in the output or not.

		Returns:
			[{name}_Data]: A {name}_Data instance of the first row of the table which satisfies the predicate provided. 
		"""
		org = cls.get_all(order, reverse)
		filtered = list(filter(predicate, org))
		return filtered[0] if filtered else filtered 
	
	@classmethod
	def create_record(cls, *args, **kwargs):
		"""
		Create a {name}_Data instance of a record which is not in a table with the intent of adding it to the actual MySQL database with Model#append_record

		Returns:
			[{name}_Data]: The record in ORM ({name}_Data) form 
		"""
		return cls.dataclass(*args, **kwargs)

	@classmethod
	def append_record(cls, data):
		"""
		Appends a {name}_Data instance to the actual SQL database

		Args:
			data ({name}_Data): The model table dataclass instance that is to be added to the SQL database 
		"""
		db = get_db()
		cur = db.cursor()
		print("INSERT OR IGNORE INTO {} VALUES (".format(cls.__table_name__) + ", ".join("?"* len(dataclasses.fields(cls.dataclass))) + ");")
		print(dataclasses.astuple(data))
		cur.execute("INSERT OR IGNORE INTO {} VALUES (".format(cls.__table_name__) + ", ".join("?"* len(dataclasses.fields(cls.dataclass))) + ");", dataclasses.astuple(data))
		db.commit()
	
	@classmethod
	def update_record(cls, data, id_column=None):
		"""
		When given a {name}_Data instance, it will set the analogous record in the database to match the instance's values.
		The instance given has to have at least one unique key column which matches it analogous record's value (which is presumed to be the first given field in the Model class if not given).

		Args:
			data ({name}_Data): The {name}_Data instance with the new values 
			id_column (str, optional): The unique key column with the matching data. Defaults to first field given in the parent Model extending class.
		"""
		db = get_db()
		cur = db.cursor()
		id_column = id_column if id_column else cls.__fields__[0]
		values = ", ".join([i+"=?" for i in cls.__fields__]) 
		print("UPDATE {} SET {} WHERE {}".format(cls.__table_name__, values, id_column + "=?"))
		cur.execute("UPDATE {} SET {} WHERE {}".format(cls.__table_name__, values, id_column + "=?"), dataclasses.astuple(data) + (getattr(data, id_column),))
		db.commit()
	
	@classmethod
	def delete_record(cls, **kwargs):
		"""
		When given a field and it's value as a keyword arguemnt, it will delete the corresponding record holding those values in the same fields.
		"""
		db = get_db()
		cur = db.cursor()
		values = " AND ".join([i+"=?" for i in kwargs])
		print("DELETE FROM {} WHERE {};".format(cls.__table_name__, values))
		cur.execute("DELETE FROM {} WHERE {}".format(cls.__table_name__, values), tuple(kwargs.values()))
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
		"""
		Used by Model to add custom fields to the {name}_Data instance.
		"""
		return ((UserMixin, ),{
			'is_active': lambda self: bool(self.is_active),
			'is_authenticated': lambda self: bool(self.is_authenticated),
			'is_anonymous': lambda self: False,
			'get_id': lambda self: self.user_id,
			'__eq__': lambda self, other: (self.get_id() == other.get_id()) if isinstance(other, UserMixin) else False,
			"__ne__": lambda self, other: not self.__eq__(other)
		})
	
class CartItem(Model):
	cartitem_id=int
	user_id=int
	item_id=int
	qty=int

class Items(Model):
	item_id=int
	name=str
	description=str
	cost=float
	is_available=bool

class Bills(Model):
	bill_id  = str
	time_generated= int #In Unix timestamp
	customer_id = int

class BillItems(Model):
	item_id=int
	qty=int
	bill_id=int
	__primary_key__ = ""
