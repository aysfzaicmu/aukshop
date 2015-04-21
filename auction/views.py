from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest
from django.contrib.auth.tokens import default_token_generator
from django.core.urlresolvers import reverse
from django.core import serializers
from django.http import HttpResponse

from django.core.exceptions import ObjectDoesNotExist
# Decorator to use built-in authentication system
from django.contrib.auth.decorators import login_required
# Used to create and manually log in a user
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.core.mail import send_mail
from django.http import Http404
import os
import json
# Django transaction system so we can use @transaction.atomic
from django.db import transaction
import datetime
from datetime import date

from auction.models import *
from auction.forms import *
from time import strftime, localtime
import stripe
import requests
from util import *
from decimal import *
from auction.s3 import s3_upload, s3_delete
import paypalrestsdk
import logging
from paypalrestsdk import Payout, ResourceNotFound


messageDict = {'0' : 'You won a bid on an item',
                '1' : 'You sucessfully bid on an item',
                '2' : 'You sucessfully uploaded an item',
                '3' : 'Your email has been sent',
                '4' : 'You successfully paid for an item',
                '5' : 'Your payment was unsuccesful. Please try again or contact our Customer Service'
              }

#Loads the homepage
@login_required
def home(request):
    if request.method == 'GET':
        scope = request.GET.get('scope', '')
        code = request.GET.get('code', '')
        if scope != '' and code != '':
            return authentication(request, scope, code)

    context = {}
    stripe.api_key = 'sk_test_BQokikJOvBiI2HlWgH4olfQ2'
    #print(stripe.Account.retrieve('acct_15ne1rIzA8r8Audf'))
    #print(stripe.Account.retrieve('acct_15nzVjIUICJ4BUZz'))

    if request.method == 'GET':
        context['form'] = SearchForm()
        loggedInWon = bidCheck(request)
        if loggedInWon:
            context['message'] = messageDict['0']
    user = request.user
    allItems = Item.objects.filter(isSold=False).exclude(seller=user)
    userProfile = UserProfile.objects.get(user=user)
    #print('Stripe Id:  ' + userProfile.stripeId)
    recentlyViewed = getRecentlyViewed(userProfile)
    #print('Recently Viewed:')
    #print(recentlyViewed)
    context['recentlyViewed'] = recentlyViewed
    subsetOfAllItems = []

    #print('All stripe charges: ')
    stripe.api_key = 'sk_test_BQokikJOvBiI2HlWgH4olfQ2'
    #print(stripe.Charge.all())
    #print(stripe.Account.all())
    for item in allItems:
        isSeen = False
        for rItem in recentlyViewed:
            if rItem.item.id == item.id:
                print "found same"
                isSeen = True
                break
        if not isSeen:
            subsetOfAllItems.append(item)
    context['items'] = subsetOfAllItems
    if request.method == 'GET':
        messageId = request.GET.get('message', '')
        if messageId != '':
            context['message'] = messageDict[str(messageId)]
        return render(request, 'auction/shoppingHome.html', context)

    form = SearchForm(request.POST)
    if not form.is_valid():
        #Error handling
        context['form'] = form
        return render(request, 'auction/shoppingHome.html', context)

    context = search(context, form, user, subsetOfAllItems)
    return render(request, 'auction/searchResults.html', context)


#Loads a user's profile
@login_required
def show_category(request, id):
    context = {}
    items = Item.objects.filter(isSold=False).exclude(seller= request.user)
    items = items.filter(category = id)

    context['items'] = items
    context['form'] = SearchForm()
    context['id'] = id
    if request.method == 'GET':
        return render(request, 'auction/show_category.html', context)
    #Search was made
    form = SearchForm(request.POST)
    if not form.is_valid():
        #Error handling
        context['form'] = form
        return render(request, 'auction/shoppingHome.html', context)
    context = search(context, form, request.user, items)
    return render(request, 'auction/searchResults.html', context)

