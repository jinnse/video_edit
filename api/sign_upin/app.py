from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
import json
import os
import requests
from functools import wraps
from jose import jwt
import datetime

app = Flask(__name__)
CORS(app, origins=["https://www.videofinding.com"])

# AWS Cognito 설정
COGNITO_CONFIG = {
    'user_pool_id': os.getenv('COGNITO_USER_POOL_ID', 'ap-northeast-2_xxxxxxxxx'),
    'client_id': os.getenv('COGNITO_CLIENT_ID', 'xxxxxxxxxxxxxxxxxxxxxxxxxx'),
    'client_secret': os.getenv('COGNITO_CLIENT_SECRET', ''),
    'region': os.getenv('AWS_REGION', 'ap-northeast-2')
}

# 비밀번호 유효성 검사 함수
def validate_password(password):
    """비밀번호가 Cognito 정책을 만족하는지 검사"""
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다"
    
    if not any(c.isupper() for c in password):
        return False, "비밀번호는 대문자를 포함해야 합니다"
    
    if not any(c.islower() for c in password):
        return False, "비밀번호는 소문자를 포함해야 합니다"
    
    if not any(c.isdigit() for c in password):
        return False, "비밀번호는 숫자를 포함해야 합니다"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "비밀번호는 특수문자를 포함해야 합니다"
    
    return True, "비밀번호가 유효합니다"

# Cognito 클라이언트 초기화
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_CONFIG['region'])

# JWT 토큰 검증을 위한 공개키 가져오기
def get_cognito_public_keys():
    try:
        url = f"https://cognito-idp.{COGNITO_CONFIG['region']}.amazonaws.com/{COGNITO_CONFIG['user_pool_id']}/.well-known/jwks.json"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"공개키 가져오기 오류: {e}")
        return None

