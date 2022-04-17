import auth
import download

print('')
cookie = auth.detect_auth()
if not cookie:
  print('No login info, please scan the qrcode to download high quality videos.')
  acc = input('Send "n" to skip login. Or just press Enter to scan qrcode.')
  if acc != 'n':
    auth.get_qrcode()
    cookie = auth.get_login_cookie()
    if not cookie:
      print('Can\'t get cookie.')
      quit
user_input = input('Type BV or link here : ')
download.save_video(user_input, cookie=cookie)
print('')