#Loads a user's profile
@login_required
def profile(request, id):
    user = get_object_or_404(User, id__exact = id)

    userProfile = UserProfile.objects.get(user = user)
    context = {}
    context['userProfile'] = userProfile
    items = Item.objects.filter(isSold=False).filter(seller=user)
    context['items'] = items
    loggedInUser = request.user
    if loggedInUser == user:
        context['buttons'] = 'True'
    else:
        context['buttons'] = 'False'
    return render(request, 'auction/profile.html', context)

#Loads the product page
@login_required
def productInfo(request, id):
    item = get_object_or_404(Item, id__exact = id)

    context = {}
    if item.isSold:
        context['error'] = 'This item has already been bought'
        return render(request, 'auction/error.html', context)
    context['item'] = item
    user = request.user
    #How to call the equals defined in models
    if item.seller == user:
        return render(request, 'auction/error.html', \
        {'error': 'Trying to buy a product that you are selling. if you would like to' + \
        ' view the product go to your profile and click on the View Inventory button'})
    userProfile = UserProfile.objects.get(user=user)
    viewedItem = ViewedItem(item=item)
    viewedItem.save()
    toBeRemoved = userProfile.viewed.filter(item=item)
    for toRemove in toBeRemoved:
        userProfile.viewed.remove(toRemove)
    userProfile.viewed.add(viewedItem)
    userProfile.save()
    context['comments'] = Comment.objects.filter(item=item).reverse()
    if item.numStarRequests == 0:
        context['notStars'] = 5
    else:
        context['notStars'] = 5 - item.sumStars / item.numStarRequests
    if request.method == 'GET':
        form = CommentForm()
        context['form'] = form
        return render(request, 'auction/product.html', context)

    #Made a commment on product
    form = CommentForm(request.POST)
    if not form.is_valid():
        context['form'] = form
        return render(request, 'auction/product.html', context)

    comment = form.cleaned_data['review']
    newComment = Comment(text = comment, commenter=user, item=item)
    item.numReviews = item.numReviews + 1
    item.save()
    context['item'] = item
    newComment.save()
    context['comments'] = Comment.objects.filter(item=item).reverse()
    context['form'] = CommentForm()
    return render(request, 'auction/product.html', context)

@login_required
def bid(request, id):
    context = {}
    item = get_object_or_404(Item, id__exact = id)
    minBid = item.bidPrice
    if not minBid or item.isSold or item.endBidDate < date.today():
        context['error'] = 'Malicious HTTP Request'
        return render(request, 'auction/error.html', context)

    context['message'] = 'You must bid more than $'
    context['minBid'] = minBid
    context['itemid'] = id
    item = Item.objects.get(id__exact = id)



    currentUserBids = item.bidInfo.filter(user = request.user)
    print "in bid in views"
    currentWinner = None

    for bidinfo in currentUserBids:
        if bidinfo.amount == item.bidPrice:
            currentWinner = bidinfo.user

    if currentWinner == request.user:
        context['isWinningMessage'] = "YOU'RE WINNING!"
    else:
        context['isWinningMessage'] = ""


    if request.method == 'GET':
        context['form'] = BidForm()
        context['item'] = item
        print context['form']
        return render(request, 'auction/submitBid.html', context)


    form = BidForm(request.POST)
    context['form'] = form
    if not form.is_valid():
        return render(request, 'auction/submitBid.html', context)
    
    bid = form.cleaned_data['bid']
    if bid < item.bidPrice:
        return render(request, 'auction/submitBid.html', context)

    biddingInfo = BiddingInfo(user = request.user, amount = bid)
    biddingInfo.save()

    item.bidInfo.add(biddingInfo)
    item.bidPrice = bid
    item.save()
    
    context['form'] = BidForm()
    context['itemid'] = id
    item = Item.objects.get(id__exact = id)
    context['item'] = item
    context['minBid'] = bid
    context['isWinningMessage'] = "YOU'RE WINNING!"
    return render(request, 'auction/submitBid.html', context)
    #Give confirmation for the bid. Dont wnat to send email because then too many emails
    #return redirect(reverse('home') + '?message=1')


