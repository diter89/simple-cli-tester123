import json
import requests
from rich import print

class TwitterCommenter:
    def __init__(self, authorization, csrf_token, cookie, user_agent):
        self.url = "https://x.com/i/api/graphql/-WPiAw0yXv4yy0FT4-GVtQ/CreateTweet"
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
            "referer": "https://x.com/compose/post",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-arch": "x86",
            "sec-ch-ua-bitness": "64",
            "sec-ch-ua-full-version": "138.0.7204.92",
            "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"138.0.7204.92\", \"Google Chrome\";v=\"138.0.7204.92\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "",
            "sec-ch-ua-platform": "Linux",
            "sec-ch-ua-platform-version": "6.1.0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en"
        }
        self.default_payload = {
            "variables": {
                "tweet_text": "",
                "reply": {
                    "in_reply_to_tweet_id": "",
                    "exclude_reply_user_ids": []
                },
                "dark_request": False,
                "media": {
                    "media_entities": [],
                    "possibly_sensitive": False
                },
                "semantic_annotation_ids": [],
                "disallowed_reply_options": None
            },
            "features": {
                "premium_content_api_read_enabled": False,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "responsive_web_jetfuel_frame": True,
                "responsive_web_grok_share_attachment_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_grok_show_grok_translated_post": False,
                "responsive_web_grok_analysis_button_from_backend": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "payments_enabled": False,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "verified_phone_label_enabled": False,
                "articles_preview_enabled": True,
                "responsive_web_grok_community_note_auto_translation_is_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "-WPiAw0yXv4yy0FT4-GVtQ"
        }

    def post_comment(self, tweet_text, in_reply_to_tweet_id):
        payload = self.default_payload.copy()
        payload["variables"]["tweet_text"] = tweet_text
        payload["variables"]["reply"]["in_reply_to_tweet_id"] = in_reply_to_tweet_id

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

