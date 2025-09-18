import json
import requests

class TweetScraper:
    FEATURES = {
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": True,
        "responsive_web_jetfuel_frame": True,
        "responsive_web_grok_share_attachment_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "payments_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "verified_phone_label_enabled": False,
        "responsive_web_grok_image_annotation_enabled": True,
        "responsive_web_grok_imagine_annotation_enabled": True,
        "responsive_web_grok_community_note_auto_translation_is_enabled": False,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
    }

    FIELD_TOGGLES = {
        "withArticleRichContentState": True,
        "withArticlePlainText": False,
    }

    BASE_URL = "https://x.com/i/api/graphql/wqi5M7wZ7tW-X9S2t-Mqcg/TweetResultByRestId"

    def __init__(self, authorization, csrf_token, cookie, user_agent):
        if not all([authorization, csrf_token, cookie, user_agent]):
            raise ValueError("All authentication parameters must be non-empty.")

        self.headers = {
            "accept": "*/*",
            "authorization": authorization,
            "cookie": cookie,
            "user-agent": user_agent,
            "x-csrf-token": csrf_token,
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://x.com",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "id",
        }

    def get_tweet_description(self, tweet_id):
        if not tweet_id:
            return {"status": "error", "message": "Invalid tweet_id provided."}

        variables = {
            "tweetId": tweet_id,
            "includePromotedContent": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withCommunity": True,
        }

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(self.FEATURES),
            "fieldToggles": json.dumps(self.FIELD_TOGGLES),
        }

        current_headers = self.headers.copy()
        current_headers["referer"] = f"https://x.com/anyuser/status/{tweet_id}"

        try:
            response = requests.get(self.BASE_URL, headers=current_headers, params=params)
            if response.status_code != 200:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "message": f"HTTP Error: {response.status_code} {response.reason}",
                    "details": response.text,
                }

            data = response.json()
            tweet_result = data.get("data", {}).get("tweetResult", {}).get("result", {})

            if not tweet_result:
                return {
                    "status": "error",
                    "message": "Tweet data not found. It might be deleted or private.",
                }

            full_text = ""
            try:
                full_text = (
                    tweet_result["note_tweet"]
                    ["note_tweet_results"]
                    ["result"]
                    ["text"]
                )
            except KeyError:
                full_text = tweet_result.get("legacy", {}).get("full_text", "")

            if full_text:
                return {"status": "success", "description": full_text}
            else:
                return {"status": "error", "message": "Could not extract tweet text from response."}

        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}
        except (KeyError, json.JSONDecodeError) as e:
            return {"status": "error", "message": f"Failed to parse response: {str(e)}"}
