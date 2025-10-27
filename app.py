"""
로또 번호 관리 앱 - 메인 애플리케이션
"""
import streamlit as st
from datetime import datetime
from database import SessionLocal, User, RecommendedNumber, PurchasedNumber, init_db
from utils import generate_numbers, parse_qr_url, fetch_winning_numbers, check_winning
from auth import get_kakao_login_url, kakao_login

# 페이지 설정
st.set_page_config(
    page_title="로또 번호 관리",
    page_icon="🎰",
    layout="wide"
)

# 데이터베이스 초기화
init_db()

# 세션 상태 초기화
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

# 카카오 로그인 콜백 처리 (code 파라미터가 있을 때)
if 'code' in query_params and not st.session_state.login_processed:
    # 중복 처리 방지
    st.session_state.login_processed = True

    auth_code = query_params['code']

    with st.spinner("로그인 중..."):
        # 카카오 로그인 처리
        user_info = kakao_login(auth_code)

        if user_info:
            # DB에서 사용자 조회 또는 생성
            session = SessionLocal()
            try:
                user = session.query(User).filter_by(kakao_id=user_info['kakao_id']).first()

                if not user:
                    # 첫 로그인: 새 사용자 생성
                    user = User(
                        kakao_id=user_info['kakao_id'],
                        nickname=user_info['nickname']
                    )
                    session.add(user)
                    session.commit()

                # 세션에 사용자 정보 저장
                st.session_state.is_logged_in = True
                st.session_state.user_id = user.id
                st.session_state.kakao_id = user.kakao_id
                st.session_state.nickname = user.nickname

                session.close()

                # JavaScript로 쿼리 파라미터 제거하고 리다이렉트
                st.markdown("""
                    <script>
                    window.location.href = window.location.origin + window.location.pathname;
                    </script>
                """, unsafe_allow_html=True)
                st.success("로그인 성공! 페이지를 새로고침합니다...")
                st.stop()

            except Exception as e:
                st.error(f"사용자 정보 저장 중 오류: {e}")
                session.rollback()
                session.close()
                st.session_state.login_processed = False
        else:
            st.error("로그인에 실패했습니다. 다시 시도해주세요.")
            st.session_state.login_processed = False

    # 실패 시에도 리다이렉트
    st.markdown("""
        <script>
        setTimeout(function() {
            window.location.href = window.location.origin + window.location.pathname;
        }, 2000);
        </script>
    """, unsafe_allow_html=True)
    st.stop()

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

    # 카카오 로그인 버튼
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        kakao_login_url = get_kakao_login_url()

        st.markdown(f"""
        <a href="{kakao_login_url}" target="_self" style="text-decoration: none;">
            <div style="
                width: 100%;
                background-color: #FEE500;
                color: #000000;
                text-align: center;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 12px;
                cursor: pointer;
                font-weight: bold;
                border: none;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            ">
                🟡 카카오톡으로 로그인
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.stop()

# ===== 메인 앱 (로그인 후) =====

# 사이드바 - 사용자 정보 및 메뉴
with st.sidebar:
    st.markdown(f"""
    ### 👤 {st.session_state.nickname}님
    """)

    if st.button("🚪 로그아웃"):
        # 세션 클리어
        st.session_state.is_logged_in = False
        st.session_state.user_id = None
        st.session_state.kakao_id = None
        st.session_state.nickname = None
        st.session_state.login_processed = False
        st.rerun()

    st.markdown("---")

    # 메뉴
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

    # 생성할 조합 수 선택
    num_sets = st.slider("생성할 조합 수", 1, 5, 1)

    if st.button("🎲 번호 생성하기"):
        with st.spinner("번호 생성 중..."):
            numbers_list = []
            labels = ['A', 'B', 'C', 'D', 'E']

            for i in range(num_sets):
                numbers = generate_numbers()
                numbers_list.append(numbers)

                # 화면에 표시
                st.markdown(f"**{labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

            # DB에 저장
            session = SessionLocal()
            try:
                numbers_dict = {labels[i]: numbers_list[i] for i in range(num_sets)}

                recommended = RecommendedNumber(
                    user_id=st.session_state.user_id,
                    numbers=numbers_dict
                )
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
    st.header("📱 QR 코드 URL 입력")

    qr_url = st.text_input(
        "QR URL을 입력하세요",
        placeholder="https://m.dhlottery.co.kr/qr.do?method=winQr&v=..."
    )

    if st.button("🔍 분석하기") and qr_url:
        with st.spinner("QR 분석 중..."):
            result = parse_qr_url(qr_url)

            if result:
                draw_number = result['draw_number']
                numbers_list = result['numbers']

                st.success(f"✅ {draw_number}회차 QR 분석 완료!")

                st.markdown("### 📊 분석 결과")
                st.markdown(f"**회차:** {draw_number}회")

                st.markdown("**파싱된 번호:**")
                labels = ['A', 'B', 'C', 'D', 'E']
                for i, numbers in enumerate(numbers_list):
                    if i < len(labels):
                        st.markdown(f"{labels[i]}조합: {' '.join([f'{n:02d}' for n in numbers])}")

                # 구매기록 저장 버튼
                if st.button("💾 구매기록 저장"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: numbers_list[i] for i in range(len(numbers_list))}

                        purchased = PurchasedNumber(
                            user_id=st.session_state.user_id,
                            draw_number=draw_number,
                            numbers=numbers_dict
                        )
                        session.add(purchased)
                        session.commit()

                        st.success("✅ 구매기록이 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()

                # 제외 번호 추천
                st.markdown("---")
                st.markdown("### 🎲 이 번호들 제외하고 5개 조합 추천")

                # 모든 번호 추출 및 중복 제거
                all_numbers = set()
                for numbers in numbers_list:
                    all_numbers.update(numbers)

                st.markdown(f"**제외된 번호:** {' '.join([f'{n:02d}' for n in sorted(all_numbers)])}")

                # 5개 조합 생성
                recommended_sets = []
                for i in range(5):
                    numbers = generate_numbers(exclude=all_numbers)
                    recommended_sets.append(numbers)
                    st.markdown(f"**추천 {labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

                # 추천번호 저장 버튼
                if st.button("💾 추천번호 5개 모두 저장"):
                    session = SessionLocal()
                    try:
                        numbers_dict = {labels[i]: recommended_sets[i] for i in range(5)}

                        recommended = RecommendedNumber(
                            user_id=st.session_state.user_id,
                            numbers=numbers_dict
                        )
                        session.add(recommended)
                        session.commit()

                        st.success("✅ 추천번호가 히스토리에 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                        session.rollback()
                    finally:
                        session.close()
            else:
                st.error("❌ QR URL 형식이 올바르지 않습니다.")

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
                # 구매 기록 확인
                purchases = session.query(PurchasedNumber)\
                    .filter_by(user_id=st.session_state.user_id)\
                    .all()

                # 추천 기록 확인
                recommendations = session.query(RecommendedNumber)\
                    .filter_by(user_id=st.session_state.user_id)\
                    .all()

                total_win = 0
                total_lose = 0

                # 구매 기록 당첨 확인
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

                # 추천 기록 당첨 확인 (회차가 있는 것만)
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