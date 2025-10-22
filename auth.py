"""
카카오 OAuth 인증 모듈
"""
import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 카카오 API 설정
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# 카카오 인증 URL
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


def get_kakao_login_url():
    """
    카카오 로그인 URL 생성

    Returns:
        str: 카카오 인증 페이지 URL
    """
    params = {
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code"
    }
    return f"{KAKAO_AUTH_URL}?{urlencode(params)}"


def get_access_token(auth_code):
    """
    인증 코드로 액세스 토큰 발급

    Args:
        auth_code: 카카오 인증 코드

    Returns:
        str: 액세스 토큰 또는 None (실패 시)
    """
    try:
        # 토큰 발급 요청
        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": auth_code
        }

        response = requests.post(KAKAO_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        return token_data.get("access_token")

    except Exception as e:
        print(f"액세스 토큰 발급 오류: {e}")
        return None


def get_user_info(access_token):
    """
    액세스 토큰으로 사용자 정보 가져오기

    Args:
        access_token: 카카오 액세스 토큰

    Returns:
        dict: {"kakao_id": 123456789, "nickname": "홍길동"} 또는 None (실패 시)
    """
    try:
        # 사용자 정보 요청
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(KAKAO_USER_INFO_URL, headers=headers, timeout=10)
        response.raise_for_status()

        user_data = response.json()

        # 필요한 정보만 추출
        kakao_id = user_data.get("id")  # 카카오 고유 ID (정수)
        nickname = user_data.get("properties", {}).get("nickname", "사용자")

        return {
            "kakao_id": kakao_id,
            "nickname": nickname
        }

    except Exception as e:
        print(f"사용자 정보 조회 오류: {e}")
        return None


def kakao_login(auth_code):
    """
    카카오 로그인 전체 프로세스

    Args:
        auth_code: 카카오 인증 코드

    Returns:
        dict: 사용자 정보 {"kakao_id": 123456789, "nickname": "홍길동"} 또는 None (실패 시)
    """
    # 1. 액세스 토큰 발급
    access_token = get_access_token(auth_code)
    if not access_token:
        return None

    # 2. 사용자 정보 가져오기
    user_info = get_user_info(access_token)
    return user_info
