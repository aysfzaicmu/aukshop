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
from datetime import date, timedelta

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
import random
import ConfigParser


messageDict = {'0' : 'You won a bid on an item',
                '1' : 'You sucessfully bid on an item',
                '2' : 'You sucessfully uploaded an item',
                '3' : 'Your email has been sent',
                '4' : 'You successfully paid for an item',
                '5' : 'Your payment was unsuccesful. Please try again or contact our Customer Service'
              }

config = ConfigParser.ConfigParser()
config.read("config.ini")

#Loads the homepage
@login_required
def home(request):
    context = {}

    if request.method == 'GET':
        context['form'] = SearchForm()
        #check for bids
        loggedInWon = bidCheck(request)
        if loggedInWon:
            #update messsage
            context['message'] = messageDict['0']
            context['good_message'] = True
    user = request.user
    allItems = Item.objects.filter(isSold=False).exclude(seller=user)
    try:
        userProfile = UserProfile.objects.get(user=user)
    except:
        return render(request, 'auction/error.html', {"error": "Malicious HTTP request"})
    recentlyViewed = getRecentlyViewed(userProfile)
    context['recentlyViewed'] = recentlyViewed
    subsetOfAllItems = []

    for item in allItems:
        isSeen = False
        for rItem in recentlyViewed:
            if rItem.item.id == item.id:
                isSeen = True
                break
        if not isSeen:
            subsetOfAllItems.append(item)
    context['items'] = subsetOfAllItems
    if request.method == 'GET':
        messageId = request.GET.get('message', '')
        if messageId in messageDict:
            context['message'] = messageDict[messageId]
            if messageId == '5':
                context['bad_message'] = True
        return render(request, 'auction/shoppingHome.html', context)

    form = SearchForm(request.POST)
    if not form.is_valid():
        #Error handling
        context['form'] = form
        return render(request, 'auction/shoppingHome.html', context)

    context = search(context, form, user, subsetOfAllItems)
    return render(request, 'auction/searchResults.html', context)

@login_required
def showCategory(request, id):
    context = {}
    items = Item.objects.filter(isSold=False).filter(category=id).exclude(seller= request.user)

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
    try:
        userProfile = UserProfile.objects.get(user = user)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})
    context = {}
    context['userProfile'] = userProfile
    loggedInUser = request.user
    if loggedInUser == user:
        context['buttons'] = 'True'
    else:
        context['buttons'] = 'False'
        items = Item.objects.filter(isSold=False).filter(seller=user)
        context['items'] = items
    data = Item.objects.filter(isSold=True).filter(seller=user)
    #calcualte how many items this user has sold in 7 day intervals
    values = []
    values.append(data.filter(boughtDate__lt = date.today()).filter(boughtDate__gte = date.today() - timedelta(days=7)).count())
    values.append(data.filter(boughtDate__lt = date.today() - timedelta(days=7)).filter(boughtDate__gte = date.today() - timedelta(days=14)).count())
    values.append(data.filter(boughtDate__lt = date.today() - timedelta(days=14)).filter(boughtDate__gte = date.today() - timedelta(days=21)).count())
    values.append(data.filter(boughtDate__lt = date.today() - timedelta(days=21)).filter(boughtDate__gte = date.today() - timedelta(days=28)).count())
    context['values'] = values
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
    if item.seller == user:
        return render(request, 'auction/error.html', \
        {'error': 'Trying to buy a product that you are selling. if you would like to' + \
        ' view the product go to your profile and click on the View Inventory button'})
    try:
        userProfile = UserProfile.objects.get(user=user)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})
    #Make a viewedItem and if item is already in recently viewed update it
    viewedItem = ViewedItem(item=item)
    viewedItem.save()
    toBeRemoved = userProfile.viewed.filter(item=item)
    for toRemove in toBeRemoved:
        userProfile.viewed.remove(toRemove)
    userProfile.viewed.add(viewedItem)
    userProfile.save()

    context['comments'] = Comment.objects.filter(item=item).reverse()
    #make token for pyament link
    token = default_token_generator.make_token(user)
    context['token'] = token
    context['hashSellingChoice'] = myHash(item.id, 'buy')

    #calculate rating for item
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
    #Put most recent comments at the top
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
    item = get_object_or_404(Item, id__exact = id)



    currentUserBids = item.bidInfo.filter(user = request.user)
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
        return render(request, 'auction/submitBid.html', context)
    #IF there is a POST requet then that is bad
    context['error'] = 'Malicious HTTP request'
    return render(request, 'auction/error.html', context)


