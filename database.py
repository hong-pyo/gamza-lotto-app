from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
import os

Base = declarative_base()

# 데이터베이스 엔진 및 세션 설정
DATABASE_URL = "sqlite:///./lotto.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테이블 생성
Base.metadata.create_all(bind=engine)


class User(Base):
    """사용자 정보"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kakao_id = Column(BigInteger, unique=True, nullable=False)  # 카카오 고유 ID (정수형)
    nickname = Column(String(100), nullable=False)  # 닉네임
    created_at = Column(DateTime, default=datetime.now, nullable=False)  # 가입일시

    # 관계 설정
    recommended_numbers = relationship("RecommendedNumber", back_populates="user", cascade="all, delete-orphan")
    purchased_numbers = relationship("PurchasedNumber", back_populates="user", cascade="all, delete-orphan")


class RecommendedNumber(Base):
    """추천 번호 히스토리"""
    __tablename__ = 'recommended_numbers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 사용자 ID
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    draw_number = Column(Integer, nullable=True)  # 회차 (null 허용)
    numbers = Column(Text, nullable=False)  # JSON 형태로 저장
    winning_status = Column(String(20), default="미확인", nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="recommended_numbers")

    def get_numbers_dict(self):
        """JSON 문자열을 딕셔너리로 변환"""
        return json.loads(self.numbers)

    def set_numbers_dict(self, numbers_dict):
        """딕셔너리를 JSON 문자열로 저장"""
        self.numbers = json.dumps(numbers_dict, ensure_ascii=False)


class PurchasedNumber(Base):
    """구매 기록"""
    __tablename__ = 'purchased_numbers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 사용자 ID
    purchased_at = Column(DateTime, default=datetime.now, nullable=False)
    draw_number = Column(Integer, nullable=False)  # 회차
    numbers = Column(Text, nullable=False)  # JSON 형태로 저장
    winning_status = Column(String(20), default="미확인", nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="purchased_numbers")

    def get_numbers_dict(self):
        """JSON 문자열을 딕셔너리로 변환"""
        return json.loads(self.numbers)

    def set_numbers_dict(self, numbers_dict):
        """딕셔너리를 JSON 문자열로 저장"""
        self.numbers = json.dumps(numbers_dict, ensure_ascii=False)


class DrawResult(Base):
    """회차별 당첨번호 캐시"""
    __tablename__ = 'draw_results'

    draw_number = Column(Integer, primary_key=True)
    winning_numbers = Column(Text, nullable=False)  # JSON 배열
    bonus_number = Column(Integer, nullable=False)
    fetched_at = Column(DateTime, default=datetime.now, nullable=False)

    def get_winning_numbers(self):
        """JSON 문자열을 리스트로 변환"""
        return json.loads(self.winning_numbers)

    def set_winning_numbers(self, numbers_list):
        """리스트를 JSON 문자열로 저장"""
        self.winning_numbers = json.dumps(numbers_list)


def migrate_existing_data(session):
    """
    기존 데이터 마이그레이션
    user_id가 없는 기존 데이터를 처리합니다.
    """
    try:
        # 기존 데이터가 있는지 확인
        engine = session.bind

        # 테이블 존재 여부 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)

        if 'recommended_numbers' in inspector.get_table_names():
            # user_id 컬럼이 없는 기존 데이터 확인
            try:
                # 컬럼 확인
                columns = [col['name'] for col in inspector.get_columns('recommended_numbers')]

                if 'user_id' not in columns:
                    print("기존 데이터베이스 발견: 마이그레이션이 필요합니다.")
                    print("새로운 스키마로 데이터베이스를 재생성합니다.")
                    # 기존 테이블 삭제하고 새로 생성
                    Base.metadata.drop_all(engine)
                    Base.metadata.create_all(engine)
                    print("마이그레이션 완료: 새로운 데이터베이스가 생성되었습니다.")
            except Exception as e:
                print(f"마이그레이션 체크 중 오류: {e}")
    except Exception as e:
        print(f"마이그레이션 오류: {e}")


def init_db(db_path='lotto.db'):
    """데이터베이스 초기화 및 세션 생성"""
    engine_local = create_engine(f'sqlite:///{db_path}', echo=False)

    # 테이블 생성
    Base.metadata.create_all(engine_local)

    # 세션 생성
    Session = sessionmaker(bind=engine_local)
    session = Session()

    # 마이그레이션 실행
    migrate_existing_data(session)

    return session


def get_session(db_path='lotto.db'):
    """데이터베이스 세션 가져오기"""
    engine_local = create_engine(f'sqlite:///{db_path}', echo=False)
    Session = sessionmaker(bind=engine_local)
    return Session()


def get_or_create_user(session, kakao_id, nickname):
    """
    사용자 조회 또는 생성

    Args:
        session: 데이터베이스 세션
        kakao_id: 카카오 고유 ID
        nickname: 닉네임

    Returns:
        User: 사용자 객체
    """
    # 기존 사용자 확인
    user = session.query(User).filter_by(kakao_id=kakao_id).first()

    if user:
        # 닉네임 업데이트 (변경되었을 수 있음)
        user.nickname = nickname
        session.commit()
        return user
    else:
        # 새 사용자 생성
        new_user = User(
            kakao_id=kakao_id,
            nickname=nickname,
            created_at=datetime.now()
        )
        session.add(new_user)
        session.commit()
        return new_user