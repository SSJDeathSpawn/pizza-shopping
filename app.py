import dataclasses
from flask import Flask, json, render_template, url_for, redirect, g, make_response, jsonify, request, Response
import math
from flask_login import LoginManager, login_user, current_user
import os
import string
import random
from urllib.parse import urlparse, urljoin
from flask import request, url_for
import time
from flask_login.utils import login_required, logout_user
from forms import *
from dotenv import load_dotenv
import sqlite3
from constants import *
import hashlib
import sys
from classes import *

DATABASE = 'database.db'

SECRET_KEY = os.getenv('SECRET_KEY')
CSRF_KEY = os.getenv('CSRF_KEY')

app = Flask(__name__)
app.secret_key = bytes(SECRET_KEY, 'utf8')
app.config['CSRF_SECRET_KEY'] = bytes(CSRF_KEY, 'utf8')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = None

def get_db():
	"""
	Get the database connection object related to Flask, and if doesn't exist create one

	Returns:
		[sqlite3.Connection]: The connection object which can interact with the database 
	"""
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)
		with open('items.txt', mode='r') as f:
			data = []
			for i in f.readlines():
				j = i[:-1].split("; ")
				print(j)
				data += [Items.create_record(item_id=j[0], name=j[1], description=j[2], cost=j[3], is_available=j[4])]
			with app.app_context():
				for i in data:
					Items.append_record(i)
				db.commit()
	return db

@app.teardown_appcontext
def close_connection(exception):
	"""
	This function is executed when the flask webserver is taken down
	"""
	db = getattr(g, '_database', None)
	if db is not None:
		db.commit()
		db.close()

def fill_db():
	"""
	Auto fills the database with the items that you have can order
	"""

def is_safe_url(target):
	"""
	Checks if the given url is safe to redirect to

	Args:
		target (str): The path which you want to check is safe

	Returns:
		[bool]: Is the given url safe or not
	"""
	ref_url = urlparse(request.host_url)
	test_url = urlparse(urljoin(request.host_url, target))
	return test_url.scheme in ('http', 'https') and \
		   ref_url.netloc == test_url.netloc


@login_manager.user_loader
def load_user(user_id):
	"""
	When given a user id, it returns the Model-based instance of the user

	Args:
		user_id (int): The user id for which you need the details of

	Returns:
		[User_Data]: User information of the user with the given ID
	"""
	t = Users.get_filtered(lambda x: x.user_id == user_id)
	return t[0] if t != [] else None

@app.context_processor
def get_items():
	"""
	Can be used in templates to get a certain item known the id

	Returns:
		[dict]: A dictionary which contains function to get a certain item, when given the id 
	"""
	def get_item(item_id):
		return Items.get_first(lambda x: x.item_id == item_id)
	return dict(get_item=get_item)

@app.route('/', methods=['GET', 'POST'])
def index():
	"""
	Flask endpoint for the index page of the website

	Returns:
		[str]: The HTML output
	"""
	form = LoginForm(request.form)
	error = ""
	open_modal = "false"
	if request.args:
		alert = request.args.get('message', "Ominous Message")
	if request.method=='POST' and form.validate():
			hashed_password = hashlib.sha256(str.encode(form.password.data, 'utf-8')).hexdigest()
			users = Users.get_filtered(lambda x: x.username==form.username.data and x.password==hashed_password)
			if users:
				user = users[0]
				login_user(user)
				return redirect(url_for('index'))
			else:
				error = "User details didn't match. Incorrect username or password!"
				open_modal = "true"
	return render_template('index.html', form=form, error=error, request=request, open_modal=open_modal)

@app.route('/order/', methods=['GET', 'POST'])
def order():
	"""
	Flask enpoint for the menu page

	Returns:
		[str]: The HTML output
	"""
	form = LoginForm(request.form)
	error = ""
	open_modal="false"
	if request.method=='POST' and form.validate():
			hashed_password = hashlib.sha256(str.encode(form.password.data, 'utf-8')).hexdigest()
			users = Users.get_filtered(lambda x: x.username==form.username.data and x.password==hashed_password)
			if users:
				user = users[0]
				login_user(user)
				return redirect(url_for('order'))
			else:
				error = "User details didn't match. Incorrect username or password!"
				open_modal = "true"
	return render_template('order_home.html', form=form, error=error, request=request, open_modal=open_modal)