#Called when a new person makes account
#Error cases: username not entered, password not entered, confirmed password not entered,
#             Check that password and confirm password are the same, Check that username is unique
#             first name not entered, last name not entered
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
    try:
        user = User.objects.get(username=username)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})

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
            email_body = """ Your username is %s""" % (u.username)
            send_mail(subject='Aukshop username', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[email])    
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
def addItem(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = AddingItemForm()
        return render(request, 'auction/registerProduct.html', context)

    form = AddingItemForm(request.POST,request.FILES)
    
    # Validates the form.
    if not form.is_valid():
        if form.cleaned_data['picture']:
            form.picture = form.cleaned_data['picture']
        context['form'] = form
        return render(request, 'auction/registerProduct.html', context)

    user = request.user
    try:
        userProfile = UserProfile.objects.get(user = user)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})

    #Store the price with two decimal places
    TWOPLACES = Decimal(10) ** -2
    price = form.cleaned_data['price']
    if price:
        price = price.quantize(TWOPLACES)
    bidPrice = form.cleaned_data['bidPrice']
    if bidPrice:
        bidPrice = bidPrice.quantize(TWOPLACES)
    new_Item = Item(seller = request.user, description = form.cleaned_data['description'], bidPrice = bidPrice, \
                    endBidDate = form.cleaned_data['endBidDate'], \
                    title = form.cleaned_data['title'], sellingChoice = form.cleaned_data['sellingChoice'],\
                    price = price, category=form.cleaned_data['category'])

    new_Item.save()

    #upload picture to s3
    if form.cleaned_data['picture']:
        url = s3_upload(form.cleaned_data['picture'], new_Item.id)
        new_Item.picture_url = url
        new_Item.save()

    #Send email that they registered an item and give confirmation message on homepage
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
    if request.method == 'GET' and 'id' in request.GET and 'sellingchoice' in request.GET and \
        'paymentId' in request.GET and 'token' in request.GET and 'PayerID' in request.GET:

        sellingchoice = request.GET['sellingchoice']
        itemid = request.GET['id']
        try:
            item = Item.objects.select_for_update().get(id=itemid)
        except:
            return render(request, 'auction/error.html', {'error': 'Payment did not work'})
        #We know this will not throw and error sicne the regualr expression matches sellingchoice to an int
        sellingchoice = int(sellingchoice)
        if sellingchoice == myHash(itemid, 'buy'):
            total = item.price
        elif sellingchoice == myHash(itemid, 'bid'):
            total = item.finalPrice
        else:
            print('selling choice is wrong')
            return render(request, 'auction/error.html', {'error': 'Malicious HTTP Request'})
        paymentId = request.GET['paymentId']
        token = request.GET['token']
        payerId = request.GET['PayerID']
        try:
            payment = paypalrestsdk.Payment.find(paymentId)
        except paypalrestsdk.exceptions.MissingConfig:
            print('missing config')
            return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})
        payment.execute({"payer_id": payerId})
        #get rid of random nmber at end
        batchid = itemid + str(random.randrange(1, 10000))
        payout = Payout({
        "sender_batch_header": {
            "sender_batch_id": batchid,
            "email_subject": "You have a payment"
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": str(total),
                    "currency": "USD"
                },
                "receiver": "aukshop-seller@hotmail.com", #change reciever to be the seller
                "note": "Thank you.",
                "sender_item_id": str(itemid),
            }
        ]
    })

        if payout.create(sync_mode=True):
            winner = request.user
            item.buyer = winner
            item.finalPrice = total
            item.boughtDate = date.today()      
            item.isSold = True
            item.save()
            removeItemFromRecentlyViewed(item)
            try:
                buyerProfile = UserProfil.objects.get(user=winner)
            except:
                return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})
            email_body = """You have sold %s by bid for $%s. Please send it to %s at \n %s \n %s, %s %s""" % (item.title, item.finalPrice, \
                winner, buyerProfile.address, buyerProfile.city, buyerProfile.state, buyerProfile.zipcode)
            send_mail(subject='Your bid item has been sold', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[item.seller.email])
            return redirect(reverse('home') + "?message=4")
        else:
            print('payout failed')
            return redirect(reverse('home') + "?message=5")
    else:
        return render(request, 'auction/error.html', {'error': 'Payment did not work'})

@login_required
@transaction.atomic
def paywithPayPal(request, id, sellingchoice, token):
    user = request.user
    if not default_token_generator.check_token(user, token):
        print('toek does not match')
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP Request'})
    try:
        userProfile = UserProfile.objects.get(user = user)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP request'})
    context = {}
    context['userProfile'] = userProfile
    try:
        item = Item.objects.select_for_update().get(id__exact = id)
    except:
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP Request'})
    #Know that this will not throw an error since regular expression matches sellingchoice to an int
    sellingchoice = int(sellingchoice)
    if sellingchoice == myHash(item.id, 'buy'):
        total = item.price
    elif sellingchoice == myHash(item.id, 'bid'):
        total = item.finalPrice
    else:
        print('erro in selling choice')
        return render(request, 'auction/error.html', {'error': 'Malicious HTTP Request'})

    paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
  "client_secret": os.environ.get('PAYPAL_SECRET_KEY')})

    payment = paypalrestsdk.Payment({
  "intent": "sale",
  "payer": {
    "payment_method": "paypal" },
  "redirect_urls": {
    "return_url": "http://" + request.get_host() + "/finishPayment?id=" + id + "&sellingchoice=" + str(sellingchoice),
    "cancel_url": "https://devtools-paypal.com/guide/pay_paypal/python?cancel=true" },

  "transactions":[{
    "amount": {
    "total": str(total),
    "currency": "USD" },
    "description": "creating a payment"}]})

    context = {}
    context['item'] = item
    if payment.create():
        links = payment['links']
        for link in links:
            if link['rel'] == 'approval_url':
                approval_url = link['href']
                context['link'] = approval_url
        if approval_url:  
            return redirect(approval_url)
    return redirect(reverse('home') + "?message=5")


