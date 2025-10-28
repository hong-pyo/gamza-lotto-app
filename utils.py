"""
유틸리티 함수 모음
"""
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re


def generate_lotto_numbers(exclude=None, count=1):
    """
    로또 번호 생성

    Args:
        exclude: 제외할 번호 set 또는 list
        count: 생성할 조합 수 (1~5)

    Returns:
        list: [1,2,3,4,5,6] (count=1일 때)
        dict: {"A": [1,2,3,4,5,6], "B": [...], ...} (count>1일 때)
    """
    # 사용 가능한 번호
    if exclude:
        available = [n for n in range(1, 46) if n not in exclude]
    else:
        available = list(range(1, 46))

    if len(available) < 6:
        return [] if count == 1 else {}

    if count == 1:
        # 단일 조합
        return sorted(random.sample(available, 6))
    else:
        # 여러 조합
        combinations = {}
        labels = ["A", "B", "C", "D", "E"]

        for i in range(count):
            numbers = sorted(random.sample(available, 6))
            combinations[labels[i]] = numbers

        return combinations


def parse_qr_url(url):
    """
    QR 코드 URL 파싱
    형식: http://m.dhlottery.co.kr/?v=1194s040913182433s041316232427s...

    Args:
        url: QR 코드 URL

    Returns:
        dict: {'draw_number': 1194, 'numbers': [[4,9,13,18,24,33], ...]} 또는 None
    """
    try:
        # URL 파싱
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        # v 파라미터 확인
        if 'v' not in query_params:
            print(f"v parameter not found in: {url}")
            return None

        v_param = query_params['v'][0]
        print(f"v parameter: {v_param}")

        # 회차 번호 추출 (처음 나오는 숫자들)
        draw_match = re.match(r'^(\d+)', v_param)
        if not draw_match:
            print("Draw number not found")
            return None

        draw_number = int(draw_match.group(1))
        print(f"Draw number: {draw_number}")

        # 회차 이후 문자열에서 's'로 구분된 번호 추출
        remaining = v_param[len(str(draw_number)):]

        # 's'로 시작하는지 확인
        if not remaining.startswith('s'):
            print(f"Invalid format after draw number: {remaining}")
            return None

        # 's'로 분리 (첫 번째는 빈 문자열이므로 제외)
        segments = remaining.split('s')[1:]
        print(f"Segments: {segments}")

        numbers_list = []

        for segment in segments[:5]:  # 최대 5개 조합
            if not segment:
                continue

            # 2자리씩 끊어서 번호 추출
            numbers = []
            for i in range(0, len(segment), 2):
                if i + 2 <= len(segment):
                    num_str = segment[i:i + 2]
                    try:
                        num = int(num_str)
                        if 1 <= num <= 45:
                            numbers.append(num)
                    except ValueError:
                        print(f"Invalid number: {num_str}")
                        continue

            # 정확히 6개 숫자가 있을 때만 추가
            if len(numbers) == 6:
                numbers_list.append(sorted(numbers))
                print(f"Valid combination: {sorted(numbers)}")
            else:
                print(f"Invalid combination length: {len(numbers)} numbers in {segment}")

        # 최소 1개 이상의 조합이 있어야 성공
        if draw_number and len(numbers_list) > 0:
            result = {
                'draw_number': draw_number,
                'numbers': numbers_list
            }
            print(f"Parse success: {result}")
            return result
        else:
            print(f"Parse failed: draw={draw_number}, combinations={len(numbers_list)}")
            return None

    except Exception as e:
        print(f"QR URL 파싱 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_excluded_numbers(combinations):
    """
    조합에서 사용된 모든 번호 추출 (중복 제거)

    Args:
        combinations: {"A": [4,9,13,18,24,33], ...}

    Returns:
        list: 중복 제거된 번호 목록
    """
    all_numbers = set()
    for numbers in combinations.values():
        all_numbers.update(numbers)

    return sorted(list(all_numbers))


def generate_excluding_numbers(excluded_numbers, count=5):
    """
    특정 번호를 제외하고 로또 번호 생성

    Args:
        excluded_numbers: 제외할 번호 리스트
        count: 생성할 조합 수

    Returns:
        dict: {"A": [1,2,3,4,5,6], "B": [...], ...}
    """
    available_numbers = [n for n in range(1, 46) if n not in excluded_numbers]

    if len(available_numbers) < 6:
        return {}

    combinations = {}
    labels = ["A", "B", "C", "D", "E"]

    for i in range(count):
        numbers = sorted(random.sample(available_numbers, 6))
        combinations[labels[i]] = numbers

    return combinations


def fetch_winning_numbers(draw_number):
    """
    동행복권 사이트에서 당첨번호 크롤링

    Args:
        draw_number: 회차 번호

    Returns:
        dict: {'winning_numbers': [1,2,3,4,5,6], 'bonus_number': 7} 또는 None
    """
    try:
        url = "https://www.dhlottery.co.kr/gameResult.do?method=byWin"
        params = {"drwNo": draw_number}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 당첨번호 추출
        winning_numbers = []
        bonus_number = None

        # 번호 추출 (클래스명: ball_645)
        balls = soup.select('.ball_645')

        if len(balls) >= 7:
            # 처음 6개는 당첨번호
            for i in range(6):
                num = int(balls[i].text.strip())
                winning_numbers.append(num)

            # 7번째는 보너스 번호
            bonus_number = int(balls[6].text.strip())

            return {
                'winning_numbers': winning_numbers,
                'bonus_number': bonus_number
            }

        return None

    except Exception as e:
        print(f"당첨번호 크롤링 오류: {e}")
        return None


def check_winning(user_numbers, winning_numbers, bonus_number):
    """
    당첨 확인

    Args:
        user_numbers: 사용자 번호 리스트 [1,2,3,4,5,6]
        winning_numbers: 당첨번호 리스트 [7,12,19,25,31,38]
        bonus_number: 보너스 번호

    Returns:
        str: "1등", "2등", "3등", "4등", "5등", "낙첨"
    """
    user_set = set(user_numbers)
    winning_set = set(winning_numbers)

    match_count = len(user_set & winning_set)
    has_bonus = bonus_number in user_set

    if match_count == 6:
        return "1등"
    elif match_count == 5 and has_bonus:
        return "2등"
    elif match_count == 5:
        return "3등"
    elif match_count == 4:
        return "4등"
    elif match_count == 3:
        return "5등"
    else:
        return "낙첨"


def format_number(num):
    """
    번호를 2자리 문자열로 포맷

    Args:
        num: 숫자

    Returns:
        str: "01", "02", ... "45"
    """
    return f"{num:02d}"


def format_numbers_with_emoji(numbers):
    """
    번호 리스트를 이모지와 함께 포맷

    Args:
        numbers: 번호 리스트

    Returns:
        str: "⚪ 01 ⚪ 02 ⚪ 03 ⚪ 04 ⚪ 05 ⚪ 06"
    """
    return " ".join([f"⚪ {format_number(n)}" for n in numbers])


def format_winning_numbers_with_emoji(numbers):
    """
    당첨번호를 이모지와 함께 포맷

    Args:
        numbers: 번호 리스트

    Returns:
        str: "🎱 01 🎱 02 🎱 03 🎱 04 🎱 05 🎱 06"
    """
    return " ".join([f"🎱 {format_number(n)}" for n in numbers])