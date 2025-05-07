import logging
import traceback
import urllib.request
from urllib.parse import urlparse

import requests

logger = logging.getLogger("uvicorn.error")


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
    for proxy in proxies:
        logger.debug(f"Trying proxy: {proxy}")
        proxy_handler = urllib.request.ProxyHandler(proxy)
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [
            (
                "User-Agent",
                "curl/7.72.0",
                # "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            )
        ]
        logger.debug("Installing as global opener")
        urllib.request.install_opener(opener)
        try:
            # Make the request
            with urllib.request.urlopen("https://ipconfig.io") as response:
                # Read and decode the response
                content: bytes = response.read()
                new_ip = content.decode("utf-8").strip()
                logger.debug(f"Response from ipconfig.io: {new_ip}")
                if new_ip == ip:
                    logger.warning(
                        f"proxy address is same as host address: {new_ip} == {ip}"
                    )
                else:
                    logger.info(f"Found good proxy {proxy} @ {new_ip}")
                    return proxy
        except Exception as e:
            logger.debug(f"error during test request: {e}\n{traceback.format_exc()}")
    return None


def validate_proxy_url(proxy_url: str) -> bool:
    """Validate proxy URL format"""
    try:
        parsed = urlparse(proxy_url)
        return all([parsed.scheme, parsed.netloc])
    except Exception as e:
        logger.debug(
            f"Invalid proxy url: {proxy_url}\n{str(e)}\n{traceback.format_exc()}"
        )
        return False


def get_host_ip() -> str:
    try:
        response = requests.get(
            "https://ipconfig.io", headers={"User-Agent": "curl/7.72.0"}
        )
        return response.text.strip()
    except Exception as e:
        logger.debug(f"error getting host ip: {e}\n{traceback.format_exc()}")
        raise e
