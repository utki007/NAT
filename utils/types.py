from typing import List, Dict, Union, TypedDict


class GrinderProfile(TypedDict):
    name: str
    role: int
    payment: int
    frequency: int


class GrinderConfig(TypedDict):
    _id: int
    payment_channel: int
    manager_roles: List[int]
    max_profiles: int
    profile: Dict[str, GrinderProfile]