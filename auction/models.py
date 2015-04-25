from django.db import models

from django.contrib.auth.models import User
import localflavor.us.models

class BiddingInfo(models.Model):
	user = models.ForeignKey(User, null=True)
	amount = models.DecimalField(decimal_places=2, null=True, max_digits=10)

class Item(models.Model):
	title = models.CharField(max_length=20)
	description = models.CharField(max_length=600)
	price = models.DecimalField(blank = True, decimal_places=2, null=True, max_digits=10)
	bidPrice = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10)
	finalPrice = models.DecimalField(blank=True, null= True, decimal_places=2, max_digits=10)
	seller = models.ForeignKey(User, related_name='seller')
	buyer = models.ForeignKey(User, blank=True, related_name='buyer', null= True)
	# picture = models.FileField(blank=True)
	picture_url = models.CharField(blank=True, max_length=256, default="http://vector-magz.com/wp-content/uploads/2013/11/question-mark-icon2.png")
	isSold = models.BooleanField(default=False)
	creationDate = models.DateField(auto_now_add=True)
	endBidDate = models.DateField(blank=True, null=True)
	boughtDate = models.DateField(blank=True, null= True)
	buyItNow = 'BUY'
	bid = 'BID'
	bidOrBuyItNow = 'BIDBUY'
	SELLING_CHOICES = (
		(buyItNow, 'Buy It Now'),
		(bid, 'Bid'),
		(bidOrBuyItNow, 'Bid or Buy It Now'))
	sellingChoice = models.CharField(max_length=22, choices=SELLING_CHOICES, default=buyItNow)	

	CATEGORY_CHOICES = (('Electronics','Electronics'), ('Furniture','Furniture'), ('Clothing','Clothing'),\
	 ('Kitchen','Kitchen'), ('Sports','Sports'), ('Books','Books'), ('Games','Games'), ('Toys','Toys'), ('Beauty','Beauty'), \
	 ('Outdoors','Outdoors'), ('Other','Other'))
	category = models.CharField(max_length=22, choices=CATEGORY_CHOICES, default = 'Other')

	bidInfo = models.ManyToManyField(BiddingInfo, blank=True, null=True)
	numReviews = models.IntegerField(default=0)
	sumStars = models.IntegerField(default=0)	
	numStarRequests = models.IntegerField(default=0)

	def __unicode__(self):
		return self.title

	def __hash__(self):
		return hash(self.id)

	def __eq__(self, other):
	 	return self.id == other.id

	def __cmp__(self, other):
		return __cmp__(self.id, other.id)

class ViewedItem(models.Model):
	item = models.ForeignKey(Item)
	viewedDate = models.DateTimeField(auto_now_add = True)

	class Meta:
		ordering = ['viewedDate']

	def __unicode__(self):
		return self.item.title

class UserProfile(models.Model):
	user = models.OneToOneField(User)
	viewed = models.ManyToManyField(ViewedItem, blank=True)
	accessToken = models.CharField(max_length=200, blank=True)
	publishableKey = models.CharField(max_length=200, blank=True)
	stripeId = models.CharField(max_length=200, blank=True)
	address = models.CharField(max_length=40)
	state = localflavor.us.models.USStateField()
	city = models.CharField(max_length=40)
	zipcode = localflavor.us.models.USZipCodeField()

	def __unicode__(self):
		return self.user.first_name + " " + self.user.last_name

class Comment(models.Model):
	text = models.CharField(max_length=200)
	commenter = models.ForeignKey(User)
	item = models.ForeignKey(Item)
	date = models.DateTimeField(auto_now_add = True)

	class Meta:
		ordering = ['date']

	def __unicode__(self):
		return self.text
