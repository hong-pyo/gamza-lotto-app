"""
로또 번호 관리 앱 - Streamlit (카카오 로그인 포함)
"""
import streamlit as st
from datetime import datetime
import json

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


# ===== 콜백 처리 =====
# URL에서 code 파라미터 확인 (카카오 인증 후 리다이렉트)
if not st.session_state.is_logged_in:
    # query_params 가져오기
    query_params = st.query_params

    # 로그인 처리 플래그 초기화
    if 'login_processed' not in st.session_state:
        st.session_state.login_processed = False

    if 'code' in query_params and not st.session_state.is_logged_in:
        auth_code = query_params['code']

        with st.spinner("로그인 중..."):
            # 카카오 로그인 처리
            user_info = kakao_login(auth_code)

            if user_info:
                # DB에서 사용자 조회 또는 생성
                session = SessionLocal()
                try:
                    # get_or_create_user 함수 사용
                    user = get_or_create_user(session, user_info['kakao_id'], user_info['nickname'])

                    # 세션에 사용자 정보 저장
                    st.session_state.is_logged_in = True
                    st.session_state.user_id = user.id
                    st.session_state.kakao_id = user.kakao_id
                    st.session_state.nickname = user.nickname

                    session.close()

                    # 성공 메시지
                    st.success("로그인 성공!")

                    # 쿼리 파라미터 제거 후 리다이렉트
                    st.query_params.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"로그인 처리 중 오류: {e}")
                    session.rollback()
                    session.close()
            else:
                st.error("로그인에 실패했습니다. 다시 시도해주세요.")
                # 쿼리 파라미터 제거
                st.query_params.clear()
                st.rerun()


# ===== 로그인 페이지 =====
if not st.session_state.is_logged_in:
    st.title("🎲 로또 번호 관리 앱")
    st.markdown("---")

    st.markdown("""
    ### 환영합니다!

    로또 번호를 관리하고 당첨을 확인할 수 있는 앱입니다.

    **주요 기능:**
    - 🎲 랜덤 번호 생성
    - 📱 QR 코드 분석
    - 📋 구매 기록 관리
    - 📊 추천 히스토리
    - 🎯 당첨 확인

    로그인하여 시작하세요!
    """)

    st.markdown("---")

    # 카카오 로그인 버튼
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        kakao_login_url = get_kakao_login_url()

        st.markdown(f"""
        <a href="{kakao_login_url}" target="_self">
            <button style="
                background-color: #FEE500;
                color: #000000;
                font-weight: bold;
                font-size: 18px;
                padding: 15px 30px;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            ">
                🟡 카카오톡으로 로그인
            </button>
        </a>
        """, unsafe_allow_html=True)

    st.stop()


# ===== 로그인 후 메인 앱 =====

# 사이드바 프로필 및 로그아웃
st.sidebar.markdown(f"### 👤 {st.session_state.nickname}")

if st.sidebar.button("로그아웃", type="secondary", use_container_width=True):
    # 세션 클리어
    st.session_state.is_logged_in = False
    st.session_state.user_id = None
    st.session_state.kakao_id = None
    st.session_state.nickname = None
    st.rerun()

st.sidebar.markdown("---")

