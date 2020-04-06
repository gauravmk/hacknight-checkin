from redis import Redis
import arrow
import os

redis = Redis.from_url(os.getenv("REDIS_URL") or "redis://")


def save(team_id, key, value):
    redis.set(_redis_key(team_id, key), value)


def retrieve(team_id, key):
    return redis.get(_redis_key(team_id, key))


def get_event_key():
    return arrow.now("US/Pacific").format("MM/DD/YYYY")


def get_checked_in_user(team_id):
    checked_in_users = redis.smembers(_redis_key(team_id, get_event_key()))
    return [u.decode() for u in checked_in_users]


def add_checked_in_user(team_id, user):
    redis.sadd(_redis_key(team_id, get_event_key()), user)


def get_teams_to_sync():
    keys = redis.keys(f"checkin:*:{get_event_key()}")
    return [k.decode().split(":")[1] for k in keys]


def _redis_key(team_id, key):
    return f"checkin:{team_id}:{key}"
