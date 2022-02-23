from friendships.models import Friendship


class FriendshipService:

    @classmethod
    def get_followers(cls, user):
        friendships = Friendship\
            .objects.filter(to_user=user)\
            .prefetch_related('from_user')
        followers = [
            friendship.from_user
            for friendship in friendships
        ]
        return followers