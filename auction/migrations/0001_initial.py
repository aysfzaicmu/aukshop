# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localflavor.us.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BiddingInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(null=True, max_digits=10, decimal_places=2)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=200)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('commenter', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=600)),
                ('price', models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True)),
                ('bidPrice', models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True)),
                ('finalPrice', models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True)),
                ('picture_url', models.CharField(default=b'http://vector-magz.com/wp-content/uploads/2013/11/question-mark-icon2.png', max_length=256, blank=True)),
                ('isSold', models.BooleanField(default=False)),
                ('creationDate', models.DateField(auto_now_add=True)),
                ('endBidDate', models.DateField(null=True, blank=True)),
                ('boughtDate', models.DateField(null=True, blank=True)),
                ('sellingChoice', models.CharField(default=b'BUY', max_length=22, choices=[(b'BUY', b'Buy It Now'), (b'BID', b'Bid'), (b'BIDBUY', b'Bid or Buy It Now')])),
                ('category', models.CharField(default=b'Other', max_length=22, choices=[(b'Electronics', b'Electronics'), (b'Furniture', b'Furniture'), (b'Clothing', b'Clothing'), (b'Kitchen', b'Kitchen'), (b'Sports', b'Sports'), (b'Books', b'Books'), (b'Games', b'Games'), (b'Toys', b'Toys'), (b'Beauty', b'Beauty'), (b'Outdoors', b'Outdoors'), (b'Other', b'Other')])),
                ('numReviews', models.IntegerField(default=0)),
                ('sumStars', models.IntegerField(default=0)),
                ('numStarRequests', models.IntegerField(default=0)),
                ('bidInfo', models.ManyToManyField(to='auction.BiddingInfo', null=True, blank=True)),
                ('buyer', models.ForeignKey(related_name='buyer', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('seller', models.ForeignKey(related_name='seller', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('accessToken', models.CharField(max_length=200, blank=True)),
                ('publishableKey', models.CharField(max_length=200, blank=True)),
                ('stripeId', models.CharField(max_length=200, blank=True)),
                ('address', models.CharField(max_length=40)),
                ('state', localflavor.us.models.USStateField(max_length=2, choices=[(b'AL', b'Alabama'), (b'AK', b'Alaska'), (b'AS', b'American Samoa'), (b'AZ', b'Arizona'), (b'AR', b'Arkansas'), (b'AA', b'Armed Forces Americas'), (b'AE', b'Armed Forces Europe'), (b'AP', b'Armed Forces Pacific'), (b'CA', b'California'), (b'CO', b'Colorado'), (b'CT', b'Connecticut'), (b'DE', b'Delaware'), (b'DC', b'District of Columbia'), (b'FL', b'Florida'), (b'GA', b'Georgia'), (b'GU', b'Guam'), (b'HI', b'Hawaii'), (b'ID', b'Idaho'), (b'IL', b'Illinois'), (b'IN', b'Indiana'), (b'IA', b'Iowa'), (b'KS', b'Kansas'), (b'KY', b'Kentucky'), (b'LA', b'Louisiana'), (b'ME', b'Maine'), (b'MD', b'Maryland'), (b'MA', b'Massachusetts'), (b'MI', b'Michigan'), (b'MN', b'Minnesota'), (b'MS', b'Mississippi'), (b'MO', b'Missouri'), (b'MT', b'Montana'), (b'NE', b'Nebraska'), (b'NV', b'Nevada'), (b'NH', b'New Hampshire'), (b'NJ', b'New Jersey'), (b'NM', b'New Mexico'), (b'NY', b'New York'), (b'NC', b'North Carolina'), (b'ND', b'North Dakota'), (b'MP', b'Northern Mariana Islands'), (b'OH', b'Ohio'), (b'OK', b'Oklahoma'), (b'OR', b'Oregon'), (b'PA', b'Pennsylvania'), (b'PR', b'Puerto Rico'), (b'RI', b'Rhode Island'), (b'SC', b'South Carolina'), (b'SD', b'South Dakota'), (b'TN', b'Tennessee'), (b'TX', b'Texas'), (b'UT', b'Utah'), (b'VT', b'Vermont'), (b'VI', b'Virgin Islands'), (b'VA', b'Virginia'), (b'WA', b'Washington'), (b'WV', b'West Virginia'), (b'WI', b'Wisconsin'), (b'WY', b'Wyoming')])),
                ('city', models.CharField(max_length=40)),
                ('zipcode', localflavor.us.models.USZipCodeField(max_length=10)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ViewedItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('viewedDate', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(to='auction.Item')),
            ],
            options={
                'ordering': ['viewedDate'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='viewed',
            field=models.ManyToManyField(to='auction.ViewedItem', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='item',
            field=models.ForeignKey(to='auction.Item'),
            preserve_default=True,
        ),
    ]
