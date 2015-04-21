from auction.models import *
from collections import OrderedDict
from auction.forms import *
from datetime import date
from django.core.mail import send_mail

MAX_RECENTLY_VIEWED = 10

def bidCheck(request):
    # Check all items to see if any have passed endBidDate
    items = Item.objects.filter(endBidDate__lte = date.today()).filter(isSold=False)
    #items = Item.objects.filter(endBidDate__gte = date.today()).filter(isSold=False)
    print('Items found in filter:')
    print(items)
    loggedInUser = request.user
    loggedInWon = False
    for item in items:
        ##NEED TO ADD CASE IF NO ONE BID ON THE ITEM

        #find the user who bid the most and send an email
        #need a user to keep track of items they have won
        print "printing bids on " + item.title
        winner = request.user
        maxBid = 0
        if len(item.bidInfo.all()) != 0:
            print "printing bidInfo length"
            print len(item.bidInfo.all())
            for b in item.bidInfo.all():
                if b.amount > maxBid:
                    maxBid = b.amount
                    winner = b.user
            #update item
            item.buyer = winner
            if winner == loggedInUser:
                loggedInWon = True
            item.finalPrice = maxBid
            item.boughtDate = date.today()
            item.isSold = True
            item.save()
            email_body = """You have won a bid for %s""" % (item.title)
            send_mail(subject='You won the bid for an item', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[winner.email])
            buyerProfile = UserProfile.objects.get(user=winner)
            email_body = """You have sold %s by bid for $%s. Please send it to %s at %s \n %s, %s %s""" % (item.title, item.finalPrice, \
                winner, buyerProfile.address, buyerProfile.city, buyerProfile.state, buyerProfile.zipcode)
            send_mail(subject='Your bit item has been sold', message= email_body, from_email='aukshopteam@gmail.com', recipient_list=[item.seller.email])
            #Need to remove this item from recently viewed
            removeItemFromRecentlyViewed(item)
        else:
            print "no one bid on " + item.title
            #enter here if no one bids on the item by the endBidDate
            #change the item type to buy it now with price equal to starting bid price
            item.sellingchoice = 'BUY'
            item.price = item.bidPrice
            item.bidPrice = None
            item.endBidDate = None
            item.save()

    return loggedInWon

            
def search(context, form, user, subsetOfAllItems, category=""):
    search = form.cleaned_data['search']
    #split the search into multiple words
    #See if each word is contained in the title
    #Count the number of times each item is found in the search results
    query = search.split()
    searchResult = {}
    for word in query:
        if category == "":
            hits = Item.objects.filter(isSold=False).filter(title__contains=word).exclude(seller=user)
        else:
            hits = Item.objects.filter(isSold=False).filter(title__contains=word).exclude(seller=user).filter(category=category)
        for hit in hits:
            if hit in searchResult:
                searchResult[hit] = searchResult[hit] + 1
            else:
                searchResult[hit] = 1
    #Sort by which item occured most in the search result
    orderedDict = OrderedDict(sorted(searchResult.items(), key=lambda t: t[1]))
    items = []
    for (key,value) in orderedDict.items():
        items.append(key)
    context['items'] = items
    if len(items) == 0:
        context['otherItems'] = subsetOfAllItems
    context['form'] = SearchForm()
    return context

#Put this in another module and import it
def getRecentlyViewed(userProfile):
    #Want most recent items in the beginning of the list
    recentlyViewed = userProfile.viewed.all().reverse()

    a = []
    for k in recentlyViewed.all():
        if k.item.seller.id != userProfile.user.id:
            a.append(k)

    recentlyViewed = a
    subset = []
    counter = 0
    for item in recentlyViewed:
        if counter < MAX_RECENTLY_VIEWED:
            subset.append(item)
            counter = counter + 1
    return subset

def removeItemFromRecentlyViewed(item):
    allUserProfiles = UserProfile.objects.all()
    for userProfile in allUserProfiles:
        toBeRemoved = userProfile.viewed.filter(item=item)
        for toRemove in toBeRemoved:
            userProfile.viewed.remove(toRemove)
        userProfile.save()