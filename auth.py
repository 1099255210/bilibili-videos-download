import time
import json
import requests
import qrcode
import re

url_qrcode_api = 'http://passport.bilibili.com/qrcode/getLoginUrl'
url_login_api = 'http://passport.bilibili.com/qrcode/getLoginInfo'

file_auth = 'auth.json'

pat_cookie = r'SESSDATA=.{34}'

payload_login = {
  'oauthKey': '',
}

def detect_auth():
  with open(file_auth, mode='r', encoding='utf-8') as fp:
    auth_json = json.load(fp)
  cookie = auth_json['Cookie']
  if cookie:
    return cookie
  return ''

def get_qrcode():
  r'''
  Create a login qrcode in terminal.
  '''

  res = requests.get(url_qrcode_api)
  res.raise_for_status()
  res_json = res.json()

  url = res_json['data']['url']
  key = res_json['data']['oauthKey']
  payload_login['oauthKey'] = key

  qr = qrcode.QRCode()
  qr.add_data(url)
  qr.print_ascii()


def get_login_cookie():
  r'''
  Request for login info.
  '''
  scanned = 0
  login_success = 0

  for i in range(180):
    res = requests.post(url=url_login_api, data=payload_login)
    res.raise_for_status()
    res_json = res.json()
    sta = bool(res_json['status'])
    if sta:
      url_login_info = res_json['data']['url']
      login_success = 1
      break
    dat = int(res_json['data'])
    if dat == -5 and not scanned:
      scanned = 1
      print('Scanned.')
    time.sleep(1)

  if not login_success:
    print('Time out.')
    return ''
  print('Login success!')
  cookie = re.search(pat_cookie, url_login_info).group(0)
  save_cookie(cookie=cookie)
  return cookie

def save_cookie(cookie=''):
  auth_json = {
    'Cookie': cookie
  }
  with open(file_auth, mode='w') as fp:
    json.dump(auth_json, fp)