@app.route('/item/')
def item():
	"""
	Endpoint which returns a set of items when a GET request is sent to it in JSON format
	It is paginated which means that it gives a set of items if c=1 and the next set if c=2 and so on

	Returns:
		[flask.wrappers.Response]: The response to the GET request with the JSON data in it
	"""
	time.sleep(0.2)
	if request.args:
		counter = int(request.args.get("c"))
		print([dataclasses.asdict(i) for i in Items.get_filtered(lambda x: x.item_id in range(counter*ITEM_LOAD_QUANTITY, (counter+1)*ITEM_LOAD_QUANTITY))])
		if counter*ITEM_LOAD_QUANTITY < len(Items.get_all()):
			res = make_response(jsonify([dataclasses.asdict(i) for i in Items.get_filtered(lambda x: x.item_id in range(counter*ITEM_LOAD_QUANTITY, (counter+1)*ITEM_LOAD_QUANTITY))]), 200)
		else:
			res = make_response(jsonify({}), 200)
		
		return res

@app.route('/bill/')
def bill():
	"""
	Endpoint which sends all the bill items of a set of bills when a GET request is sent to it in JSON format.
	It is paginated which means that it gives a set of bill items if c=1 and the next set of bill items if c=2 and so on   

	Returns:
		[flask.wrappers.Response]: The response to the GET request with the requested JSON data in it
	"""
	time.sleep(0.2)
	try:
		if request.args:
			count = int(request.args.get("c"))
			user=Users.get_first(lambda x: x.user_id == int(request.args.get("uid")))
			if (user and count*ITEM_LOAD_QUANTITY < len(Bills.get_filtered(lambda x: x.customer_id == user.user_id ))):
				bills = Bills.get_filtered(lambda x: x.customer_id == user.user_id, order="time_generated", reverse=True)
				print(bills)
				bills = bills[count*ITEM_LOAD_QUANTITY: ((count+1)*ITEM_LOAD_QUANTITY if len(bills) >= (count+1)*ITEM_LOAD_QUANTITY else len(bills))]
				all_bill_items = []
				for bill in bills:
					bill_item = []
					for i in BillItems.get_filtered(lambda x: x.bill_id == bill.bill_id):
						temp = dataclasses.asdict(i)
						temp.update({"name": Items.get_first(lambda x: x.item_id == i.item_id).name, "rate":  Items.get_first(lambda x: x.item_id == i.item_id).cost, "time": datetime.datetime.fromtimestamp(int(bill.time_generated)).strftime('%Y-%m-%d %H:%M:%S')})
						bill_item += [temp]
					all_bill_items += [bill_item]
				print(all_bill_items)
				res = make_response(jsonify(all_bill_items), 200)
			else:
				res = make_response(jsonify({}), 200)
	except ValueError as e:
		print("Not an integer")
		res = make_response(jsonify({}), 200)
	return res

@app.route('/add-cart/')
@login_required
def add_cart():
	"""
	Endpoint which adds to the quantity or adds a new item the cart when a GET request is sent to it.
	'id' specifies which item to add and 'qty' specifies how much of the item should be added to the cart

	Returns:
		[flask.wrappers.Response]: An empty OK response if everything goes well
	"""
	if request.args:
		item_id = int(request.args.get("id"))
		qty_change=int(request.args.get("qty"))
		user_id = int(current_user.get_id())
		if not CartItem.get_first(lambda x: x.user_id == user_id and x.item_id ==item_id):
			cartitem_id = random.randint(1,9999999)
			while CartItem.get_first(lambda x: x.cartitem_id == cartitem_id):
				cartitem_id = random.randint(1,9999999)
			cartitem = CartItem.create_record(cartitem_id=cartitem_id, user_id=user_id, item_id=item_id, qty=1)
			CartItem.append_record(cartitem)
		else:
			cartitem = CartItem.get_first(lambda x: x.user_id == user_id and x.item_id == item_id)
			if cartitem.qty >= -qty_change:
				cartitem.qty = cartitem.qty+ qty_change
			CartItem.update_record(cartitem)
		CartItem.delete_record(qty=0)
		return make_response(jsonify({}), 200)

@app.route('/cart')
@login_required
def show_cart():
	"""
	Flask endpoint of the checkout page 

	Returns:
		(str): The HTML output
	"""
	cart = CartItem.get_filtered(lambda x: x.user_id == current_user.get_id())
	total = sum([Items.get_first(lambda x: x.item_id==item.item_id).cost * item.qty for item in cart])
	round_off = 0
	if total %1 !=0:
		round_off = math.floor(total)
	return render_template('show_cart.html', cart=cart, total=total, round_off=round_off, request=request)

@app.route('/checkout/', methods=['GET','POST'])
@login_required
def checkout():
	"""
	Flask enpoint of the payment details page

	Returns:
		(str): The HTML output
	"""
	form1 = CheckoutForm(request.form)
	form2 = None
	if request.method=='POST' and form1.validate():
		selection = {
			'card': CreditCardForm,
			'upi': UPIForm,
			'cod': CODForm
		}
		if form1.payment_option.data:
			form2 = selection[form1.payment_option.data]()
	return render_template('checkout.html', form1=form1, form2=form2)

