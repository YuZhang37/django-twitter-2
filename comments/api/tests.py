from comments.models import Comment
from django.utils import timezone
from rest_framework.test import APIClient
from testing.testcases import TestCase


COMMENT_URL = '/api/comments/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentApiTests(TestCase):

    def setUp(self):
        super(CommentApiTests, self).setUp()
        self.user1 = self.create_user('user1')
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(self.user1)
        self.user2 = self.create_user('user2')
        self.user2_client = APIClient()
        self.user2_client.force_authenticate(self.user2)
        self.tweet = self.create_tweet(self.user1)

    def test_create(self):
        # 匿名不可以创建
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # 啥参数都没带不行
        response = self.user1_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 只带 tweet_id 不行
        response = self.user1_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # 只带 content 不行
        response = self.user1_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content 太长不行
        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        # tweet_id 和 content 都带才行
        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['comment']['user']['id'], self.user1.id)
        self.assertEqual(response.data['comment']['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['comment']['content'], '1')

    def test_destroy(self):
        comment = self.create_comment(self.user1, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 非本人不能删除
        response = self.user2_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 本人可以删除
        count = Comment.objects.count()
        response = self.user1_client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.user1, self.tweet, 'original')
        another_tweet = self.create_tweet(self.user2)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 使用 put 的情况下
        # 匿名不可以更新
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        # 非本人不能更新
        response = self.user2_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, 'new')
        # 不能更新除 content 外的内容，静默处理，只更新内容
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.user1_client.put(url, {
            'content': 'new',
            'user_id': self.user2.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.user1)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        # 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 带了 tweet_id 可以访问
        # 一开始没有评论
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # 评论按照时间顺序排序
        self.create_comment(self.user1, self.tweet, '1')
        self.create_comment(self.user2, self.tweet, '2')
        self.create_comment(self.user2, self.create_tweet(self.user2), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 同时提供 user_id 和 tweet_id 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.user1.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.user1)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.user2_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['tweet']['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.user1, tweet)
        response = self.user2_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.user2, tweet)
        self.create_newsfeed(self.user2, tweet)
        response = self.user2_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 2)

    def test_comments_count_with_cache(self):
        self.create_newsfeed(self.user1, self.tweet)
        self.create_newsfeed(self.user2, self.tweet)
        tweet_url = '/api/tweets/{}/'.format(self.tweet.id)
        response = self.user1_client.get(tweet_url)
        self.assertEqual(self.tweet.comments_count, 0)
        self.assertEqual(response.data['tweet']['comments_count'], 0)

        data = {'tweet_id': self.tweet.id, 'content': 'a comment'}
        for i in range(2):
            _, client = self.create_user_and_client('someone{}'.format(i))
            client.post(COMMENT_URL, data)
            response = client.get(tweet_url)
            self.assertEqual(response.data['tweet']['comments_count'], i + 1)
            self.tweet.refresh_from_db()
            self.assertEqual(self.tweet.comments_count, i + 1)

        post_response = self.user2_client.post(COMMENT_URL, data)
        comment_data = post_response.data
        response = self.user2_client.get(tweet_url)
        self.assertEqual(response.data['tweet']['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # check tweet list
        response = self.user1_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['comments_count'], 3)
        response = self.user2_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['comments_count'], 3)

        # check newsfeed api
        newsfeed_url = '/api/newsfeeds/'
        response = self.user1_client.get(newsfeed_url)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 3)
        response = self.user2_client.get(newsfeed_url)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 3)

        # update comment shouldn't update comments_count
        comment_url = '{}{}/'.format(COMMENT_URL, comment_data['comment']['id'])
        response = self.user2_client.put(comment_url, {'content': 'updated'})
        self.assertEqual(response.status_code, 200)
        response = self.user2_client.get(tweet_url)
        self.assertEqual(response.data['tweet']['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # delete a comment will update comments_count
        response = self.user2_client.delete(comment_url)
        self.assertEqual(response.status_code, 200)
        response = self.user1_client.get(tweet_url)
        self.assertEqual(response.data['tweet']['comments_count'], 2)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 2)


