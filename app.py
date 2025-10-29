"""
로또 번호 관리 앱 - 메인 애플리케이션
"""
import streamlit as st
from datetime import datetime
import json
import os

from database import SessionLocal, User, init_db, get_session, RecommendedNumber, PurchasedNumber, DrawResult, get_or_create_user
from utils import (
    generate_lotto_numbers,
    parse_qr_url,
    get_excluded_numbers,
    generate_excluding_numbers,
    fetch_winning_numbers,
    check_winning,
    format_numbers_with_emoji,
    format_winning_numbers_with_emoji,
    format_number
)
from auth import get_kakao_login_url, kakao_login

# 페이지 설정
st.set_page_config(
    page_title="로또 번호 관리 앱",
    page_icon="🎲",
    layout="wide"
)

# 데이터베이스 초기화
@st.cache_resource
def initialize_database():
    return init_db()

# 세션 초기화
if 'db_session' not in st.session_state:
    st.session_state.db_session = initialize_database()

session = st.session_state.db_session

# 로그인 상태 초기화
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'kakao_id' not in st.session_state:
    st.session_state.kakao_id = None
if 'nickname' not in st.session_state:
    st.session_state.nickname = None
if 'login_processed' not in st.session_state:
    st.session_state.login_processed = False

# ===== 로그인 처리 =====
query_params = st.query_params

# 카카오 로그인 콜백 처리
if 'code' in query_params and not st.session_state.is_logged_in and not st.session_state.login_processed:
    st.session_state.login_processed = True

    auth_code = query_params['code']

    with st.spinner("로그인 중..."):
        user_info = kakao_login(auth_code)

        if user_info:
            session = SessionLocal()
            try:
                user = get_or_create_user(session, user_info['kakao_id'], user_info['nickname'])

                st.session_state.is_logged_in = True
                st.session_state.user_id = user.id
                st.session_state.kakao_id = user.kakao_id
                st.session_state.nickname = user.nickname

                session.close()

                st.success("로그인 성공!")
                st.query_params.clear()
                st.rerun()

            except Exception as e:
                st.error(f"로그인 처리 중 오류: {e}")
                session.rollback()
                session.close()
                st.session_state.login_processed = False
        else:
            st.error("로그인에 실패했습니다. 다시 시도해주세요.")
            st.session_state.login_processed = False

