def invalidate_cached_object(sender, instance, **kwargs):
    from utils.memcached_services import MemcachedService
    MemcachedService.invalidate_object(sender, instance.id)
