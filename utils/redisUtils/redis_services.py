from django.conf import settings

from utils.redisUtils.constants import REDIS_ENCODING
from utils.redisUtils.redis_client import RedisClient
from utils.redisUtils.redis_serializers import RedisModelSerializer


class RedisService:

    @classmethod
    def _load_objects(cls, key, lazy_get_objects, serializer=RedisModelSerializer):
        serialized_objects = []
        limited_queryset = list(
            lazy_get_objects(settings.REDIS_CACHED_LIST_LIMIT_LENGTH)
        )

        for obj in limited_queryset:
            serialized_obj = serializer.serialize(obj)
            serialized_objects.append(serialized_obj)

        if serialized_objects:
            conn = RedisClient.get_connection()
            conn.rpush(key, *serialized_objects)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
        return limited_queryset

    @classmethod
    def get_objects(cls, key, lazy_get_objects, serializer=RedisModelSerializer):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            deserialized_objects = cls._load_objects(key, lazy_get_objects, serializer)
            return deserialized_objects
        objects = conn.lrange(key, 0, -1)
        deserialized_objects = []
        for obj in objects:
            deserialized_object = serializer.deserialize(obj)
            deserialized_objects.append(deserialized_object)
        return deserialized_objects

    @classmethod
    def push_object(cls, key, obj, lazy_get_objects, serializer=RedisModelSerializer):
        conn = RedisClient.get_connection()
        serialized_obj = serializer.serialize(obj)
        if not conn.exists(key):
            cls._load_objects(key, lazy_get_objects, serializer)
            return
        conn.lpush(key, serialized_obj)
        conn.ltrim(key, 0, settings.REDIS_CACHED_LIST_LIMIT_LENGTH - 1)

    @classmethod
    def _get_count_key(cls, instance, attr):
        key = f'{instance.__class__.__name__}.{attr}:{instance.id}'
        return key

    @classmethod
    def incr_count_key(cls, instance, attr):
        if instance is None:
            return -1
        key = cls._get_count_key(instance, attr)
        conn = RedisClient.get_connection()
        if conn.exists(key):
            return conn.incr(key)

        count = getattr(instance, attr)
        conn.set(key, count, ex=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def decr_count_key(cls, instance, attr):
        if instance is None:
            return -1
        key = cls._get_count_key(instance, attr)
        conn = RedisClient.get_connection()
        if conn.exists(key):
            return conn.decr(key)

        count = getattr(instance, attr)
        conn.set(key, count, ex=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def get_count(cls, instance, attr):
        if instance is None:
            return -1
        key = cls._get_count_key(instance, attr)
        conn = RedisClient.get_connection()
        count = conn.get(key)
        if count is not None:
            return int(count)
        count = getattr(instance, attr)
        conn.set(key, count, ex=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def _load_set(cls, key, lazy_get_objects, serializer=RedisModelSerializer):
        conn = RedisClient.get_connection()
        elements = list(lazy_get_objects())
        serialized_objects = []
        for obj in elements:
            serialized_obj = serializer.serialize(obj)
            serialized_objects.append(serialized_obj)

        serialized_objects.append("")
        conn.sadd(key, *serialized_objects)
        conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
        return elements

    @classmethod
    def add_to_set(cls, key, value, lazy_get_objects, serializer):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            cls._load_set(key, lazy_get_objects, serializer)
            return
        serialized_obj = serializer.serialize(value)
        conn.sadd(key, serialized_obj)

    @classmethod
    def remove_from_set(cls, key, value, lazy_get_objects, serializer):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            cls._load_set(key, lazy_get_objects, serializer)
            return
        serialized_obj = serializer.serialize(value)
        conn.srem(key, serialized_obj)

    @classmethod
    def get_from_set(cls, key, lazy_get_objects, serializer):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            deserialized_objects = cls._load_set(key, lazy_get_objects, serializer)
            return deserialized_objects
        elements = conn.smembers(key)
        elements.remove("".encode(encoding=REDIS_ENCODING))
        deserialized_objects = set()
        for obj in elements:
            deserialized_object = serializer.deserialize(obj)
            deserialized_objects.add(deserialized_object)
        return deserialized_objects