# ===== 로그인 페이지 =====
if not st.session_state.is_logged_in:
    st.title("🎰 로또 번호 관리")
    st.markdown("---")

    # 로그인 안내
    st.markdown("""
    ### 로그인이 필요합니다
    
    카카오톡 계정으로 로그인하여 나만의 로또 번호를 관리하세요!
    
    **기능:**
    - 🎲 랜덤 번호 생성 및 저장
    - 📱 QR 코드로 구매 기록 관리
    - 🎯 자동 당첨 확인
    - 📊 번호 추천 히스토리
    """)

    st.markdown("---")

    # 카카오 로그인 버튼 (새 탭)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        kakao_login_url = get_kakao_login_url()

        st.markdown(f"""
        <div style="text-align: center;">
            <a href="{kakao_login_url}" target="_blank" rel="noopener noreferrer" 
               style="text-decoration: none; display: inline-block; width: 100%;">
                <div style="
                    background-color: #FEE500;
                    color: #000000;
                    text-align: center;
                    padding: 15px 30px;
                    font-size: 18px;
                    border-radius: 12px;
                    cursor: pointer;
                    font-weight: bold;
                    border: none;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    🟡 카카오톡으로 로그인
                </div>
            </a>
            <div style="margin-top: 15px; color: #666; font-size: 14px;">
                💡 새 탭에서 로그인 후 이 페이지로 돌아와주세요
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ===== 메인 앱 (로그인 후) =====

# 사이드바
with st.sidebar:
    st.markdown(f"""
    ### 👤 {st.session_state.nickname}님
    """)

    if st.button("🚪 로그아웃"):
        st.session_state.is_logged_in = False
        st.session_state.user_id = None
        st.session_state.kakao_id = None
        st.session_state.nickname = None
        st.session_state.login_processed = False
        st.rerun()

    st.markdown("---")

    menu = st.radio(
        "메뉴",
        ["🎲 번호 생성", "📱 QR 입력", "📋 구매 기록", "📊 추천 히스토리", "🎯 당첨 확인"]
    )

# 메인 영역
st.title("🎰 로또 번호 관리")
st.markdown("---")

# ===== 1. 번호 생성 =====
if menu == "🎲 번호 생성":
    st.header("🎲 랜덤 번호 생성")

    num_sets = st.slider("생성할 조합 수", 1, 5, 1)

    if st.button("🎲 번호 생성하기"):
        with st.spinner("번호 생성 중..."):
            numbers_list = []
            labels = ['A', 'B', 'C', 'D', 'E']

            for i in range(num_sets):
                numbers = generate_lotto_numbers()
                numbers_list.append(numbers)

                st.markdown(f"**{labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

            session = SessionLocal()
            try:
                numbers_dict = {labels[i]: numbers_list[i] for i in range(num_sets)}

                recommended = RecommendedNumber(
                    user_id=st.session_state.user_id
                )
                recommended.numbers = numbers_dict

                session.add(recommended)
                session.commit()

                st.success("✅ 생성된 번호가 히스토리에 저장되었습니다!")

            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")
                session.rollback()
            finally:
                session.close()

# ===== 2. QR 입력 =====
elif menu == "📱 QR 입력":
    st.header("📱 QR 코드 입력")

    tab1, tab2 = st.tabs(["📷 카메라로 스캔", "⌨️ URL 직접 입력"])

    with tab1:
        st.markdown("### 📷 카메라로 QR 코드 스캔")
        st.info("🎯 QR 코드를 카메라에 비추면 자동으로 인식됩니다!")

        # QR 스캐너 HTML
        qr_scanner_html = """
        <!-- 기존 HTML 코드 그대로 -->
        """

        scanned_url = st.components.v1.html(qr_scanner_html, height=600)

        # 스캔 결과를 session_state에 저장
        if 'camera_qr_result' not in st.session_state:
            st.session_state.camera_qr_result = None

        if scanned_url:
            with st.spinner("QR 분석 중..."):
                result = parse_qr_url(scanned_url)

                if result:
                    st.session_state.camera_qr_result = result

        # 분석 결과가 있으면 표시
        if st.session_state.camera_qr_result:
            result = st.session_state.camera_qr_result
            draw_number = result['draw_number']
            numbers_list = result['numbers']

            st.markdown("---")
            st.success(f"✅ {draw_number}회차 QR 분석 완료!")

            st.markdown("### 📊 분석 결과")
            st.markdown(f"**회차:** {draw_number}회")

            st.markdown("**파싱된 번호:**")
            labels = ['A', 'B', 'C', 'D', 'E']
            for i, numbers in enumerate(numbers_list):
                if i < len(labels):
                    st.markdown(f"{labels[i]}조합: {' '.join([f'{n:02d}' for n in numbers])}")

            # 구매기록 저장 버튼
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 구매기록 저장", key="save_camera_scan"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: numbers_list[i] for i in range(len(numbers_list))}

                        purchased = PurchasedNumber(
                            user_id=st.session_state.user_id,
                            draw_number=draw_number
                        )
                        purchased.numbers = numbers_dict

                        session.add(purchased)
                        session.commit()

                        st.success("✅ 구매기록이 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()

            with col2:
                if st.button("🗑️ 결과 지우기", key="clear_camera"):
                    st.session_state.camera_qr_result = None
                    st.rerun()

            # 제외 번호 추천 (위와 동일한 로직)
            st.markdown("---")
            st.markdown("### 🎲 이 번호들 제외하고 5개 조합 추천")

            all_numbers = set()
            for numbers in numbers_list:
                all_numbers.update(numbers)

            st.markdown(f"**제외된 번호:** {' '.join([f'{n:02d}' for n in sorted(all_numbers)])}")

            if 'camera_recommended' not in st.session_state:
                st.session_state.camera_recommended = None

            if st.button("🎲 제외 번호 기반 추천 생성", key="gen_excluding_camera"):
                recommended_sets = []
                for i in range(5):
                    numbers = generate_lotto_numbers(exclude=all_numbers)
                    recommended_sets.append(numbers)

                st.session_state.camera_recommended = recommended_sets

            if st.session_state.camera_recommended:
                st.markdown("**추천 번호:**")
                for i, numbers in enumerate(st.session_state.camera_recommended):
                    st.markdown(f"**추천 {labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

                if st.button("💾 추천번호 5개 모두 저장", key="save_recommended_camera"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: st.session_state.camera_recommended[i] for i in range(5)}

                        recommended = RecommendedNumber(
                            user_id=st.session_state.user_id
                        )
                        recommended.numbers = numbers_dict

                        session.add(recommended)
                        session.commit()

                        st.success("✅ 추천번호가 히스토리에 저장되었습니다!")
                        st.session_state.camera_recommended = None
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()

    with tab2:
        st.markdown("### ⌨️ URL 직접 입력")

        qr_url = st.text_input(
            "QR URL을 입력하세요",
            placeholder="http://m.dhlottery.co.kr/?v=...",
            key="manual_qr_url"
        )

        # 분석 결과를 session_state에 저장
        if 'manual_qr_result' not in st.session_state:
            st.session_state.manual_qr_result = None

        if st.button("🔍 분석하기", key="analyze_manual") and qr_url:
            with st.spinner("QR 분석 중..."):
                result = parse_qr_url(qr_url)

                if result:
                    st.session_state.manual_qr_result = result
                    st.success(f"✅ {result['draw_number']}회차 QR 분석 완료!")
                else:
                    st.error("❌ QR URL 형식이 올바르지 않습니다.")
                    st.session_state.manual_qr_result = None

        # 분석 결과가 있으면 표시
        if st.session_state.manual_qr_result:
            result = st.session_state.manual_qr_result
            draw_number = result['draw_number']
            numbers_list = result['numbers']

            st.markdown("---")
            st.markdown("### 📊 분석 결과")
            st.markdown(f"**회차:** {draw_number}회")

            st.markdown("**파싱된 번호:**")
            labels = ['A', 'B', 'C', 'D', 'E']
            for i, numbers in enumerate(numbers_list):
                if i < len(labels):
                    st.markdown(f"{labels[i]}조합: {' '.join([f'{n:02d}' for n in numbers])}")

            # 구매기록 저장 버튼
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 구매기록 저장", key="save_manual"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: numbers_list[i] for i in range(len(numbers_list))}

                        purchased = PurchasedNumber(
                            user_id=st.session_state.user_id,
                            draw_number=draw_number
                        )
                        purchased.numbers = numbers_dict

                        session.add(purchased)
                        session.commit()

                        st.success("✅ 구매기록이 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()

            with col2:
                if st.button("🗑️ 결과 지우기", key="clear_manual"):
                    st.session_state.manual_qr_result = None
                    st.rerun()

            # 제외 번호 추천
            st.markdown("---")
            st.markdown("### 🎲 이 번호들 제외하고 5개 조합 추천")

            all_numbers = set()
            for numbers in numbers_list:
                all_numbers.update(numbers)

            st.markdown(f"**제외된 번호:** {' '.join([f'{n:02d}' for n in sorted(all_numbers)])}")

            # 추천 결과를 session_state에 저장
            if 'manual_recommended' not in st.session_state:
                st.session_state.manual_recommended = None

            if st.button("🎲 제외 번호 기반 추천 생성", key="gen_excluding_manual"):
                recommended_sets = []
                for i in range(5):
                    numbers = generate_lotto_numbers(exclude=all_numbers)
                    recommended_sets.append(numbers)

                st.session_state.manual_recommended = recommended_sets

            # 추천 결과 표시
            if st.session_state.manual_recommended:
                st.markdown("**추천 번호:**")
                for i, numbers in enumerate(st.session_state.manual_recommended):
                    st.markdown(f"**추천 {labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

                if st.button("💾 추천번호 5개 모두 저장", key="save_recommended_manual"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: st.session_state.manual_recommended[i] for i in range(5)}

                        recommended = RecommendedNumber(
                            user_id=st.session_state.user_id
                        )
                        recommended.numbers = numbers_dict

                        session.add(recommended)
                        session.commit()

                        st.success("✅ 추천번호가 히스토리에 저장되었습니다!")
                        st.session_state.manual_recommended = None
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()

# ===== 3. 구매 기록 =====
elif menu == "📋 구매 기록":
    st.header("📋 구매 기록")

    session = SessionLocal()
    try:
        purchases = session.query(PurchasedNumber)\
            .filter_by(user_id=st.session_state.user_id)\
            .order_by(PurchasedNumber.purchased_at.desc())\
            .all()

        if not purchases:
            st.info("구매 기록이 없습니다.")
        else:
            for purchase in purchases:
                with st.expander(f"📅 {purchase.purchased_at.strftime('%Y-%m-%d %H:%M')} | {purchase.draw_number}회차"):
                    for label, numbers in purchase.numbers.items():
                        status = purchase.winning_status or "미확인"
                        st.markdown(f"**{label}조합:** {' '.join([f'{n:02d}' for n in numbers])} | {status}")
    finally:
        session.close()

# ===== 4. 추천 히스토리 =====
elif menu == "📊 추천 히스토리":
    st.header("📊 추천 번호 히스토리")

    session = SessionLocal()
    try:
        recommendations = session.query(RecommendedNumber)\
            .filter_by(user_id=st.session_state.user_id)\
            .order_by(RecommendedNumber.created_at.desc())\
            .all()

        if not recommendations:
            st.info("추천 기록이 없습니다.")
        else:
            for rec in recommendations:
                draw_info = f"{rec.draw_number}회차" if rec.draw_number else "미배정"
                with st.expander(f"📅 {rec.created_at.strftime('%Y-%m-%d %H:%M')} | {draw_info}"):
                    for label, numbers in rec.numbers.items():
                        status = rec.winning_status or "미확인"
                        st.markdown(f"**{label}조합:** {' '.join([f'⚪ {n:02d}' for n in numbers])} | {status}")
    finally:
        session.close()

# ===== 5. 당첨 확인 =====
elif menu == "🎯 당첨 확인":
    st.header("🎯 당첨 확인")

    draw_number = st.number_input("회차 번호", min_value=1, value=1194, step=1)

    if st.button("🔍 당첨번호 조회하기"):
        with st.spinner("당첨번호 조회 중..."):
            winning_info = fetch_winning_numbers(draw_number)

            if winning_info:
                st.success(f"✅ {draw_number}회차 당첨번호")

                winning_numbers = winning_info['winning_numbers']
                bonus_number = winning_info['bonus_number']

                st.markdown("**당첨번호:** " + " ".join([f"🎱 {n:02d}" for n in winning_numbers]))
                st.markdown(f"**보너스:** 🎱 {bonus_number:02d}")
            else:
                st.error("당첨번호를 가져오지 못했습니다.")

    st.markdown("---")

    if st.button("📋 전체 기록 일괄 확인"):
        with st.spinner("당첨 확인 중..."):
            session = SessionLocal()
            try:
                purchases = session.query(PurchasedNumber)\
                    .filter_by(user_id=st.session_state.user_id)\
                    .all()

                recommendations = session.query(RecommendedNumber)\
                    .filter_by(user_id=st.session_state.user_id)\
                    .all()

                total_win = 0
                total_lose = 0

                for purchase in purchases:
                    winning_info = fetch_winning_numbers(purchase.draw_number)
                    if winning_info:
                        for label, numbers in purchase.numbers.items():
                            result = check_winning(numbers, winning_info['winning_numbers'], winning_info['bonus_number'])
                            if result != "낙첨":
                                total_win += 1
                                st.success(f"🎉 {result}! | {purchase.draw_number}회차 {label}조합")
                            else:
                                total_lose += 1

                for rec in recommendations:
                    if rec.draw_number:
                        winning_info = fetch_winning_numbers(rec.draw_number)
                        if winning_info:
                            for label, numbers in rec.numbers.items():
                                result = check_winning(numbers, winning_info['winning_numbers'], winning_info['bonus_number'])
                                if result != "낙첨":
                                    total_win += 1
                                    st.success(f"🎉 {result}! | {rec.draw_number}회차 {label}조합")
                                else:
                                    total_lose += 1

                st.markdown("---")
                st.markdown(f"**총 당첨:** {total_win}건 | **낙첨:** {total_lose}건")

            finally:
                session.close()