from redis import Redis
import arrow
import os

redis = Redis.from_url(os.getenv("REDISCLOUD_URL") or "redis://")


def redis_key(k):
    return f"oo-checkin:{k}"


def get_current_event():
    event = _current_event_val()
    if not event:
        return None

    event_type, event_date = event.decode().split(":")
    return {"type": event_type, "date": arrow.get(event_date)}


def set_current_event(event_type="hacknight", event_date=None):
    if not event_date:
        event_date = arrow.now("US/Pacific")

    event_key = f"{event_type}:{event_date.format('YYYY-MM-DD')}"
    redis.set(redis_key("current_event"), event_key)


def get_checked_in_user():
    checked_in_emails = redis.smembers(redis_key(_current_event_val()))
    return [e.decode() for e in checked_in_emails]


def add_checked_in_user(email):
    redis.sadd(redis_key(_current_event_val()), email)


def _current_event_val():
    return redis.get(redis_key("current_event"))