# JWT 토큰 검증 데코레이터 (Cognito용)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(' ')[1]  # Bearer 토큰에서 실제 토큰 추출
            
            # Cognito JWT 토큰 검증
            public_keys = get_cognito_public_keys()
            if not public_keys:
                return jsonify({'message': 'Unable to verify token!'}), 401
            
            # 토큰 헤더에서 kid 추출
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            # 해당 kid의 공개키 찾기
            public_key = None
            for key in public_keys['keys']:
                if key['kid'] == kid:
                    public_key = key
                    break
            
            if not public_key:
                return jsonify({'message': 'Invalid token!'}), 401
            
            # 토큰 검증
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=COGNITO_CONFIG['client_id'],
                issuer=f"https://cognito-idp.{COGNITO_CONFIG['region']}.amazonaws.com/{COGNITO_CONFIG['user_pool_id']}"
            )
            
            current_user = payload.get('cognito:username') or payload.get('username')
            return f(current_user, *args, **kwargs)
            
        except Exception as e:
            print(f"토큰 검증 오류: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
    return decorated

# 회원가입 요청 API (이메일 인증 코드 전송)
@app.route('/api/auth/send-verification', methods=['POST'])
def send_verification():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': '모든 필드를 입력해주세요'}), 400
        
        # 간단한 이메일 형식 검증
        if '@' not in email or '.' not in email:
            return jsonify({'error': '올바른 이메일 형식을 입력해주세요'}), 400
        
        # 비밀번호 유효성 검사
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400

        try:
            # Cognito에 실제 사용자 생성 (이메일 확인 코드 자동 전송)
            response = cognito_client.sign_up(
                ClientId=COGNITO_CONFIG['client_id'],
                Username=username,
                Password=password,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': email
                    }
                ]
            )
            
            return jsonify({
                'message': '회원가입 요청이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.',
                'userSub': response['UserSub'],
                'username': username,
                'email': email,
                'requiresConfirmation': True
            }), 200
            
        except cognito_client.exceptions.UsernameExistsException:
            return jsonify({'error': '이미 존재하는 사용자명입니다'}), 409
        except cognito_client.exceptions.InvalidPasswordException as e:
            return jsonify({'error': f'비밀번호가 정책을 만족하지 않습니다: {str(e)}'}), 400
        except cognito_client.exceptions.InvalidParameterException as e:
            # 이메일 중복 체크
            if 'email' in str(e).lower() and 'exists' in str(e).lower():
                return jsonify({'error': '이미 존재하는 이메일입니다'}), 409
            return jsonify({'error': f'잘못된 매개변수: {str(e)}'}), 400
        except Exception as e:
            # 일반적인 예외에서도 이메일 중복 체크
            if 'email' in str(e).lower() and ('exists' in str(e).lower() or 'duplicate' in str(e).lower()):
                return jsonify({'error': '이미 존재하는 이메일입니다'}), 409
            return jsonify({'error': f'Cognito 오류: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 이메일 인증 코드 확인 API (회원가입 완료)
@app.route('/api/auth/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        username = data.get('username')
        code = data.get('code')
        
        if not username or not code:
            return jsonify({'error': '사용자명과 인증 코드를 입력해주세요'}), 400
        
        try:
            # Cognito에서 이메일 확인 코드 확인 (회원가입 완료)
            response = cognito_client.confirm_sign_up(
                ClientId=COGNITO_CONFIG['client_id'],
                Username=username,
                ConfirmationCode=code
            )
            
            return jsonify({
                'message': '회원가입이 완료되었습니다! 이제 로그인할 수 있습니다.',
                'username': username,
                'verified': True
            }), 200
            
        except cognito_client.exceptions.CodeMismatchException:
            return jsonify({'error': '잘못된 인증 코드입니다'}), 400
        except cognito_client.exceptions.ExpiredCodeException:
            return jsonify({'error': '인증 코드가 만료되었습니다'}), 400
        except cognito_client.exceptions.UserNotFoundException:
            return jsonify({'error': '존재하지 않는 사용자입니다'}), 404
        except Exception as e:
            return jsonify({'error': f'인증 코드 확인 실패: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 회원가입 완료 API (이미 이메일 인증이 완료된 사용자)
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': '모든 필드를 입력해주세요'}), 400
        
        # 이미 이메일 인증이 완료된 사용자인지 확인
        try:
            # 사용자 정보 조회 (이미 인증된 사용자만 조회 가능)
            user_response = cognito_client.admin_get_user(
                UserPoolId=COGNITO_CONFIG['user_pool_id'],
                Username=username
            )
            
            # 이메일 인증 상태 확인
            email_verified = False
            for attr in user_response['UserAttributes']:
                if attr['Name'] == 'email_verified' and attr['Value'] == 'true':
                    email_verified = True
                    break
            
            if not email_verified:
                return jsonify({'error': '이메일 인증이 완료되지 않았습니다. 먼저 이메일 인증을 완료해주세요.'}), 400
            
            # 회원가입 완료 처리 (이미 Cognito에서 사용자가 생성되고 이메일 인증이 완료된 상태)
            # 여기서는 추가적인 처리가 필요하다면 수행 (예: 사용자 프로필 정보 저장 등)
            
            return jsonify({
                'message': '회원가입이 완료되었습니다! 로그인 페이지로 이동합니다.',
                'username': username,
                'email': email,
                'success': True
            }), 200
            
        except cognito_client.exceptions.UserNotFoundException:
            return jsonify({'error': '존재하지 않는 사용자입니다. 먼저 이메일 인증을 완료해주세요.'}), 404
        except Exception as e:
            return jsonify({'error': f'사용자 확인 실패: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 이메일 확인 코드 확인 API
@app.route('/api/auth/confirm-signup', methods=['POST'])
def confirm_signup():
    try:
        data = request.get_json()
        username = data.get('username')
        code = data.get('code')
        
        if not username or not code:
            return jsonify({'error': '사용자명과 인증 코드를 입력해주세요'}), 400
        
        try:
            # Cognito에서 이메일 확인 코드 확인
            response = cognito_client.confirm_sign_up(
                ClientId=COGNITO_CONFIG['client_id'],
                Username=username,
                ConfirmationCode=code
            )
            
            return jsonify({
                'message': '이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다.',
                'username': username
            }), 200
            
        except cognito_client.exceptions.CodeMismatchException:
            return jsonify({'error': '잘못된 인증 코드입니다'}), 400
        except cognito_client.exceptions.ExpiredCodeException:
            return jsonify({'error': '인증 코드가 만료되었습니다'}), 400
        except cognito_client.exceptions.UserNotFoundException:
            return jsonify({'error': '존재하지 않는 사용자입니다'}), 404
        except Exception as e:
            return jsonify({'error': f'인증 코드 확인 실패: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 로그인 API (Cognito)
@app.route('/api/auth/signin', methods=['POST'])
def signin():
    try:
        data = request.get_json()
        username = data.get('username')  # ID로 사용
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        try:
            # Cognito 로그인 (ADMIN_USER_PASSWORD_AUTH 사용)
            response = cognito_client.admin_initiate_auth(
                UserPoolId=COGNITO_CONFIG['user_pool_id'],
                ClientId=COGNITO_CONFIG['client_id'],
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            # 로그인 성공
            if 'AuthenticationResult' in response:
                auth_result = response['AuthenticationResult']
                return jsonify({
                    'message': '로그인이 완료되었습니다',
                    'token': auth_result['IdToken'],
                    'refreshToken': auth_result.get('RefreshToken'),
                    'expiresIn': auth_result['ExpiresIn'],
                    'user': {
                        'username': username
                    }
                }), 200
            else:
                # 추가 인증 필요 (예: MFA, 이메일 확인 등)
                return jsonify({
                    'error': '추가 인증이 필요합니다',
                    'challenge': response.get('ChallengeName'),
                    'session': response.get('Session')
                }), 400
                
        except cognito_client.exceptions.NotAuthorizedException:
            return jsonify({'error': '잘못된 사용자명 또는 비밀번호입니다'}), 401
        except cognito_client.exceptions.UserNotConfirmedException:
            return jsonify({'error': '이메일을 확인하여 계정을 활성화해주세요'}), 400
        except cognito_client.exceptions.UserNotFoundException:
            return jsonify({'error': '존재하지 않는 사용자입니다'}), 404
        except Exception as e:
            return jsonify({'error': f'Cognito 오류: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 사용자 정보 조회 API (토큰 필요)
@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    try:
        # Cognito에서 사용자 정보 조회
        response = cognito_client.get_user(
            AccessToken=request.headers.get('Authorization').split(' ')[1]
        )
        
        user_attributes = {}
        for attr in response['UserAttributes']:
            user_attributes[attr['Name']] = attr['Value']
        
        return jsonify({
            'username': current_user,
            'email': user_attributes.get('email'),
            'created_at': user_attributes.get('created_at')
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 토큰 검증 API
@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': '토큰이 없습니다'}), 400
        
        try:
            # Cognito JWT 토큰 검증
            public_keys = get_cognito_public_keys()
            if not public_keys:
                return jsonify({'error': '토큰 검증 실패'}), 401
            
            # 토큰 헤더에서 kid 추출
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            # 해당 kid의 공개키 찾기
            public_key = None
            for key in public_keys['keys']:
                if key['kid'] == kid:
                    public_key = key
                    break
            
            if not public_key:
                return jsonify({'error': '유효하지 않은 토큰입니다'}), 401
            
            # 토큰 검증
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=COGNITO_CONFIG['client_id'],
                issuer=f"https://cognito-idp.{COGNITO_CONFIG['region']}.amazonaws.com/{COGNITO_CONFIG['user_pool_id']}"
            )
            
            return jsonify({
                'valid': True,
                'user': {
                    'username': payload.get('cognito:username') or payload.get('username'),
                    'email': payload.get('email')
                }
            }), 200
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '토큰이 만료되었습니다'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '유효하지 않은 토큰입니다'}), 401
            
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

# 헬스체크 API
@app.route('/api/auth/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Sign up/in API is running'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
