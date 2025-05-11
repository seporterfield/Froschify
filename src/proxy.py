import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    logger.debug(f"{ip = }")
    logger.debug(f"{proxies =}")

    def test_proxy(proxy: dict[str, str]) -> dict[str, str] | None:
        logger.debug(f"Trying proxy: {proxy}")
        proxy_handler = urllib.request.ProxyHandler(proxy)
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [
            ("User-Agent", "curl/7.72.0"),
        ]
        urllib.request.install_opener(opener)
        try:
            with urllib.request.urlopen("https://ipconfig.io", timeout=10) as response:
                content: bytes = response.read()
                new_ip = content.decode("utf-8").strip()
                logger.debug(f"Response from ipconfig.io: {new_ip}")
                if new_ip != ip:
                    logger.info(f"Found good proxy {proxy} @ {new_ip}")
                    return proxy
                else:
                    logger.warning(
                        f"proxy address is same as host address: {new_ip} == {ip}"
                    )
        except Exception as e:
            logger.debug(f"Error during test request: {e}")
        return None

    candidates_proxies = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_proxy = {
            executor.submit(test_proxy, proxy): proxy for proxy in proxies
        }
        for future in as_completed(future_to_proxy):
            result = future.result()
            if result:
                candidates_proxies.append(result)
    for candidate_proxy in candidates_proxies:
        try:
            yt = YouTube(settings.TEST_YOUTUBE_URL, proxies=candidate_proxy)
            if yt.vid_info.get("videoDetails", {}).get("lengthSeconds") is not None:
                logger.info(f"Found REALLY good proxy {candidate_proxy}")
                return candidate_proxy
        except Exception:
            logger.warning(f"Candidate proxy {candidate_proxy} failed to get video")

    raise NoGoodProxyException


def get_host_ip() -> str:
    try:
        response = requests.get(
            "https://ipconfig.io", headers={"User-Agent": "curl/7.72.0"}
        )
        return response.text.strip()
    except Exception as e:
        logger.debug(f"error getting host ip: {e}")
        raise e
