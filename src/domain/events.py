from domain.models import DomainEvent


def event(name: str, **payload: object) -> DomainEvent:
    return DomainEvent(name=name, payload=dict(payload))
