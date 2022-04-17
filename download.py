from fileinput import filename
from tqdm import tqdm
import time
import re
import requests
import json

url_videoinfo_api = 'http://api.bilibili.com/x/web-interface/view'
url_download_api = 'https://api.bilibili.com/x/player/playurl'
url_referer = 'https://www.bilibili.com'
url_api = 'api.bilibili.com'

pat_BV = r'BV.{10}'
pat_page = r'p=\d+'

chunk_size = 1024

header_info = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
  'Cookie': '',
  'Host': url_api,
}

header_dl = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0',
  'Referer': url_referer,
}

def save_video(user_input='', cookie=''):
  r'''
  Find and execute video download by passing `bvid`
  '''

  bvid = get_BV(user_input)
  page = get_page(user_input)
  if not bvid:
    print('Not a valid input.')
    return -1

  video_info = get_video_info(bvid=bvid, page=page, cookie=cookie)

  if not video_info:
    print('Video info not found.')
    return -1
  
  video_title = video_info['title']
  video_quality = video_info['accept_description']
  video_qn = video_info['accept_quality']
  video_url = video_info['accept_url']
  video_size = video_info['accept_size']
  video_page_title = video_info['page_title']
  if page:
    video_page = 'p' + str(page)
  else:
    video_page = ''

  acc = input(
    f'Video title is : {video_title}-{video_page}-{video_page_title}'
    f'\nIs this the video you want to download? (send "n" to reject) '
  )
  if acc == 'n':
    print('Download canceled.')
    return -1

  print('The video quality list :')
  for i in range(len(video_quality)):
    if video_size[i] < 0:
      print('{}) {:<12} No Resource.'.format(i, video_quality[i]))
      continue
    print('{}) {:<12} {:.2f}MB'.format(i, video_quality[i], video_size[i]))

  user_choice = input('Choose the video quality : ')

  if not user_choice.isdigit():
    print('Invalid input.')
    return -1
  user_choice = int(user_choice)
  if user_choice < 0 or user_choice > len(video_quality):
    print('Invalid input.')
    return -1
  if video_size[user_choice] < 0:
    print('You need to login first.')
    return -1

  file_name = f'{video_title}-{video_page}-{video_page_title}'
  download_video(url=video_url[user_choice], qn=video_qn[user_choice], file=file_name)


def get_video_info(bvid='', page=0, cookie=''):
  r'''
  Get bilibili video's info by passing `bvid`.
  Return a dictionary if everything is OK, else return "".
  The info includes:
  `title`: video's title,
  `accept_description`: the description of the video quality,
  `accept_quality`: qn codes refering to the quality,
  `accpet_url`: download links refering to the quality,
  `accpet_size`: video file size refering to the quality.
  '''

  para = {}

  para['bvid'] = bvid
  header_info['Cookie'] = cookie

  video_info_res = requests.get(
    url = url_videoinfo_api,
    headers = header_info,
    params = para,
  )
  video_info_res.raise_for_status()
  video_info_json = video_info_res.json()

  # print(json.dumps(video_info_json))

  video_info = {}

  video_page = int(page)
  video_cid = video_info_json['data']['pages'][video_page]['cid']
  video_page_title = video_info_json['data']['pages'][video_page]['part']

  para = {
    'bvid': bvid,
    'cid': video_cid,
    'qn': '64',
  }
  for _ in range(10):
    video_res = requests.get(
      url = url_download_api,
      params = para,
      headers = header_info,
    )
    if video_res.status_code == 200:
      break
    time.sleep(0.1)
  video_json = video_res.json()

  # print(json.dumps(video_json))
  
  accept_description = video_json['data']['accept_description']
  accept_quality = video_json['data']['accept_quality']
  accept_url = []
  accept_size = []

  for quality in accept_quality:
    if quality > 64 and not cookie:
      accept_url.append('No url.')
      accept_size.append(-1)
      continue

    para['qn'] = quality
    for _ in range(10):
      video_res = requests.get(
        url = url_download_api,
        params = para,
        headers = header_info,
      )
      if video_res.status_code == 200:
        break
      time.sleep(0.1)

    if video_res.status_code != 200:
      accept_url.append('No url.')
      accept_size.append(-1)
      continue

    video_json = video_res.json()
    accept_url.append(video_json['data']['durl'][0]['url'])
    accept_size.append(int(video_json['data']['durl'][0]['size']) / 1_048_576)

  video_info['title'] = video_info_json['data']['title']
  video_info['page_title'] = video_page_title

  video_info['accept_description'] = accept_description
  video_info['accept_quality'] = accept_quality
  video_info['accept_url'] = accept_url
  video_info['accept_size'] = accept_size
  return video_info


def download_video(url='', qn='', file=''):
  r'''
  Download video by passing `url` and `file_name`.
  '''
  
  if qn == '16':
    file_name = file + '.mp4'
  else:
    file_name = file + '.flv'

  try:
    res_head = requests.head(url=url, headers=header_dl)
    res_size = res_head.headers.get('Content-Length')
    if not res_size:
      print('No response(file).')
      return -1
    res_size = int(res_size)

    res = requests.get(
      url = url,
      headers = header_dl,
      timeout = 30,
      stream = True,
    )
    res.raise_for_status()
    bar = tqdm(total=res_size, unit='B', unit_scale=True, unit_divisor=1024)
    with open(file_name, mode='wb') as fp:
      for chunk in res.iter_content(chunk_size=chunk_size):
        fp.write(chunk)
        bar.update(chunk_size)
    bar.close()
    return 0
  except:
    print('Stop downloading.')
    return -1


def get_BV(user_input=''):
  res = re.search(pattern=pat_BV, string=user_input)
  if res:
    return res.group(0)
  return ''

def get_page(user_input=''):
  res = re.search(pattern=pat_page, string=user_input)
  if res:
    return int(res.group(0).split('=')[-1])
  return 0