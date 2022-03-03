from django.core.cache import cache
from django.shortcuts import render
from rest_framework import viewsets

from core import models
from likes.models import Like
from twitter.cache import USER_PATTERN


def calculate():
    x = 1
    y = 2
    return x + y


def say_hello(request):
    key = USER_PATTERN.format(user_id=6)
    cache.delete(key)
    result = cache.get(key)
    print('None: ', result)
    user = models.User.objects.get(id=6)
    cache.set(key, user)
    result = cache.get(key)
    print('exist: ', result)
    print('username: ', result.username)
    user.username = 'testname666'
    user.save()
    result = cache.get(key)
    print('None: ', result)
    user = models.User.objects.get(id=6)
    cache.set(key, user)
    result = cache.get(key)
    print('exist: ', result)
    print('username: ', result.username)

    # profile = UserProfile.objects.filter(id=3).first()
    # url = profile.avatar.url
    # print(url)
    # like = Like.objects.all().first()
    # model_name = like.content_type.model
    # print(model_name)
    # print(model_name == 'comment')
    # print(model_name == 'tweet')
    return render(request, 'playground/hello.html', {'name': 'Marvin', 'value': 'url'})


class PlayViewSet(viewsets.ModelViewSet):
    pass
