from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from wtforms.csrf.session import SessionCSRF
from dotenv import load_dotenv
import os
from flask import session
from classes import Users
import hashlib

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