#Called when a new person makes account
#Error cases: username not entered, password not entered, confirmed password not entered,
#             Check that password and confirm password are the same, Check that username is unique
#             first name not entered, last name not entered, age is non numeric, bio exists
@transaction.atomic
def register(request):
    context = {}
    # Just display the registration form if this is a GET request
    if request.method == 'GET':
        context['form'] = RegistrationForm()
        return render(request, 'auction/register.html', context)

    form = RegistrationForm(request.POST)
    context['form'] = form

    if not form.is_valid():
        return render(request, 'auction/register.html', context)

    # Creates the new user from the valid form data
    new_user = User.objects.create_user(username=form.cleaned_data['username'], \
                                        password=form.cleaned_data['password1'],
                                        email = form.cleaned_data['email'],\
                    first_name = form.cleaned_data['firstName'], \
                    last_name = form.cleaned_data['lastName'])

    #Initially set the user as inactive so cant login until click on email link
    new_user.is_active = False
    new_user.save()

    userProfile = UserProfile(user = new_user, address=form.cleaned_data['address'], state=form.cleaned_data['state'], \
                            zipcode=form.cleaned_data['zipcode'], city=form.cleaned_data['city'])
    userProfile.save()

    # Generate a one-time use token and an email message body
    token = default_token_generator.make_token(new_user)

    #Create and send email
    email_body = """
        Welcome to Aukshop. Please click the link below to
        verify your email address and complete the registration of your account:
        http://%s%s
        """ % (request.get_host(),
    reverse('confirm', args=(new_user.username, token)))
    send_mail(subject='Verify your email address', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[new_user.email])
    context['email'] = form.cleaned_data['email']
    return render(request, 'auction/needsConfirmation.html', context)

#Called when user clicks on the link in the email
@transaction.atomic
def confirmRegistration(request, username, token):
    user = get_object_or_404(User, username=username)
    # Send 404 error if token is invalid
    if not default_token_generator.check_token(user, token):
        raise Http404
    # Otherwise token was valid, activate the user.
    user.is_active = True
    user.save()
    return render(request, 'auction/confirmed.html', {})

#Called when click on the forgot password link
def forgotPassword(request):
    context = {}
    if request.method == 'GET':
        context['form'] = ForgotPasswordForm()
        return render(request, 'auction/forgotPassword.html', context)

    #Request is a POST so sending back info in form
    form = ForgotPasswordForm(request.POST)
    context['form'] = form
    if not form.is_valid():
        return render(request, 'auction/forgotPassword.html', context)

    username = form.cleaned_data['username']
    user = User.objects.get(username=username)

    token = default_token_generator.make_token(user)

    #Create and send email
    email_body = """
        Please click the link below to change your password:
        http://%s%s
        """ % (request.get_host(),
    reverse('confirmPass', args=(username, token)))
    email = form.cleaned_data['email']
    send_mail(subject='Password Reset', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[email])
    context['email'] = email
    user.is_active = False
    return render(request, 'auction/needsPasswordReset.html', context)

def forgotUsername(request):
    context = {}
    if request.method == 'GET':
        context['form'] = ForgotUsernameForm()
        return render(request, 'auction/forgotUsername.html', context)

    form = ForgotUsernameForm(request.POST)
    context['form'] = form
    if not form.is_valid():
        return render(request, 'auction/forgotUsername.html', context)

    password = form.cleaned_data['password']
    email = form.cleaned_data['email']
    users = User.objects.filter(email=email)
    for u in users:
        if u.check_password(password):
            email_body = """ Your username %s""" % (u.username)
            send_mail(subject='Your username', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[email])    
            return render(request, 'auction/confirmUsername.html', {'email' : email})
    return render(request, 'auction/error.html', {'error': 'Malicious HTTP Request'})

