import google_auth_oauthlib.flow
import os

# 이 스크립트가 있는 폴더 경로
dir_path = os.path.dirname(os.path.realpath(__file__))
client_secrets_path = os.path.join(dir_path, 'client_secrets.json')
token_path = os.path.join(dir_path, 'token.json')

# client_secrets.json 파일을 사용하여 인증 흐름을 설정합니다.
# 이 방법은 로컬 서버를 자동으로 실행하여 리디렉션을 처리하므로 더 안정적입니다.
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    client_secrets_path,
    scopes=['https://www.googleapis.com/auth/youtube.upload'])

# run_local_server가 브라우저를 자동으로 열고, 인증 후 토큰을 받아옵니다.
# port=0 은 사용 가능한 포트를 자동으로 찾아서 사용하라는 의미입니다.
credentials = flow.run_local_server(port=0)

# 생성된 인증 정보(토큰)를 token.json 파일로 저장합니다.
with open(token_path, 'w') as f:
    f.write(credentials.to_json())

print(f"\n성공! '{token_path}' 파일이 생성되었습니다.")
print("이제 이 터미널 창은 닫으셔도 됩니다.") 