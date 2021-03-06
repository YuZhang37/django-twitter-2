"""twitter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import notifications
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from comments.api.views import CommentViewSet
from core.api.views import AccountViewSet, UserProfileViewSet, UserViewSet
from friendships.api.views import FriendshipViewSet
from inbox.api.views import NotificationViewSet
from likes.api.views import LikeViewSet
from newsfeeds.api.views import NewsFeedViewSet
from tweets.api.views import TweetViewSet
from notifications import urls

admin.site.site_header = 'Twitter Admin'
# The text to put at the top of the admin index page (a string).
# By default, this is “Site administration”.
admin.site.index_title = 'Admin'

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('accounts', AccountViewSet, basename='account')
router.register('tweets', TweetViewSet, basename='tweet')
router.register('friendships', FriendshipViewSet, basename='friendship')
router.register('newsfeeds', NewsFeedViewSet, basename='newsfeed')
router.register('comments', CommentViewSet, basename='comment')
router.register('likes', LikeViewSet, basename='like')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('userprofiles', UserProfileViewSet, basename='userprofile')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('playground/', include('playground.urls')),
    path('api/', include(router.urls)),
    path(
        'notifications/',
        include(notifications.urls, namespace='notifications')
    ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


