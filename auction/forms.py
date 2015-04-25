from django import forms
from django.contrib.auth.models import User
from models import *
from decimal import *
from datetime import date
#import re
import localflavor.us.forms

forms.DateInput.input_type="date"

def checkTwoDecimalPlaces(price):
	e = abs(Decimal(str(price)).as_tuple().exponent)
	if e > 2:
		raise forms.ValidationError('Can only have two decimal places')

class RegistrationForm(forms.Form):
	firstName = forms.CharField(max_length=20, label='First Name',widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'First Name'}))
	lastName = forms.CharField(max_length=20, label='Last Name',widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'Last Name'}))
	email = forms.EmailField(max_length=75,widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':' Email'}))
	username = forms.CharField(max_length=20,widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'Username'}))
	address = forms.CharField(max_length=40,widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'Address'}))
	city = forms.CharField(max_length=40,widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'City'}))
	state = localflavor.us.forms.USStateField(widget=forms.Select(choices=localflavor.us.us_states.US_STATES,attrs={'class':'form-control'}))
	zipcode = localflavor.us.forms.USZipCodeField(widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'ZipCode'}))
	password1 = forms.CharField(max_length=200, label='Password',
		widget=forms.PasswordInput(attrs={'class':'form-control input-lg','placeholder':'Password'}))
	password2 = forms.CharField(max_length=200, label='Confirm password',
		widget=forms.PasswordInput(attrs={'class':'form-control input-lg','placeholder':'Confirm Password'}))
	
	# Customizes form validation for properties that apply to more
	# than one field. Overrides the forms.Form.clean function.
	def clean(self):
		# Calls our parent (forms.Form) .clean function, gets a dictionary
		# of cleaned data as a result
		cleaned_data = super(RegistrationForm, self).clean()
		# Confirms that the two password fields match
		username = cleaned_data.get('username')
		password1 = cleaned_data.get('password1')
		password2 = cleaned_data.get('password2')
		if password1 is None or password2 is None:
			raise forms.ValidationError('Enter passwords')
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError('Passwords did not match.')
		#The form validator already checks for the @ in the email
		#but we cant assume the HTTP reuqest was sent from our website
		#so we check agin here

		#NOTE: In DJango, the email field for a user is optional 
		#but for us we want it to be required.
		email = cleaned_data.get('email')
		if email is None:
			raise forms.ValidationError('Email is a required field')
		if email.index('@') == -1:
			raise forms.ValidationError('Invalid Email address')
		if email.rfind('.') == len(email) - 3:
			raise forms.ValidationError('Invalid Email address')
		if len(email) > 75:
			raise forms.ValidationError('Email too long')
		firstName = cleaned_data.get('firstName')
		if len(firstName) > 20:
			raise forms.ValidationError('First Name too long')
		lastName = cleaned_data.get('lastName')
		if len(lastName) > 20:
			raise forms.ValidationError('Last Name too long')
		username = cleaned_data.get('username')
		if len(username) > 20:
			raise forms.ValidationError('username too long')
		if len(password1) > 200 or len(password2) > 200:
			raise forms.ValidationError('password too long')
		# We must return the cleaned data we got from our parent.
		return cleaned_data

	# Customizes form validation for the username field.
	def clean_username(self):
		# Confirms that the username is not already present in the
		# User model database.
		username = self.cleaned_data.get('username')
		if User.objects.filter(username__exact=username):
			raise forms.ValidationError('Username is already taken.')
		# We must return the cleaned data we got from the cleaned_data
		# dictionary
		return username

	def clean_email(self):
		email = self.cleaned_data.get('email')
		if User.objects.filter(email__exact=email):
			raise forms.ValidationError('Email already taken')
		return email


class ForgotPasswordForm(forms.Form):
	username = forms.CharField(max_length=20)
	email = forms.EmailField(max_length=75)

	def clean(self):
		cleaned_data = super(ForgotPasswordForm, self).clean()
		username = cleaned_data.get('username')
		try:
			user = User.objects.get(username=username)
		except:
			raise forms.ValidationError('A user with username ' + username + ' does not exist')

		email = cleaned_data.get('email')
		if user.email != email:
			raise forms.ValidationError('Username and email do not match')
		return cleaned_data

class ForgotUsernameForm(forms.Form):
	email = forms.EmailField(max_length=75)
	password = forms.CharField(max_length=20, widget=forms.PasswordInput())

	def clean(self):
		cleaned_data = super(ForgotUsernameForm, self).clean()
		password = cleaned_data.get('password')
		email = cleaned_data.get('email')

		users = User.objects.filter(email=email)
		#Assuming two users do not have the same password and email address
		for u in users:
			if u.check_password(password):
				return cleaned_data
		raise forms.ValidationError('Could not find user')

class ChangePasswordForm(forms.Form):
	password1 = forms.CharField(max_length=200, label='New Password', widget=forms.PasswordInput())
	password2 = forms.CharField(max_length=200, label='Confirm Password', widget=forms.PasswordInput())

	def clean(self):
		cleaned_data = super(ChangePasswordForm, self).clean()
		password1 = cleaned_data.get('password1')
		password2 = cleaned_data.get('password2')
		if password1 != password2:
			raise forms.ValidationError('Passwords do not match')
		if len(password1) > 200:
			raise forms.ValidationError('Password too long')
		return cleaned_data

