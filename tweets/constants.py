
class TweetPhotoStatus:
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


TWEET_PHOTO_STATUS_CHOICES = [
    (TweetPhotoStatus.PENDING, 'Pending'),
    (TweetPhotoStatus.APPROVED, 'Approved'),
    (TweetPhotoStatus.REJECTED, 'Rejected'),
]

TWEET_PHOTO_DEFAULT_STATUS = TweetPhotoStatus.PENDING
TWEET_PHOTO_UPLOAD_LIMIT = 9