#Called when user clicks on link in email
@transaction.atomic
def confirmPasswordReset(request, username, token):
    if request.method == 'GET':
        context = {}
        context['form'] = ChangePasswordForm()
        return render(request, 'auction/newPassword.html', context)

    user = get_object_or_404(User, username=username)
    # Send 404 error if token is invalid
    if not default_token_generator.check_token(user, token):
        raise Http404

    form = ChangePasswordForm(request.POST)
    if not form.is_valid():
        return render(request, 'auction/newPassword/html', {})

    newPassword = form.cleaned_data['password1']
    user.set_password(newPassword)
    #Now allow the user to login
    user.is_active = True
    user.save()
    return render(request, 'auction/confirmedPassword.html', {})

#Called when user wants to add an item
@login_required
@transaction.atomic
def add_item(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = AddingItemForm()
        return render(request, 'auction/registerProduct.html', context)

    form = AddingItemForm(request.POST,request.FILES)
    
    # Validates the form.
    if not form.is_valid():
        context['form'] = form
        return render(request, 'auction/registerProduct.html', context)

    user = request.user
    userProfile = UserProfile.objects.get(user = user)

    TWOPLACES = Decimal(10) ** -2
    price = form.cleaned_data['price']
    if price:
        price = price.quantize(TWOPLACES)
        print(price)
    bidPrice = form.cleaned_data['bidPrice']
    if bidPrice:
        bidPrice = bidPrice.quantize(TWOPLACES)
    new_Item = Item(seller = request.user, description = form.cleaned_data['description'], bidPrice = bidPrice, \
                    endBidDate = form.cleaned_data['endBidDate'], \
                    title = form.cleaned_data['title'], sellingChoice = form.cleaned_data['sellingChoice'],\
                    price = price)
    

    new_Item.save()

    if form.cleaned_data['picture']:
        url = s3_upload(form.cleaned_data['picture'], new_Item.id)
        new_Item.picture_url = url
        new_Item.save()

    #Send email that they registered an item and but some confimation on the redirect page that ell them that they have uploaded an item
    email = user.email
    email_body = """
        You have put %s for sale
        """ % (new_Item.title)
    send_mail(subject='You have put up for sale an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[email])    
    return redirect(reverse('home') + '?message=2')

@login_required
def transactionSellerHistory(request):
    user = request.user
    sold = Item.objects.filter(isSold=True).filter(seller=user)
    return render(request, 'auction/transactionHistory.html', {'items': sold})

@login_required
def transactionBuyerHistory(request):
    user = request.user
    bought = Item.objects.filter(isSold=True).filter(buyer=user)
    return render(request, 'auction/transactionHistory.html', {'items': bought})

@login_required
def viewInventory(request):
    user = request.user
    notBought = Item.objects.filter(isSold=False).filter(seller=user)
    return render(request, 'auction/inventory.html', {'items': notBought})

@login_required
@transaction.atomic
def finishPayment(request):
    print "got id " +  request.GET['id']
    sellingchoice = request.GET['sellingchoice']
    itemid = request.GET['id']
    item = Item.objects.get(id__exact = itemid)
    if sellingchoice == "buy":
        value = item.price
    else:
        value = item.finalPrice
    paymentId = request.GET['paymentId']
    token = request.GET['token']
    payerId = request.GET['PayerID']
    payment = paypalrestsdk.Payment.find(paymentId)
    payment.execute({"payer_id": payerId})
    batchid = itemid + str(1)
    print "below are details after payment"
    print payment
    payout = Payout({
    "sender_batch_header": {
        "sender_batch_id": batchid,
        "email_subject": "You have a payment"
    },
    "items": [
        {
            "recipient_type": "EMAIL",
            "amount": {
                "value": 2.00,
                "currency": "USD"
            },
            "receiver": "aysfzai-buyer@hotmail.com",
            "note": "Thank you.",
            "sender_item_id": str(itemid),
        }
    ]
})

    if payout.create(sync_mode=True):
        print("payout[%s] created successfully" % (payout.batch_header.payout_batch_id))
        item = Item.objects.get(id__exact = itemid)
        item.buyer = request.user
        item.finalPrice = value
        item.boughtDate = date.today()
        item.isSold = True
        item.save()
        print "successfully updated " + item.title
        return redirect(reverse('home') + "?message=4")

    else:
        print(payout.error)
        return redirect(reverse('home') + "?message=5")

@login_required
@transaction.atomic
def paywithPayPal(request,id,sellingchoice):
    userProfile = UserProfile.objects.get(user = request.user)
    context = {}
    context['userProfile'] = userProfile
    item = Item.objects.get(id__exact = id)
    if sellingchoice == "buy":
        total = item.price
    else:
        total = item.finalPrice

    paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
  "client_secret": os.environ.get('PAYPAL_SECRET_KEY')})

    payment = paypalrestsdk.Payment({
  "intent": "sale",
  "payer": {
    "payment_method": "paypal" },
  "redirect_urls": {
    "return_url": "http://localhost:8000/finishPayment?id=" + id + "&sellingchoice=" + sellingchoice,
    "cancel_url": "https://devtools-paypal.com/guide/pay_paypal/python?cancel=true" },

  "transactions":[{
    "amount": {
    "total": "12",
    "currency": "USD" },
    "description": "creating a payment"}]})

    approval_url = ""
    context = {}
    context['item'] = item
    if payment.create():
        print("Payment created successfully")
        print payment

        print payment['links']
        links = payment['links']
        for link in links:
            if link['rel'] == 'approval_url':
                approval_url = link['href']
                context['link'] = approval_url
    else:
        print(payment.error)
    print approval_url

    # payment = paypalrestsdk.Payment.find("PAY-46562054D3033294DKUYIGWQ")
    # payment.execute({"payer_id": "ELGV6XMVJU6QU"})
    # print "below are details after payment"
    # print payment