# 사이드바 메뉴
st.sidebar.title("🎰 로또 번호 관리")
menu = st.sidebar.radio(
    "메뉴 선택",
    ["🎲 번호 생성", "📱 QR 입력", "📋 구매 기록", "📊 추천 히스토리", "🎯 당첨 확인"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Gamza Lotto App v2.0")


# ===== 1. 번호 생성 페이지 =====
if menu == "🎲 번호 생성":
    st.title("🎲 로또 번호 생성")
    st.markdown("랜덤으로 로또 번호를 생성합니다.")

    # 생성할 조합 수 선택
    count = st.slider("생성할 조합 수", min_value=1, max_value=5, value=1, step=1)

    if st.button("🎲 번호 생성하기", type="primary", use_container_width=True):
        combinations = generate_lotto_numbers(count)

        st.success(f"{count}개의 조합이 생성되었습니다!")

        # 생성된 번호 표시
        cols = st.columns(count)
        for idx, (label, numbers) in enumerate(combinations.items()):
            with cols[idx]:
                st.markdown(f"### {label}조합")
                st.markdown(format_numbers_with_emoji(numbers))

        # 히스토리에 자동 저장 (사용자별)
        try:
            new_record = RecommendedNumber(
                user_id=st.session_state.user_id,  # 현재 로그인한 사용자
                created_at=datetime.now(),
                draw_number=None,
                numbers=json.dumps(combinations, ensure_ascii=False),
                winning_status="미확인"
            )
            session.add(new_record)
            session.commit()
            st.info("✅ 생성된 번호가 추천 히스토리에 자동 저장되었습니다.")
        except Exception as e:
            session.rollback()
            st.error(f"저장 중 오류 발생: {e}")


# ===== 2. QR 입력 페이지 =====
# ===== 2. QR 입력 =====
elif menu == "📱 QR 입력":
    st.header("📱 QR 코드 스캔")

    # 탭으로 구분
    tab1, tab2 = st.tabs(["📷 카메라로 스캔", "⌨️ URL 직접 입력"])

    with tab1:
        st.markdown("### 📷 카메라로 QR 코드 스캔")
        st.info("🎯 QR 코드를 카메라에 비추면 자동으로 인식됩니다!")

        # QR 스캐너 HTML/JavaScript
        qr_scanner_html = """
        <div style="max-width: 500px; margin: 0 auto;">
            <div id="qr-reader" style="width: 100%; border-radius: 10px; overflow: hidden;"></div>
            <div id="qr-result" style="margin-top: 20px; display: none;">
                <div style="padding: 15px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; color: #155724;">
                    <strong>✅ QR 코드 인식 성공!</strong>
                    <div id="qr-url" style="margin-top: 10px; word-break: break-all;"></div>
                </div>
            </div>
            <div id="qr-error" style="margin-top: 20px; display: none;">
                <div style="padding: 15px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; color: #721c24;">
                    <strong>❌ 카메라 접근 불가</strong>
                    <div style="margin-top: 10px;">카메라 권한을 허용해주세요.</div>
                </div>
            </div>
        </div>

        <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
        <script>
        let html5QrCode = null;
        let isScanning = false;

        function onScanSuccess(decodedText, decodedResult) {
            if (!isScanning) return;

            console.log(`QR Code detected: ${decodedText}`);

            // QR 코드 인식 성공 표시
            document.getElementById('qr-result').style.display = 'block';
            document.getElementById('qr-url').textContent = decodedText;

            // Streamlit에 데이터 전달
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: decodedText
            }, '*');

            // 스캔 중지
            if (html5QrCode) {
                html5QrCode.stop().then(() => {
                    isScanning = false;
                    document.getElementById('qr-reader').innerHTML = '<div style="padding: 20px; text-align: center; color: #28a745;">✅ QR 코드 인식 완료!</div>';
                }).catch(err => {
                    console.log('Stop scanning error:', err);
                });
            }
        }

        function onScanError(errorMessage) {
            // 스캔 실패는 무시 (계속 시도)
        }

        // QR 스캐너 시작
        function startScanner() {
            html5QrCode = new Html5Qrcode("qr-reader");
            isScanning = true;

            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            };

            // 모바일: 후면 카메라 우선
            html5QrCode.start(
                { facingMode: "environment" },
                config,
                onScanSuccess,
                onScanError
            ).catch(err => {
                console.log('Camera start error:', err);
                document.getElementById('qr-error').style.display = 'block';

                // 후면 카메라 실패 시 전면 카메라 시도
                html5QrCode.start(
                    { facingMode: "user" },
                    config,
                    onScanSuccess,
                    onScanError
                ).catch(err2 => {
                    console.log('Front camera also failed:', err2);
                });
            });
        }

        // 페이지 로드 시 자동 시작
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', startScanner);
        } else {
            startScanner();
        }
        </script>
        """

        # HTML 컴포넌트로 렌더링
        scanned_url = st.components.v1.html(qr_scanner_html, height=600)

        # QR 코드가 인식되면 자동으로 분석
        if scanned_url:
            st.markdown("---")
            st.markdown("### 📊 QR 분석 중...")

            with st.spinner("분석 중..."):
                result = parse_qr_url(scanned_url)

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
                    if st.button("💾 구매기록 저장", key="save_qr_scan"):
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

                    # 제외 번호 추천
                    st.markdown("---")
                    st.markdown("### 🎲 이 번호들 제외하고 5개 조합 추천")

                    # 모든 번호 추출 및 중복 제거
                    all_numbers = set()
                    for numbers in numbers_list:
                        all_numbers.update(numbers)

                    st.markdown(f"**제외된 번호:** {' '.join([f'{n:02d}' for n in sorted(all_numbers)])}")

                    # 5개 조합 생성
                    if st.button("🎲 제외 번호 기반 추천 생성", key="gen_excluding"):
                        from utils import generate_lotto_numbers

                        recommended_sets = []
                        for i in range(5):
                            numbers = generate_lotto_numbers(exclude=all_numbers)
                            recommended_sets.append(numbers)
                            st.markdown(f"**추천 {labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

                        # 추천번호 저장 버튼
                        if st.button("💾 추천번호 5개 모두 저장", key="save_recommended"):
                            session = SessionLocal()
                            try:
                                numbers_dict = {labels[i]: recommended_sets[i] for i in range(5)}

                                recommended = RecommendedNumber(
                                    user_id=st.session_state.user_id
                                )
                                recommended.numbers = numbers_dict

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

    with tab2:
        st.markdown("### ⌨️ URL 직접 입력")

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

                    # 제외 번호 추천 (위와 동일)
                    st.markdown("---")
                    st.markdown("### 🎲 이 번호들 제외하고 5개 조합 추천")

                    all_numbers = set()
                    for numbers in numbers_list:
                        all_numbers.update(numbers)

                    st.markdown(f"**제외된 번호:** {' '.join([f'{n:02d}' for n in sorted(all_numbers)])}")

                    if st.button("🎲 제외 번호 기반 추천 생성", key="gen_excluding_manual"):
                        from utils import generate_lotto_numbers

                        recommended_sets = []
                        for i in range(5):
                            numbers = generate_lotto_numbers(exclude=all_numbers)
                            recommended_sets.append(numbers)
                            st.markdown(f"**추천 {labels[i]}조합:** " + " ".join([f"⚪ {n:02d}" for n in numbers]))

                        if st.button("💾 추천번호 5개 모두 저장", key="save_recommended_manual"):
                            session = SessionLocal()
                            try:
                                numbers_dict = {labels[i]: recommended_sets[i] for i in range(5)}

                                recommended = RecommendedNumber(
                                    user_id=st.session_state.user_id
                                )
                                recommended.numbers = numbers_dict

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


# ===== 3. 구매 기록 페이지 =====
elif menu == "📋 구매 기록":
    st.title("📋 구매 기록")
    st.markdown("QR로 스캔한 구매 번호 기록을 관리합니다.")

    # 구매 기록 조회 (현재 사용자만)
    purchases = session.query(PurchasedNumber).filter_by(user_id=st.session_state.user_id).order_by(PurchasedNumber.purchased_at.desc()).all()

    if not purchases:
        st.info("📭 구매 기록이 없습니다.")
    else:
        # 회차 필터
        all_draws = sorted(list(set([p.draw_number for p in purchases])), reverse=True)
        selected_draw = st.selectbox(
            "회차 필터",
            ["전체"] + [f"{d}회" for d in all_draws]
        )

        # 필터링
        if selected_draw != "전체":
            draw_num = int(selected_draw.replace("회", ""))
            filtered_purchases = [p for p in purchases if p.draw_number == draw_num]
        else:
            filtered_purchases = purchases

        st.markdown(f"**총 {len(filtered_purchases)}개의 구매 기록**")

        # 삭제할 항목 선택
        delete_ids = []

        for purchase in filtered_purchases:
            with st.container():
                col1, col2 = st.columns([0.05, 0.95])

                with col1:
                    if st.checkbox("", key=f"purchase_{purchase.id}"):
                        delete_ids.append(purchase.id)

                with col2:
                    st.markdown(f"**{purchase.draw_number}회** | {purchase.purchased_at.strftime('%Y-%m-%d %H:%M')}")

                    combinations = json.loads(purchase.numbers)
                    for label, numbers in combinations.items():
                        st.markdown(f"{label}조합: {format_numbers_with_emoji(numbers)}")

                    # 당첨여부 표시
                    if purchase.winning_status == "미확인":
                        st.caption("⏳ 당첨여부: 미확인")
                    elif purchase.winning_status == "낙첨":
                        st.caption("❌ 낙첨")
                    else:
                        st.caption(f"🎉 {purchase.winning_status} 당첨!")

                st.markdown("---")

        # 선택 삭제 버튼
        if delete_ids:
            if st.button(f"🗑️ 선택한 {len(delete_ids)}개 항목 삭제", type="secondary"):
                try:
                    for del_id in delete_ids:
                        purchase = session.query(PurchasedNumber).filter_by(id=del_id, user_id=st.session_state.user_id).first()
                        if purchase:
                            session.delete(purchase)
                    session.commit()
                    st.success(f"✅ {len(delete_ids)}개 항목이 삭제되었습니다.")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ 삭제 중 오류 발생: {e}")


# ===== 4. 추천 히스토리 페이지 =====
elif menu == "📊 추천 히스토리":
    st.title("📊 추천 히스토리")
    st.markdown("생성했던 추천 번호 목록을 관리합니다.")

    # 정렬 옵션
    sort_option = st.selectbox(
        "정렬 방식",
        ["최신순", "오래된순", "당첨순"]
    )

    # 히스토리 조회 (현재 사용자만)
    if sort_option == "최신순":
        histories = session.query(RecommendedNumber).filter_by(user_id=st.session_state.user_id).order_by(RecommendedNumber.created_at.desc()).all()
    elif sort_option == "오래된순":
        histories = session.query(RecommendedNumber).filter_by(user_id=st.session_state.user_id).order_by(RecommendedNumber.created_at.asc()).all()
    else:  # 당첨순
        # 당첨 등수를 숫자로 변환하여 정렬
        histories = session.query(RecommendedNumber).filter_by(user_id=st.session_state.user_id).all()
        def sort_key(h):
            if h.winning_status == "미확인":
                return 10
            elif h.winning_status == "낙첨":
                return 9
            else:
                return int(h.winning_status.replace("등", ""))
        histories = sorted(histories, key=sort_key)

    if not histories:
        st.info("📭 추천 히스토리가 없습니다.")
    else:
        st.markdown(f"**총 {len(histories)}개의 추천 기록**")

        # 삭제할 항목 선택
        delete_ids = []

        for history in histories:
            with st.container():
                col1, col2 = st.columns([0.05, 0.95])

                with col1:
                    if st.checkbox("", key=f"history_{history.id}"):
                        delete_ids.append(history.id)

                with col2:
                    # 생성일시
                    st.markdown(f"**생성일시:** {history.created_at.strftime('%Y-%m-%d %H:%M')}")

                    # 회차
                    if history.draw_number:
                        st.markdown(f"**회차:** {history.draw_number}회")
                    else:
                        st.markdown("**회차:** 미배정")

                    # 번호 표시
                    combinations = json.loads(history.numbers)
                    for label, numbers in combinations.items():
                        st.markdown(f"{label}조합: {format_numbers_with_emoji(numbers)}")

                    # 당첨여부 표시
                    if history.winning_status == "미확인":
                        st.caption("⏳ 당첨여부: 미확인")
                    elif history.winning_status == "낙첨":
                        st.caption("❌ 낙첨")
                    else:
                        st.caption(f"🎉 {history.winning_status} 당첨!")

                st.markdown("---")

        # 선택 삭제 버튼
        if delete_ids:
            if st.button(f"🗑️ 선택한 {len(delete_ids)}개 항목 삭제", type="secondary"):
                try:
                    for del_id in delete_ids:
                        history = session.query(RecommendedNumber).filter_by(id=del_id, user_id=st.session_state.user_id).first()
                        if history:
                            session.delete(history)
                    session.commit()
                    st.success(f"✅ {len(delete_ids)}개 항목이 삭제되었습니다.")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ 삭제 중 오류 발생: {e}")


# ===== 5. 당첨 확인 페이지 =====
elif menu == "🎯 당첨 확인":
    st.title("🎯 당첨 확인")
    st.markdown("동행복권 사이트에서 당첨번호를 조회하고 구매 기록과 비교합니다.")

    # 회차 입력
    draw_input = st.number_input(
        "회차 번호 입력",
        min_value=1,
        max_value=9999,
        value=1100,
        step=1,
        help="조회할 회차 번호를 입력하세요."
    )

    if st.button("🔍 당첨번호 조회하기", type="primary", use_container_width=True):
        with st.spinner("당첨번호 조회 중..."):
            # 캐시 확인
            cached = session.query(DrawResult).filter_by(draw_number=draw_input).first()

            if cached:
                winning_numbers = json.loads(cached.winning_numbers)
                bonus_number = cached.bonus_number
                st.info("💾 캐시된 데이터를 사용합니다.")
            else:
                # 크롤링
                winning_numbers, bonus_number = fetch_winning_numbers(draw_input)

                if winning_numbers is None:
                    st.error("❌ 당첨번호를 조회할 수 없습니다. 회차를 확인해주세요.")
                else:
                    # 캐시 저장
                    try:
                        new_result = DrawResult(
                            draw_number=draw_input,
                            winning_numbers=json.dumps(winning_numbers),
                            bonus_number=bonus_number,
                            fetched_at=datetime.now()
                        )
                        session.add(new_result)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        print(f"캐시 저장 오류: {e}")

            # 당첨번호 표시
            if winning_numbers:
                st.success(f"✅ {draw_input}회 당첨번호")
                st.markdown(f"**당첨번호:** {format_winning_numbers_with_emoji(winning_numbers)}")
                st.markdown(f"**보너스:** 🎱 {format_number(bonus_number)}")

                st.session_state.current_winning = {
                    "draw_number": draw_input,
                    "winning_numbers": winning_numbers,
                    "bonus_number": bonus_number
                }

    st.markdown("---")

    # 전체 기록 일괄 확인
    if st.button("📋 전체 기록 일괄 확인", use_container_width=True):
        with st.spinner("전체 기록 확인 중..."):
            # 모든 구매 기록 + 추천 히스토리 조회 (현재 사용자만)
            purchases = session.query(PurchasedNumber).filter_by(user_id=st.session_state.user_id).all()
            recommendations = session.query(RecommendedNumber).filter_by(user_id=st.session_state.user_id).all()

            total_checked = 0
            total_winning = 0
            total_losing = 0

            # 구매 기록 확인
            for purchase in purchases:
                draw_num = purchase.draw_number

                # 당첨번호 조회 (캐시 또는 크롤링)
                cached = session.query(DrawResult).filter_by(draw_number=draw_num).first()

                if cached:
                    winning_numbers = json.loads(cached.winning_numbers)
                    bonus_number = cached.bonus_number
                else:
                    winning_numbers, bonus_number = fetch_winning_numbers(draw_num)

                    if winning_numbers:
                        try:
                            new_result = DrawResult(
                                draw_number=draw_num,
                                winning_numbers=json.dumps(winning_numbers),
                                bonus_number=bonus_number,
                                fetched_at=datetime.now()
                            )
                            session.add(new_result)
                            session.commit()
                        except:
                            session.rollback()

                if winning_numbers:
                    # 각 조합 확인
                    combinations = json.loads(purchase.numbers)
                    best_result = "낙첨"

                    for label, numbers in combinations.items():
                        result = check_winning(numbers, winning_numbers, bonus_number)
                        if result != "낙첨":
                            # 최고 등수 저장
                            if best_result == "낙첨":
                                best_result = result
                            elif int(result.replace("등", "")) < int(best_result.replace("등", "")):
                                best_result = result

                    purchase.winning_status = best_result
                    total_checked += 1

                    if best_result != "낙첨":
                        total_winning += 1
                    else:
                        total_losing += 1

            # 추천 히스토리 중 회차가 배정된 것만 확인
            for recommendation in recommendations:
                if recommendation.draw_number:
                    draw_num = recommendation.draw_number

                    # 당첨번호 조회
                    cached = session.query(DrawResult).filter_by(draw_number=draw_num).first()

                    if cached:
                        winning_numbers = json.loads(cached.winning_numbers)
                        bonus_number = cached.bonus_number
                    else:
                        winning_numbers, bonus_number = fetch_winning_numbers(draw_num)

                        if winning_numbers:
                            try:
                                new_result = DrawResult(
                                    draw_number=draw_num,
                                    winning_numbers=json.dumps(winning_numbers),
                                    bonus_number=bonus_number,
                                    fetched_at=datetime.now()
                                )
                                session.add(new_result)
                                session.commit()
                            except:
                                session.rollback()

                    if winning_numbers:
                        # 각 조합 확인
                        combinations = json.loads(recommendation.numbers)
                        best_result = "낙첨"

                        for label, numbers in combinations.items():
                            result = check_winning(numbers, winning_numbers, bonus_number)
                            if result != "낙첨":
                                if best_result == "낙첨":
                                    best_result = result
                                elif int(result.replace("등", "")) < int(best_result.replace("등", "")):
                                    best_result = result

                        recommendation.winning_status = best_result
                        total_checked += 1

                        if best_result != "낙첨":
                            total_winning += 1
                        else:
                            total_losing += 1

            session.commit()

            st.success(f"✅ 총 {total_checked}개 기록 확인 완료!")
            st.markdown(f"**🎉 당첨:** {total_winning}건")
            st.markdown(f"**❌ 낙첨:** {total_losing}건")

    st.markdown("---")

    # 당첨 내역 표시
    if 'current_winning' in st.session_state:
        winning_info = st.session_state.current_winning
        draw_num = winning_info['draw_number']

        st.markdown("### 📊 당첨 내역")

        # 구매 기록 확인 (현재 사용자만)
        purchases = session.query(PurchasedNumber).filter_by(draw_number=draw_num, user_id=st.session_state.user_id).all()

        if purchases:
            st.markdown("#### 🎫 구매 기록")
            for purchase in purchases:
                combinations = json.loads(purchase.numbers)

                for label, numbers in combinations.items():
                    result = check_winning(
                        numbers,
                        winning_info['winning_numbers'],
                        winning_info['bonus_number']
                    )

                    if result == "낙첨":
                        st.markdown(f"❌ **{label}조합:** {format_numbers_with_emoji(numbers)} - 낙첨")
                    else:
                        st.markdown(f"🎉 **{label}조합:** {format_numbers_with_emoji(numbers)} - **{result}** 당첨!")

        # 추천 히스토리 확인 (현재 사용자만)
        recommendations = session.query(RecommendedNumber).filter_by(draw_number=draw_num, user_id=st.session_state.user_id).all()

        if recommendations:
            st.markdown("#### 💡 추천 번호")
            for recommendation in recommendations:
                combinations = json.loads(recommendation.numbers)

                for label, numbers in combinations.items():
                    result = check_winning(
                        numbers,
                        winning_info['winning_numbers'],
                        winning_info['bonus_number']
                    )

                    if result == "낙첨":
                        st.markdown(f"❌ **{label}조합:** {format_numbers_with_emoji(numbers)} - 낙첨")
                    else:
                        st.markdown(f"🎉 **{label}조합:** {format_numbers_with_emoji(numbers)} - **{result}** 당첨!")

        if not purchases and not recommendations:
            st.info("해당 회차의 기록이 없습니다.")
