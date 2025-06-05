import logging

import requests
from pytubefix import YouTube  # type: ignore

from src.config import settings

logger = logging.getLogger("uvicorn.error")


class NoGoodProxyException(Exception):
    pass


def get_working_proxy(proxy_conns: list[str]) -> dict[str, str] | None:
    proxies = []
    for proxy_conn in proxy_conns:
        protocol = ""
        match proxy_conn[:5]:
            case "http:":
                protocol = "http"
            case "https":
                protocol = "https"
            case _:
                protocol = "https"
                proxy_conn = "https://" + proxy_conn
        proxies.append({protocol: proxy_conn})

    ip = get_host_ip()

    def test_proxy(proxy: dict[str, str]) -> dict[str, str] | None:
        response = requests.get(
            "https://ipconfig.io",
            proxies=proxy,
            headers={"User-Agent": "curl/7.72.0"},
            timeout=10,
        )
        new_ip = response.text.strip()
        if new_ip != ip:
            return proxy
        return None

    candidates_proxies = []
    for proxy in proxies:
        if test_proxy(proxy):
            candidates_proxies.append(proxy)

    for candidate_proxy in candidates_proxies:
        yt = YouTube(settings.TEST_YOUTUBE_URL, proxies=candidate_proxy)
        if yt.vid_info.get("videoDetails", {}).get("lengthSeconds") is not None:
            return candidate_proxy

    raise NoGoodProxyException


def get_host_ip() -> str:
    response = requests.get(
        "https://ipconfig.io", headers={"User-Agent": "curl/7.72.0"}
    )
    return response.text.strip()