@app.route('/billing/', methods=["POST"])
@login_required
def billing():
	"""
	Endpoint for generating bill and sending order to the server/database

	Returns:
		(str): HTML output of the page 
	"""	
	a = [UPIForm, CODForm, CreditCardForm]
	for i in a:
		print(list(request.form.keys()),"==", [j.name for j in i()], list(request.form.keys()) in [j.name for j in i()])
		if sorted(list(request.form.keys())) == sorted([j.name for j in i()]):
			form = i(request.form)
	if form.validate():
		bill_id = "".join([random.choice(string.ascii_uppercase + string.digits) for _ in range(6)])
		while Bills.get_first(lambda x: x.bill_id == bill_id):
			bill_id = "".join([random.choice(string.ascii_uppercase + string.digits) for _ in range(6)])
		bill = Bills.create_record(bill_id=bill_id, customer_id=current_user.get_id(), time_generated=time.mktime(datetime.datetime.now().timetuple()))
		for i in CartItem.get_filtered(lambda x: x.user_id == current_user.get_id()):
			bill_item = BillItems.create_record(bill_id=bill_id, item_id=i.item_id, qty=i.qty)
			BillItems.append_record(bill_item)
		Bills.append_record(bill)
		CartItem.delete_record(user_id=current_user.get_id())
	else:
		return render_template('checkout.html', error="Payment failed.", form1=CheckoutForm(), form2=form)
	return redirect(url_for('index', message="Success"))

@app.route('/reserve/')
def reserve():
	return render_template('reserve.html')

@app.route('/signup/', methods=["GET", "POST"])
def signup():
	form = SignUpForm(request.form)
	error = alert = ""
	if request.method=="POST" and form.validate():
		username = form.username.data
		email = form.email.data
		if Users.get_first(lambda x: x.username == username):
			error = "There is already an user with that username"
		elif Users.get_first(lambda x: x.email == email):
			error = "There is an account registered in that email already."
		elif form.password.data == "12345678":
			error = "Do you want your account to be hacked that easily? Please enter another password."
		else:
			hash_pass = hashlib.sha256(str.encode(form.password.data, 'utf-8')).hexdigest()
			address = form.address.data
			full_name=form.full_name.data
			u_id = random.randint(0, 999999999)
			while Users.get_first(lambda x: x.user_id == u_id):
				u_id = random.randint(0, 999999999)
			user = Users.create_record(user_id=u_id, username=username, email=email, password=hash_pass, address=address, full_name=full_name, is_authenticated=True, is_active=True)
			Users.append_record(user)
			alert = "Account registered successfully."
	return render_template('sign_up.html', form=form, error=error, alert=alert)

@app.route('/logout/')
@login_required
def logout():
	logout_user()
	if request.args:
		next = request.args.get("next")
		if is_safe_url(next):
			return redirect(next)
		else:
			return redirect(url_for('index/'))

@app.route('/forgot-password/', methods=['GET', 'POST'])
def forgot_password():
	form = ForgotPasswordForm(request.form)
	error=""
	passw=None
	if request.method=="POST" and form.validate():
		email = form.email.data
		user = Users.get_first(lambda x: x.email==email)
		if user:
			pick = string.ascii_letters + string.digits + "_#$&?^"
			passw = "".join([random.choice(pick) for i in range(10)])
			hashed_passw = hashlib.sha256(str.encode(passw, 'utf-8')).hexdigest()
			user.password = hashed_passw
			Users.update_record(user)
			print(passw)
		else:
			error="No user with that email!"
	return render_template('repassword.html', form=form, error=error, passw=passw)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
	user = Users.get_first(lambda x: x.user_id == current_user.get_id())
	form = EditProfileForm(request.form)
	error = alert = ""
	print(request.method=="POST")
	if request.method=="POST" and form.validate():
		print(form.password.data, form.new_password.data, form.confirm.data)
		if form.password.data:
			if user.password == hashlib.sha256(str.encode(form.password.data, 'utf-8')).hexdigest():
				hash_new_pass = hashlib.sha256(str.encode(form.new_password.data, 'utf-8')).hexdigest()
				user.password = hash_new_pass
			else:
				error = "Password is incorrect."
		user.username = form.username.data
		user.address = form.address.data
		Users.update_record(user)
		alert = "Profile updated."
	else:
		form.username.data, form.email.data, form.address.data, form.name.data = user.username, user.email, user.address, user.full_name 
	return render_template('edit_profile.html', form=form, error=error, alert=alert) 

@app.route('/orders', methods=['GET'])
@login_required
def orders():
	return render_template('past_orders.html')

if __name__ == "__main__":
    app.run()