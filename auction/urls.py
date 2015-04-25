from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^login$', 'django.contrib.auth.views.login', {'template_name':'auction/login.html'}, name='login'),
    url(r'^logout$', 'django.contrib.auth.views.logout_then_login', name='logout'),
    url(r'^register$', 'auction.views.register', name='register'),
    url(r'^forgotPassword$', 'auction.views.forgotPassword', name='forgotPassword'),
    url(r'^addItem$', 'auction.views.addItem', name = 'addItem'),
    url(r'^confirm-registration/(?P<username>[a-zA-Z0-9_@\+\-]+)/(?P<token>[a-z0-9\-]+)$', 'auction.views.confirmRegistration', name='confirm'),
    url(r'^$', 'auction.views.home', name = 'home'),
    url(r'^profile/(?P<id>\d+)$', 'auction.views.profile', name = 'profile'),
    url(r'^showCategory/(?P<id>\w+)$', 'auction.views.showCategory', name = 'showCategory'),
    url(r'^productInfo/(?P<id>\d+)$', 'auction.views.productInfo', name = 'productInfo'),
    url(r'^bid/(?P<id>\d+)$', 'auction.views.bid', name = 'submitBid'),
    url(r'^confirmPasswordReset/(?P<username>[a-zA-Z0-9_@\+\-]+)/(?P<token>[a-z0-9\-]+)$', 'auction.views.confirmPasswordReset', name='confirmPass'),
    url(r'^transactionHistory$', 'auction.views.transactionSellerHistory', name='sellerHistory'),
    url(r'^buyerHistory$', 'auction.views.transactionBuyerHistory', name='buyerHistory'),
    url(r'^inventory$', 'auction.views.viewInventory', name='inventory'),
    url(r'^forgotUsername$', 'auction.views.forgotUsername', name='forgotUsername'),
    url(r'^updateBid$', 'auction.views.updateBid', name = 'updateBid'),
    url(r'^rate$', 'auction.views.rate', name='rate'),
    url(r'^paywithPayPal/(?P<id>\d+)/(?P<sellingchoice>\d+)/(?P<token>[a-z0-9\-]+)$', 'auction.views.paywithPayPal', name='paywithPayPal'),
    url(r'^finishPayment$', 'auction.views.finishPayment', name='finishPayment'),
    url(r'^sendEmail/(?P<sellerId>\d+)/(?P<itemTitle>[a-zA-Z0-9_@\+\-\s]+)$', 'auction.views.sendEmail', name='sendEmail'),
    url(r'^editItem/(?P<id>\d+)$', 'auction.views.editItem', name='editItem'),
    url(r'^submitBid$', 'auction.views.submitBid', name='ajaxBid'),
    url(r'^about$', 'auction.views.about', name='about')

)
