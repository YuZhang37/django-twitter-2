from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):

    queryset = NewsFeed.objects.all()
    serializer_class = NewsFeedSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    # may need to access the database if beyond the limit of the size cached list
    # more likely than tweets to access the database
    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request: Request):
        user = request.user
        queryset = NewsFeed.objects.filter(user_id=user.id).order_by('-created_at')
        newsfeed_list = NewsFeedService.get_cached_newsfeed_list(
            user.id, queryset=queryset
        )
        page = self.paginator.paginate_cached_list_with_limited_size(
            newsfeed_list, request
        )
        if not page:
            page = self.paginate_queryset(queryset)
        serializer = NewsFeedSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