class AddingItemForm(forms.ModelForm): 
	
	class Meta:
		model = Item
		exclude = (
            'seller',
            'isSold',
            'buyer',
            'finalPrice',
            'boughtDate',
            'bidInfo',
            'sumStars',
            'numReviews',
            'numStarRequests',
            'picture_url'
            )
		labels = {
			'bidPrice': 'Bid Price',
			'endBidDate': 'End Bid Date',
			'sellingChoice': 'Selling Choice'
		}
	picture = forms.FileField(required=False)

	def clean(self):
		cleaned_data = super(AddingItemForm, self).clean()
		title = cleaned_data.get('title')
		if not title or len(title) > 20:
			raise forms.ValidationError('Invalid title')
		description = cleaned_data.get('description')
		if not description or len(description) > 600:
			raise forms.ValidationError('Invalid Description')
		price = cleaned_data.get('price')
		if price: 
			checkTwoDecimalPlaces(price)
			if price < .5 or price > 99999999.99:
				raise forms.ValidationError('Price too big or too small')
		bidPrice = cleaned_data.get('bidPrice')
		if bidPrice:
			checkTwoDecimalPlaces(bidPrice)
			if bidPrice < .5 or bidPrice > 99999999.99:
				raise forms.ValidationError('Bid Price too big or too small')
		sellingChoice = cleaned_data.get('sellingChoice')			

		endBidDate = cleaned_data.get('endBidDate')
		if sellingChoice == 'BUY':
			if bidPrice or endBidDate or not price:
				raise forms.ValidationError('Form is inconsistent')
		elif sellingChoice == 'BID':
			if price or not bidPrice or not endBidDate:
				raise forms.ValidationError('Form is inconsistent')
		elif sellingChoice == 'BIDBUY':
			if not (bidPrice and price and endBidDate):
				raise forms.ValidationError('Form is inconsistent')
		else:
			raise forms.ValidationError('Illegal Selling choice')
		if endBidDate and endBidDate < date.today():
			raise forms.ValidationError('Cannot have end bid date in the past')
		return cleaned_data

class SearchForm(forms.Form):
	search = forms.CharField(max_length=200,widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'Search',
							'float':'none','margin':'auto'}))

	def clean(self):
		cleaned_data = super(SearchForm, self).clean()
		search = cleaned_data.get('search')
		if search and len(search) > 200:
			raise forms.ValidationError('Search too long')
		return cleaned_data

class BidForm(forms.Form):
	bid = forms.DecimalField(decimal_places=2, max_digits=10)

	def clean(self):
		cleaned_data = super(BidForm, self).clean()
		bid = cleaned_data.get('bid')
		#How to check that bid is greater than the bidPrice here and not in views
		if bid <= 0:
			raise forms.ValidationError('Cannot bid a negative amount')
		checkTwoDecimalPlaces(bid)
		return cleaned_data

class CommentForm(forms.Form):
	review = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class':'form-control input-lg','placeholder':'Post a Review',
							'float':'none','margin':'auto'}))

	def clean(self):
		cleaned_data = super(CommentForm, self).clean()
		review = cleaned_data.get('review')
		if review and len(review) <= 200:
			return cleaned_data
		raise forms.ValidationError('Review either missing or too long')

class EmailForm(forms.Form):
	subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Subject',
							}))
	body = forms.CharField(max_length=10000, widget=forms.Textarea(attrs={'class':'form-control','placeholder':'Email Body',
							}))


	def clean(self):
		cleaned_data = super(EmailForm, self).clean()
		subject = cleaned_data.get('subject')
		body = cleaned_data.get('body')
		if not subject or len(subject) > 200:
			raise forms.ValidationError('Subject too long')
		if not body or len(body) > 10000:
			raise forms.ValidationError('Email too long')
		return cleaned_data

class EditItemForm(forms.ModelForm):
	class Meta:
		model = Item
		exclude = (
			'finalPrice',
			'seller',
			'buyer',
			'isSold',
			'creationDate',
			'boughtDate',
			'bidInfo',
			'numReviews',
			'sumStars',
			'numStarRequests',
			'bidPrice',
			'endBidDate',
			'sellingChoice',
			'picture_url'
		)
		labels = {
			'endBidDate': 'End Bid Date',
			'sellingChoice': 'Selling Choice'
		}

	def clean(self):
		cleaned_data = super(EditItemForm, self).clean()
		title = cleaned_data.get('title')
		if not title or len(title) > 20:
			raise forms.ValidationError('Invalid title')
		description = cleaned_data.get('description')
		if not description or len(description) > 600:
			raise forms.ValidationError('Invalid description')
		price = cleaned_data.get('price')
		if price: 
			checkTwoDecimalPlaces(price)
			if price < .5 or price > 99999999.99:
				raise forms.ValidationError('Price too big or too small')
		bidPrice = cleaned_data.get('bidPrice')
		endBidDate = cleaned_data.get('endBidDate')
		if bidPrice or endBidDate:
			raise forms.ValidationError('error')
		return cleaned_data