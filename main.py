import dataclasses
from flask import Flask, json, render_template, url_for, redirect, g, make_response, jsonify, request
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
from classes import Items, Users
from models import get_user

DATABASE = 'database.db'

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
CSRF_KEY = os.getenv('CSRF_KEY')

app = Flask(__name__)
app.secret_key = bytes(SECRET_KEY, 'utf8')
app.config['CSRF_SECRET_KEY'] = bytes(CSRF_KEY, 'utf8')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = None

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)
	return db

@app.teardown_appcontext
def close_connection(exception):
	db = getattr(g, '_database', None)
	if db is not None:
		db.commit()
		db.close()

def init_db():
	with app.app_context():
		db = get_db()
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()

def fill_db():
	with open('items.txt', mode='r') as f:
		data = []
		for i in f.readlines():
			j = i[:-1].split("; ")
			print(j)
			data += [Items.create_record(item_id=j[0], name=j[1], description=j[2], cost=j[3], is_available=j[4])]
		with app.app_context():
			db = get_db()
			for i in data:
				Items.append_record(i)
			db.commit()

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


@login_manager.user_loader
def load_user(user_id):
	t = Users.get_filtered(lambda x: x.user_id == user_id)
	return t[0] if t != [] else None

@app.route('/', methods=['GET', 'POST'])
def index():
	form = LoginForm(request.form)
	error = ""
	open_modal = "false"
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

@app.route('/reviews/')
def reviews():
	return render_template('reviews_home.html')

@app.route('/order/', methods=['GET', 'POST'])
def order():
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
	time.sleep(0.5)
	print("Reached here!")
	if request.args:
		counter = int(request.args.get("c"))
		print([dataclasses.asdict(i) for i in Items.get_filtered(lambda x: x.item_id in range(counter*ITEM_LOAD_QUANTITY, (counter+1)*ITEM_LOAD_QUANTITY))])
		if counter*ITEM_LOAD_QUANTITY < len(Items.get_all()):
			res = make_response(jsonify([dataclasses.asdict(i) for i in Items.get_filtered(lambda x: x.item_id in range(counter*ITEM_LOAD_QUANTITY, (counter+1)*ITEM_LOAD_QUANTITY))]), 200)
		else:
			res = make_response(jsonify({}), 200)
		
		return res

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
		elif form.password.data == "1234":
			error = "Do you want your account to be hacked that easily?"
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

if len(sys.argv) == 1 :
	if __name__=="__main__":
		app.run(host="0.0.0.0", port=8080, threaded=True,debug=True)
else:
	if __name__ == "__main__":
		if sys.argv[1].lower() == "init":
			init_db()
			print("hello")
			fill_db()