#need to take into account if the item is sold
@login_required
@transaction.atomic
def updateBid(request):
    bidInfo = {}
    if 'itemid' in request.GET:
        itemid = request.GET['itemid']
        try:
            item = Item.objects.select_for_update().get(id__exact = itemid)
        except:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        user = request.user
        if item.isSold or item.sellingChoice == 'BUY' or item.seller == user:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        bidInfo['bidPrice'] = str(item.bidPrice)

        currentUserBids = item.bidInfo.filter(user = user)
        currentWinner = None

        for bidinfo in currentUserBids:
            if bidinfo.amount == item.bidPrice:
                currentWinner = bidinfo.user

        if currentWinner == request.user:
            bidInfo['message'] = "YOU'RE WINNING!"
        else:
            bidInfo['message'] = ""

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
        try:
            numStars = int(request.POST['numStars'])
        except ValueError:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        itemId = request.POST['id']
    
        item = get_object_or_404(Item, id=itemId)
        #Error handling
        if numStars < 1 or numStars > 5:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        if item.isSold or item.seller == request.user:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        try:
            numStars = int(numStars)
        except ValueError:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        #Compute new rating and send it back
        item.sumStars = item.sumStars + numStars
        item.numStarRequests = item.numStarRequests + 1
        item.save()
        #do double division
        newRating = item.sumStars / (item.numStarRequests * 1.0)
        responseText = json.dumps(newRating)
        return HttpResponse(responseText, content_type='application/json')
    return HttpResponse('Malicious HTTP Request', content_type='application/json')

@login_required
def sendEmail(request, sellerId, itemTitle):
    context = {}
    if len(Item.objects.filter(title=itemTitle)) == 0:
        return render(request, 'auction/error.html', {'error': 'You changed a hidden field'})
    try:
        seller = User.objects.get(id=sellerId)
    except:
        return render(request, 'auction/error.html', {'error': 'You changed a hidden field'})
    if request.method == 'GET':
        context['form'] = EmailForm(initial = {'subject': 'Question about ' + itemTitle})
        return render(request, 'auction/email.html', context)

    form = EmailForm(request.POST)
    if not form.is_valid():
        context['form'] = form
        context['sellerId'] = sellerId
        context['itemTitle'] = itemTitle
        return render(request, 'auction/email.html', context)

    subject = form.cleaned_data['subject']
    body = form.cleaned_data['body']
    send_mail(subject=subject, message= str(request.user) + '(' + str(request.user.email) + ') would like to know: ' + body, \
        from_email='aukshopteam@gmail.com', recipient_list=[seller.email])
    #Give confimration message
    return redirect(reverse('home') + '?message=3')

@login_required
@transaction.atomic
def editItem(request, id):
    context = {}
    try:
        itemToBeEdited = Item.objects.select_for_update().get(id=id)
    except:
        return render(request, 'auction/error.html', {'error': 'Item with that id does not exist'})
    if request.user != itemToBeEdited.seller or itemToBeEdited.isSold:
        return render(request, 'auction/error.html', {'error' : 'Not allowed to edit this item'})
    if itemToBeEdited.sellingChoice == 'BUY':
        context['buy'] = 'True'
    else:
        context['buy'] = 'False'
    if request.method == 'GET':
        context['form'] = EditItemForm(instance=itemToBeEdited)
        return render(request, 'auction/editItem.html', context)
    form = EditItemForm(request.POST, instance=itemToBeEdited)

    if not form.is_valid():
        context ['form'] = form
        return render(request, 'auction/editItem.html', context)
    if itemToBeEdited.isSold:
        return render(request, 'auction/error.html', {'error' : 'This item has been sold'})
    form.save()
    itemToBeEdited.picture_url = "http://vector-magz.com/wp-content/uploads/2013/11/question-mark-icon2.png"
    itemToBeEdited.save()
    return redirect(reverse('inventory'))

@login_required
@transaction.atomic
def submitBid(request):
    if request.method == 'POST' and 'itemid' in request.POST and 'bidAmount' in request.POST:
        itemId = request.POST['itemid']
        bidAmount = request.POST['bidAmount']
        try:
            item = Item.objects.select_for_update().get(id=itemId)
        except:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        if item.isSold:
            return HttpResponse('Item has been sold', content_type='application/json')
        if item.sellingChoice == 'BUY' or item.seller == request.user:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        try:
            float(bidAmount)
        except ValueError:
            return HttpResponse('Malicious HTTP Request', content_type='application/json')
        #Max bid amount is 10 digits long
        if float(bidAmount) > 99999999.99:
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

def about(request):
    if request.user.is_authenticated():
        return render(request, 'auction/about.html', {})
    else:
        return render(request, 'auction/aboutNotLoggedIn.html', {})