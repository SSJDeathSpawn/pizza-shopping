from urllib.parse import urlsplit
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from wtforms.fields import FormField, SelectField
from wtforms.csrf.session import SessionCSRF
from dotenv import load_dotenv
import os
from flask import session
from wtforms.fields.core import DateField, IntegerField
from classes import Users
import hashlib
import datetime

load_dotenv()
RAW_KEY = os.getenv('CSRF_KEY')
KEY = bytes(RAW_KEY, 'utf8')

class CustomForm(Form):
    class Meta:
        csrf = True
        csrf_class=SessionCSRF
        csrf_secret= KEY

        @property
        def csrf_context(self):
            return session

class LoginForm(CustomForm):
    username = StringField('Username', validators=[validators.Length(min=4,max=25), validators.input_required()])
    password = PasswordField('Password', validators=[validators.input_required()])

class SignUpForm(CustomForm):
    username = StringField('Username', validators=[validators.InputRequired(), validators.Length(min=5, max=25)])
    email = StringField('Email', validators=[validators.InputRequired(), validators.Email("Not a valid email address!")])
    full_name = StringField('Full Name (For Address)', validators=[validators.InputRequired(), validators.Length(min=7, max=30)])
    address = TextAreaField('Address', validators=[validators.InputRequired()])
    password = PasswordField('Password', validators=[validators.InputRequired(), validators.Length(min=8, max=25)])
    confirm = PasswordField('Confirm Password', validators=[validators.InputRequired(), validators.Length(min=8, max=25), validators.EqualTo('password', "Passwords do not match!")])

class ForgotPasswordForm(CustomForm):
    email = StringField('Email', validators=[validators.Length(min=10, max=30), validators.input_required()])

class NotEqualTo(object):
    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        if not message:
            message = u'This field is required.'
        self.message = message

    def __call__(self, form, field):
        try:
            other=form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(field.gettest("Invalid field name '%s'.") % self.fieldname)
        if other.data == field.data:
            raise validators.ValidationError(self.message)

class ConditionalOptional(object):
    def __init__(self, fieldname, message=None):
        self.fieldname=fieldname
        if not message:
            message = u'This field is required.'
        self.message = message

    def __call__(self, form, field):
        try:
            other=form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(field.gettest("Invalid field name '%s'.") % self.fieldname)
        if other.data and not field.data:
            raise validators.ValidationError(self.message)

class EditProfileForm(CustomForm):
    username = StringField('Username', validators=[validators.Length(min=4,max=25), validators.input_required()])
    email = StringField('Email', render_kw={'readonly': True})
    name = StringField('Name', render_kw={'readonly': True})
    address = TextAreaField('Address', validators=[validators.InputRequired(message="Address cannot be empty!")])
    new_password = PasswordField('New Password', validators=[validators.optional(strip_whitespace=True), ConditionalOptional('password', "New password cannot be empty."), NotEqualTo('password', "New password cannot be the same as the old password.")])
    password = PasswordField('Password', validators=[ConditionalOptional('new_password', "Please enter your password.")])
    confirm  = PasswordField('Repeat Password', validators=[validators.equal_to('password', message="Password do not match")]) 

class LuhnAlgo(object):
    def __init__(self, message=None):
        if not message:
            message="Invalid card"
        self.message=message
    
    def __call__(self, form, field):
        nums = list(map(int, field.data))[:-1]
        check_digit= sum([sum(list(map(int, str(nums[i]*2)))) if i&1 else sum(list(map(int, str(nums[i])))) for i in range(len(nums))]) % 10
        if nums[-1] != check_digit:
            raise validators.ValidationError(self.message)

class BeforeDate(object):
    def __init__(self, message=None):
        if not message:
            message="Expired"
        self.message = message

    def __call__(self, form, field):
        date = field.data
        given = datetime.date(day=1,month=int(date[:2]),year=2000+int(date[3:]))
        today = datetime.date.today()
        if given <= today:
            raise validators.ValidationError(self.message)

class CreditCardForm(CustomForm):
    number = StringField('Card Number', validators=[validators.InputRequired(), LuhnAlgo("This card is invalid.")])
    name = StringField('Name on Card', validators=[validators.InputRequired()])
    expiry = DateField('Use By Date', validators=[validators.InputRequired(), BeforeDate("Your card has expired.")], format='%m/%y')
    cvv = IntegerField('CVV', validators=[validators.InputRequired(), validators.NumberRange(min=0,max=999, message="Your CVV is more than 3 digits or negative.")])

class Upi(object):
    def __init__(self, message=None):
        if not message:
            message="Invaid UPI"
        self.message = message

    def __call__(self, form, field):
        upi = field.data
        if '@' not in upi:
            raise validators.ValidationError(self.message)

class UPIForm(CustomForm):
    upi = StringField('upi', validators=[validators.InputRequired(), Upi('Please enter a valid UPI')])

class CheckoutForm(CustomForm):
    payment_option = SelectField(u'Payment Method', choices=[('card','Credit/Debit Card'), ('cod', 'Cash on Delivery (Not encouraged)'), ('upi', 'UPI')])