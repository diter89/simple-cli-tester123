import json
import requests
from rich import print
from pathlib import Path

class TwitterUnliker:
    def __init__(self, authorization, csrf_token, cookie, user_agent):
        self.url = "https://x.com/i/api/graphql/ZYKSe-w7KEslx3JhSIk5LA/UnfavoriteTweet"
        self.headers = {
            "authorization": authorization,
            "content-type": "application/json",
            "x-csrf-token": csrf_token,
            "cookie": cookie,
            "user-agent": user_agent,
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://x.com",
            "referer": "https://x.com/",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-arch": "\"x86\"",
            "sec-ch-ua-bitness": "\"64\"",
            "sec-ch-ua-full-version": "\"138.0.7204.92\"",
            "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"138.0.7204.92\", \"Google Chrome\";v=\"138.0.7204.92\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-ch-ua-platform-version": "\"6.1.0\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en"
        }
        self.default_payload = {
            "variables": {
                "tweet_id": ""
            },
            "queryId": "ZYKSe-w7KEslx3JhSIk5LA"
        }

    def unlike_tweet(self, tweet_id):
        payload = self.default_payload.copy()
        payload["variables"]["tweet_id"] = tweet_id

        try:
            response = requests.post(self.url, headers=self.headers, json=payload)
            if response.status_code == 200:
                return {"status": "success", "data": response.json(), "text": response.text}
            else:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "message": response.text
                }
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}