#     payout = Payout({
#     "sender_batch_header": {
#         "sender_batch_id": "batch_1",
#         "email_subject": "You have a payment"
#     },
#     "items": [
#         {
#             "recipient_type": "EMAIL",
#             "amount": {
#                 "value": 0.99,
#                 "currency": "USD"
#             },
#             "receiver": "aysfzai-buyer@hotmail.com",
#             "note": "Thank you.",
#             "sender_item_id": "item_1"
#         }
#     ]
# })

#     if payout.create(sync_mode=True):
#         print("payout[%s] created successfully" % (payout.batch_header.payout_batch_id))
#     else:
#         print(payout.error)

    return render(request, 'auction/payment.html', context)

    
@transaction.atomic
def makePayment(request):
    # Set your secret key: remember to change this to your live secret key in production # See your keys here https://dashboard.stripe.com/account/apikeys 
    if request.method == 'GET':
        return render(request, 'auction/error.html', {})
    stripe.api_key = 'sk_test_BQokikJOvBiI2HlWgH4olfQ2'
    # Get the credit card details submitted by the form 
    token = request.POST['stripeToken'] 
    price = request.POST['price']
    amount = int(float(price)*100)
    itemId = request.POST['id']
    item = get_object_or_404(Item, id=itemId).select_for_update()
    if item.isSold:
        return render(request, 'auction/error.html', {'error': 'This item has already been bought'})
    # Create the charge on Stripe's servers - this will charge the user's card 
    try: 
        charge = stripe.Charge.create( amount=amount, # amount in cents, again 
        currency="usd", source=token, description=str(request.user) + ' bought ' + item.title)
    except stripe.CardError, e: # The card has been declined 
        #Need to do some error handling here
        pass
    
    #Mark that item got sold
    #Send email confirmation
    #Redriect to home page
    #show confirmation
    user = request.user
    buyerProfile = UserProfile.objects.get(user=user)
    item.isSold = True
    item.finalPrice = item.price
    item.boughtDate = strftime("%Y-%m-%d", localtime())
    item.buyer = user
    if item.buyer == item.seller:
        raise ValueError
    item.save()
    email_body = """
        You have bought %s
        """ % (item.title)
    
    send_mail(subject='You bought an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[user.email])
    seller = item.seller 
    sellerEmail = seller.email
    email_body = """
        You have sold %s. Please send it to %s at %s \n %s, %s %s
        """ % (item.title, user, buyerProfile.address, buyerProfile.city, buyerProfile.state, buyerProfile.zipcode)
    send_mail(subject='You sold an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[sellerEmail])
    #For each user profile remove the item from recently viewed
    removeItemFromRecentlyViewed(item)
    # recipient = stripe.Recipient.create(
    #     name=item.seller,
    #     type="individual",
    #     email=sellerEmail,
    #     bank_account=sellerProfile.accessToken
    # )
    # print(recipient)
    
    sellerProfile = UserProfile.objects.get(user=seller)
    print('stripe id:' + sellerProfile.stripeId)
    # stripe.Transfer.create(
    #     amount=amount,
    #     currency='usd',
    #     destination=sellerProfile.stripeId,
    #     source_transaction=charge['id'],
    #     description="test"
    # )

    return redirect(reverse('home') + "?message=1")
    

# Set your secret key: remember to change this to your live secret key in production
# See your keys here https://dashboard.stripe.com/account/apikeys
# stripe.api_key = "sk_test_BQokikJOvBiI2HlWgH4olfQ2"

# # Get the credit card details submitted by the form
# token = request.POST['stripeToken']

# # Create a Customer
# customer = stripe.Customer.create(
#     source=token,
#     description="payinguser@example.com"
# )

# # Charge the Customer instead of the card
# stripe.Charge.create(
#     amount=1000, # in cents
#     currency="usd",
#     customer=customer.id
# )

# # Save the customer ID in your database so you can use it later
# save_stripe_customer_id(user, customer.id)

# # Later...
# customer_id = get_stripe_customer_id(user)

# stripe.Charge.create(
#     amount=1500, # $15.00 this time
#     currency="usd",
#     customer=customer_id
# )

def authentication(request, scope, code):
    print('Inside authentication')
    data   = {'grant_type': 'authorization_code',
            'client_id': 'ca_5zdI88hiyw23dfEoLYf3qsYTz86aoZSj',
            'client_secret': 'sk_test_x61AEqhtpgOTpOSpVBFVjQ3t',
            'code': code
           }
    url = 'https://connect.stripe.com/oauth/token'
    resp = requests.post(url, params=data)

    # Grab access_token (use this as your user's API key)
    response = resp.json()
    print(response)
    token = response['access_token']
    publishableKey = response['stripe_publishable_key']
    userId = response['stripe_user_id']
    user = request.user
    userProfile = UserProfile.objects.get(user=user)
    userProfile.accessToken = token
    userProfile.publishableKey = publishableKey
    userProfile.stripeId = userId
    userProfile.save()
    print('stripe Id:' + userProfile.stripeId)
    return redirect(reverse('home'))


#need to take into account if the item is sold
def update_bid(request):
    bidInfo = {}
    itemid = request.GET['itemid']
    item = Item.objects.get(id__exact = itemid)
    bidInfo['bidPrice'] = str(item.bidPrice)

    currentUserBids = item.bidInfo.filter(user = request.user)
    print len(currentUserBids)
    currentWinner = None

    for bidinfo in currentUserBids:
        if bidinfo.amount == item.bidPrice:
            currentWinner = bidinfo.user

    if currentWinner == request.user:
        bidInfo['message'] = "YOU'RE WINNING!"
    else:
        bidInfo['message'] = ""

    # response_text = json.dumps(bidInfo)
    # return HttpResponse(response_text, content_type='application/json')
    if 'itemid' in request.GET:
        itemid = request.GET['itemid']
        item = get_object_or_404(Item, id__exact = itemid)
        TWOPLACES = Decimal(10) ** -2
        bidPrice = item.bidPrice
        price = bidPrice.quantize(TWOPLACES)
        bidInfo['bidPrice'] = str(price)
        response_text = json.dumps(bidInfo)
        return HttpResponse(response_text, content_type='application/json')
    return HttpResponse('Malicious HTTP Request', content_type='application/json')

@login_required
def rate(request):
    if 'numStars' in request.POST and 'id' in request.POST:
        numStars = int(request.POST['numStars'])
        itemId = request.POST['id']
    
        item = get_object_or_404(Item, id=itemId)
        if numStars < 1 or numStars > 5:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        if item.isSold or item.seller == request.user:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        item.sumStars = item.sumStars + numStars
        item.numStarRequests = item.numStarRequests + 1
        item.save()
        newRating = item.sumStars / (item.numStarRequests * 1.0)
        responseText = json.dumps(newRating)
        return HttpResponse(responseText, content_type='application/json')
    return HttpResponse('Malicious HTTP Request', content_type='application/json')

@login_required
def sendEmail(request, sellerId, itemTitle):
    context = {}
    if request.method == 'GET':
        context['form'] = EmailForm(initial = {'subject': 'Question about ' + itemTitle})
        return render(request, 'auction/email.html', context)

    if len(Item.objects.filter(title=itemTitle)) == 0:
        return render(request, 'auction/error.html', {'error': 'You changed a hidden field'})
    sellerId = int(sellerId)
    try:
        seller = User.objects.get(id=sellerId)
    except:
        return render(request, 'auction/error.html', {'error': 'You changed a hidden field'})
    form = EmailForm(request.POST)
    if not form.is_valid():
        context['form'] = form
        context['sellerId'] = sellerId
        context['itemTitle'] = itemTitle
        return render(request, 'auction/email.html', context)

    subject = form.cleaned_data['subject']
    body = form.cleaned_data['body']
    send_mail(subject=subject, message= str(request.user) + '( ' + str(request.user.email) + ') would like to know: ' + body, \
        from_email='aukshopteam@gmail.com', recipient_list=[seller.email])
    #Give confimration message
    print('Sent email')
    return redirect(reverse('home') + '?message=3')

@login_required
@transaction.atomic
def editItem(request, id):
    context = {}
    try:
        itemToBeEdited = Item.objects.select_for_update().get(id=int(id))
    except:
        return render(request, 'auction/error.html', {'error': 'Item with that id does not exist'})
    if request.user != itemToBeEdited.seller or itemToBeEdited.isSold:
        return render(request, 'auction/error.html', {'error' : 'Not allowed to edit this item'})
    if itemToBeEdited.sellingChoice == 'BID' or itemToBeEdited.sellingChoice == 'BIDBUY':
        context['bid'] = 'True'
    else:
        context['bid'] = 'False'
    if request.method == 'GET':
        context['form'] = EditItemForm(instance=itemToBeEdited)
        return render(request, 'auction/editItem.html', context)
    
    form = EditItemForm(request.POST, instance=itemToBeEdited)

    if not form.is_valid():
        context ['form'] = form
        return render(request, 'auction/editItem.html', context)
    if itemToBeEdited.isSold:
        return render(request, 'auction/error.html', {'error' : 'Not allowed to edit this item'})
    form.save()
    return redirect(reverse('inventory'))

def submitBid(request):
    if request.method == 'POST' and 'itemid' in request.POST and 'bidAmount' in request.POST:
        itemId = request.POST['itemid']
        bidAmount = request.POST['bidAmount']
        item = get_object_or_404(Item, id=itemId)
        if item.isSold or item.sellingChoice == 'BUY' or item.seller == request.user:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        currentUserBids = item.bidInfo.filter(user = request.user)

        
        biddingInfo = BiddingInfo(user = request.user, amount = bidAmount)
        biddingInfo.save()
        bidInfo = {}
        bidInfo['message'] = "YOU'RE WINNING!"
        item.bidInfo.add(biddingInfo)
        item.bidPrice = bidAmount
        item.save()
        bidInfo['bidPrice'] = str(bidAmount)
        response_text = json.dumps(bidInfo)
        return HttpResponse(response_text, content_type='application/json')
    return HttpResponse('Malicious HTTP Request', content_type='application/json')

def pay(request):
    token = request.GET['stripeToken'] 
    price = request.GET['price']
    amount = int(float(price)*100)
    itemId = request.GET['id']
    item = get_object_or_404(Item, id=itemId).select_for_update()
    user = request.user
    buyerProfile = UserProfile.objects.get(user=user)
    # paypalrestsdk.configure({
    #     "mode": "sandbox", # sandbox or live
    #     "client_id": "Ab0SgjqwSB9h88oGnvvoA5-pLOhlLalh50i3ZJ_uohQ13OYoBnbsEQ8bIknlbt7AYOvQjz2uHf_61hh5",
    #     "client_secret": "EH5BZ30PMGx0QIVg21A1dND_Qn6vYMUZrXc02h9CoLtvF7hHYiethjT-8rR3L-LQvEVGWIEwLvSyAUw9" })
    # data   = {'X-PAYPAL-SECURITY-USERID': 'akhilprakash_api1.yahoo.com',
    #         'X-PAYPAL-SECURITY-PASSWORD': 'GU7979J2Y7E83YCC',
    #         'X-PAYPAL-SECURITY-SIGNATURE': 'AezEgy1qEwOnYyN0WO5cjdPMHua.AC1S4q3QWyYGSRvcFuAl5UsCsP4I',
    #         'X-PAYPAL-APPLICATION-ID' : 'APP-80W284485P519543T',
    #         'X-PAYPAL-REQUEST-DATA-FORMAT' : 'JSON',
    #         'X-PAYPAL-RESPONSE-DATA-FORMAT' : 'JSON',
    #         {
    #             "actionType":"PAY",    # Specify the payment action
    #             "currencyCode":"USD",  #The currency of the payment
    #             "receiverList":{"receiver":[{
    #             "amount":"1.00",                    # The payment amount
    #             "email":"akhilprakash-facilitator@yahoo.com"}]}  # The payment Receiver's email address
    #         },

    #         # Where the Sender is redirected to after approving a successful payment
    #         "returnUrl":"http://Payment-Success-URL",

    #         #Where the Sender is redirected to upon a canceled payment
    #         "cancelUrl":"http://Payment-Cancel-URL",
    #         "requestEnvelope":{
    #             "errorLanguage":"en_US",    # Language used to display errors
    #             "detailLevel":"ReturnAll"   # Error detail level
    #             }
    #         }
    # url = ' https://svcs.sandbox.paypal.com/AdaptivePayments/Pay'

    resp = requests.post(url, params=data)

    # Grab access_token (use this as your user's API key)
    response = resp.json()




    item.isSold = True
    item.finalPrice = item.price
    item.boughtDate = strftime("%Y-%m-%d", localtime())
    item.buyer = user
    if item.buyer == item.seller:
        raise ValueError
    item.save()
    email_body = """
        You have bought %s
        """ % (item.title)
    
    send_mail(subject='You bought an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[user.email])
    seller = item.seller 
    sellerEmail = seller.email
    email_body = """
        You have sold %s. Please send it to %s at %s \n %s, %s %s
        """ % (item.title, user, buyerProfile.address, buyerProfile.city, buyerProfile.state, buyerProfile.zipcode)
    send_mail(subject='You sold an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[sellerEmail])
    #For each user profile remove the item from recently viewed
    removeItemFromRecentlyViewed(item)
    # recipient = stripe.Recipient.create(
    #     name=item.seller,
    #     type="individual",
    #     email=sellerEmail,
    #     bank_account=sellerProfile.accessToken
    # )
    # print(recipient)
    
    sellerProfile = UserProfile.objects.get(user=seller)
    print('stripe id:' + sellerProfile.stripeId)
    # stripe.Transfer.create(
    #     amount=amount,
    #     currency='usd',
    #     destination=sellerProfile.stripeId,
    #     source_transaction=charge['id'],
    #     description="test"
    # )

    return redirect(reverse('home') + "?message=1")

def about(request):
    return render(request, 'auction/about.html', {})
