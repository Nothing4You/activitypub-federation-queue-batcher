from collections.abc import Sequence
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address
from typing import TypeAlias

from aiohttp.web import AppKey
from aiohttp_remotes.utils import parse_trusted_element

IPAddress: TypeAlias = IPv4Address | IPv6Address
IPNetwork: TypeAlias = IPv4Network | IPv6Network

IPRule: TypeAlias = Sequence[IPAddress | IPNetwork]

ALLOWED_IPS_APP_KEY: AppKey[IPRule] = AppKey("ALLOWED_IPS_APP_KEY", IPRule)


def parse_trusted_ips(s: str, sep: str = ",") -> IPRule:
    return parse_trusted_element(s.split(sep))


def is_allowed_ip(*, allowed_ips: IPRule, client_ip: str | IPAddress) -> bool:
    if isinstance(client_ip, str):
        client_ip = ip_address(client_ip)

    return any(
        # This uses an explicit Union instead of IPAddress
        # See https://github.com/python/mypy/issues/12155
        (isinstance(rule, IPv4Address | IPv6Address) and client_ip == rule)
        or (isinstance(rule, IPv4Network | IPv6Network) and client_ip in rule)
        for rule in allowed_ips
    )
