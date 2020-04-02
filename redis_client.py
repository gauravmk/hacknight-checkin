from redis import Redis
import arrow
import os

redis = Redis.from_url(os.getenv("REDIS_URL") or "redis://")


def redis_key(k):
    return f"oo-checkin:{k}"


def get_event_key():
    return arrow.now("US/Pacific").format("MM/DD/YYYY")


def get_checked_in_user():
    checked_in_users = redis.smembers(redis_key(get_event_key()))
    return [u.decode() for u in checked_in_users]


def add_checked_in_user(user):
    redis.sadd(redis_key(get_event_key()), user)
