"""
Copyright 2018 YoongiKim

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import requests
import shutil
from multiprocessing import Pool
import signal
import argparse
from collect_links import CollectLinks
import imghdr
import base64
from pathlib import Path
import random
import traceback
import platform
import sys
from urllib3.exceptions import ReadTimeoutError, ConnectTimeoutError


class Sites:
    GOOGLE = 1
    NAVER = 2
    GOOGLE_FULL = 3
    NAVER_FULL = 4

    @staticmethod
    def get_text(code):
        if code == Sites.GOOGLE:
            return 'google'
        elif code == Sites.NAVER:
            return 'naver'
        elif code == Sites.GOOGLE_FULL:
            return 'google'
        elif code == Sites.NAVER_FULL:
            return 'naver'

    @staticmethod
    def get_face_url(code):
        if code == Sites.GOOGLE or code == Sites.GOOGLE_FULL:
            return "&tbs=itp:face"
        if code == Sites.NAVER or code == Sites.NAVER_FULL:
            return "&face=1"


class AutoCrawler:
    def __init__(self, skip_already_exist=True, n_threads=4, do_google=True, do_naver=True, download_path='download',
                 full_resolution=False, face=False, no_gui=False, limit=0, proxy_list=None):
        """
        :param skip_already_exist: Skips keyword already downloaded before. This is needed when re-downloading.
        :param n_threads: Number of threads to download.
        :param do_google: Download from google.com (boolean)
        :param do_naver: Download from naver.com (boolean)
        :param download_path: Download folder path
        :param full_resolution: Download full resolution image instead of thumbnails (slow)
        :param face: Face search mode
        :param no_gui: No GUI mode. Acceleration for full_resolution mode.
        :param limit: Maximum count of images to download. (0: infinite)
        :param proxy_list: The proxy list. Every thread will randomly choose one from the list.
        """

        self.skip = skip_already_exist
        self.n_threads = n_threads
        self.do_google = do_google
        self.do_naver = do_naver
        self.download_path = download_path
        self.full_resolution = full_resolution
        self.face = face
        self.no_gui = no_gui
        self.limit = limit
        self.proxy_list = proxy_list if proxy_list and len(proxy_list) > 0 and proxy_list[0] else None

        # 시스템 정보 출력
        self.print_system_info()

        # 다운로드 디렉토리 생성
        os.makedirs('./{}'.format(self.download_path), exist_ok=True)

    def print_system_info(self):
        """시스템 정보를 출력합니다."""
        print("=== 시스템 정보 ===")
        print(f"Python 버전: {sys.version}")
        print(f"운영체제: {platform.system()} {platform.release()}")
        print(f"아키텍처: {platform.machine()}")
        print(f"현재 작업 디렉토리: {os.getcwd()}")
        print("=== 프로그램 설정 ===")
        print(f"건너뛰기: {self.skip}")
        print(f"스레드 수: {self.n_threads}")
        print(f"Google 사용: {self.do_google}")
        print(f"Naver 사용: {self.do_naver}")
        print(f"전체 해상도: {self.full_resolution}")
        print(f"얼굴 검색: {self.face}")
        print(f"GUI 없음: {self.no_gui}")
        print(f"이미지 제한: {self.limit if self.limit > 0 else '무제한'}")
        print(f"프록시 목록: {self.proxy_list}")
        print("===================")

    @staticmethod
    def all_dirs(path):
        """지정된 경로의 모든 디렉토리 목록을 반환합니다."""
        paths = []
        try:
            for dir in os.listdir(path):
                dir_path = os.path.join(path, dir)
                if os.path.isdir(dir_path):
                    paths.append(dir_path)
        except Exception as e:
            print(f"디렉토리 목록 가져오기 오류: {e}")
        return paths

    @staticmethod
    def all_files(path):
        """지정된 경로의 모든 파일 목록을 반환합니다."""
        paths = []
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(path, file)
                    if os.path.isfile(file_path):
                        paths.append(file_path)
        except Exception as e:
            print(f"파일 목록 가져오기 오류: {e}")
        return paths

    @staticmethod
    def get_extension_from_link(link, default='jpg'):
        """URL에서 파일 확장자를 추출합니다."""
        try:
            splits = str(link).split('.')
            if len(splits) == 0:
                return default
            ext = splits[-1].lower()
            # 확장자에 추가 파라미터가 있는 경우 제거 (예: .jpg?param=value)
            if '?' in ext:
                ext = ext.split('?')[0]
            if ext == 'jpg' or ext == 'jpeg':
                return 'jpg'
            elif ext == 'gif':
                return 'gif'
            elif ext == 'png':
                return 'png'
            else:
                return default
        except Exception:
            return default

    @staticmethod
    def validate_image(path):
        """이미지 파일의 유효성을 검사합니다."""
        try:
            ext = imghdr.what(path)
            if ext == 'jpeg':
                ext = 'jpg'
            return ext  # 유효하지 않은 경우 None 반환
        except Exception as e:
            print(f"이미지 유효성 검사 오류: {e}")
            return None

    @staticmethod
    def make_dir(dirname):
        """디렉토리를 생성합니다."""
        try:
            current_path = os.getcwd()
            path = os.path.join(current_path, dirname)
            if not os.path.exists(path):
                os.makedirs(path)
                print(f"디렉토리 생성: {path}")
            return path
        except Exception as e:
            print(f"디렉토리 생성 오류: {e}")
            return None

    @staticmethod
    def get_keywords(keywords_file='keywords.txt'):
        """키워드 파일에서 검색 키워드를 읽어옵니다."""
        keywords = []
        try:
            # 키워드 파일이 존재하는지 확인
            if not os.path.exists(keywords_file):
                print(f"경고: {keywords_file} 파일이 존재하지 않습니다.")
                return keywords

            # 파일에서 키워드 읽기
            with open(keywords_file, 'r', encoding='utf-8-sig') as f:
                text = f.read()
                lines = text.split('\n')
                lines = filter(lambda x: x != '' and x is not None, lines)
                keywords = sorted(set(lines))

            print('{} 키워드 발견: {}'.format(len(keywords), keywords))

            # 정렬된 키워드 다시 저장
            with open(keywords_file, 'w+', encoding='utf-8') as f:
                for keyword in keywords:
                    f.write('{}\n'.format(keyword))

        except Exception as e:
            print(f"키워드 파일 읽기 오류: {e}")
            traceback.print_exc()

        return keywords

    @staticmethod
    def save_object_to_file(object, file_path, is_base64=False):
        """객체를 파일로 저장합니다."""
        try:
            # 디렉토리 경로 확인 및 생성
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with open('{}'.format(file_path), 'wb') as file:
                if is_base64:
                    file.write(object)
                else:
                    shutil.copyfileobj(object.raw, file)
            return True
        except Exception as e:
            print(f'파일 저장 실패 - {e}')
            return False

    @staticmethod
    def base64_to_object(src):
        """Base64 인코딩된 이미지를 디코딩합니다."""
        try:
            header, encoded = str(src).split(',', 1)
            data = base64.decodebytes(bytes(encoded, encoding='utf-8'))
            return data
        except Exception as e:
            print(f"Base64 디코딩 오류: {e}")
            return None

    def download_images(self, keyword, links, site_name, max_count=0):
        """이미지 URL 목록에서 이미지를 다운로드합니다."""
        keyword_dir = self.make_dir('{}/{}'.format(self.download_path, keyword.replace('"', '')))
        total = len(links)
        success_count = 0
        fail_count = 0

        if max_count == 0:
            max_count = total

        for index, link in enumerate(links):
            if success_count >= max_count:
                break

            try:
                print('다운로드 중 {} from {}: {} / {}'.format(keyword, site_name, success_count + 1, max_count))

                if str(link).startswith('data:image/jpeg;base64'):
                    response = self.base64_to_object(link)
                    ext = 'jpg'
                    is_base64 = True
                elif str(link).startswith('data:image/png;base64'):
                    response = self.base64_to_object(link)
                    ext = 'png'
                    is_base64 = True
                else:
                    response = requests.get(link, stream=True, timeout=10)
                    ext = self.get_extension_from_link(link)
                    is_base64 = False

                # 응답 코드 확인 (Base64가 아닌 경우)
                if not is_base64 and response.status_code != 200:
                    print(f'다운로드 실패: HTTP {response.status_code} - {link}')
                    fail_count += 1
                    continue

                no_ext_path = '{}/{}/{}_{}'.format(self.download_path.replace('"', ''), keyword, site_name,
                                                   str(index).zfill(4))
                path = no_ext_path + '.' + ext

                if self.save_object_to_file(response, path, is_base64=is_base64):
                    success_count += 1
                    del response

                    # 이미지 유효성 검사
                    ext2 = self.validate_image(path)
                    if ext2 is None:
                        print('읽을 수 없는 파일 - {}'.format(link))
                        os.remove(path)
                        success_count -= 1
                        fail_count += 1
                    else:
                        if ext != ext2:
                            path2 = no_ext_path + '.' + ext2
                            os.rename(path, path2)
                            print('확장자 변경 {} -> {}'.format(ext, ext2))
                else:
                    fail_count += 1

            except KeyboardInterrupt:
                print("사용자에 의한 중단")
                break

            except (ReadTimeoutError, ConnectTimeoutError, requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectTimeout) as e:
                print(f'다운로드 타임아웃 - {e}')
                fail_count += 1
                continue

            except Exception as e:
                print(f'다운로드 실패 - {e}')
                fail_count += 1
                continue

        print(f'{site_name}에서 {keyword} 다운로드 완료: 성공 {success_count}, 실패 {fail_count}')
        return success_count

    def download_from_site(self, keyword, site_code):
        """특정 사이트에서 키워드에 대한 이미지를 다운로드합니다."""
        site_name = Sites.get_text(site_code)
        add_url = Sites.get_face_url(site_code) if self.face else ""

        try:
            proxy = None
            if self.proxy_list:
                proxy = random.choice(self.proxy_list)
                print(f"선택된 프록시: {proxy}")

            collect = CollectLinks(no_gui=self.no_gui, proxy=proxy)  # 크롬 드라이버 초기화

            # 브라우저 초기화 실패 시 종료
            if collect.browser is None:
                print(f'ChromeDriver 초기화 실패 - {site_name}:{keyword}')
                return

        except Exception as e:
            print(f'ChromeDriver 초기화 중 오류 발생 - {e}')
            traceback.print_exc()
            return

        try:
            print(f'링크 수집 중... {keyword} from {site_name}')

            if site_code == Sites.GOOGLE:
                links = collect.google(keyword, add_url)

            elif site_code == Sites.NAVER:
                links = collect.naver(keyword, add_url)

            elif site_code == Sites.GOOGLE_FULL:
                links = collect.google_full(keyword, add_url, self.limit)

            elif site_code == Sites.NAVER_FULL:
                links = collect.naver_full(keyword, add_url)

            else:
                print('유효하지 않은 사이트 코드')
                links = []

            print(f'수집된 링크에서 이미지 다운로드 중... {keyword} from {site_name}')
            success_count = self.download_images(keyword, links, site_name, max_count=self.limit)

            # 다운로드 성공 시 완료 표시 파일 생성
            if success_count > 0:
                keyword_dir = os.path.join(self.download_path, keyword.replace('"', ''))
                Path(f'{keyword_dir}/{site_name}_done').touch()
                print(f'완료 {site_name} : {keyword}')
            else:
                print(f'다운로드 실패 {site_name} : {keyword} - 이미지 없음')

        except KeyboardInterrupt:
            print("사용자에 의한 중단")
            return

        except Exception as e:
            print(f'예외 발생 {site_name}:{keyword} - {e}')
            traceback.print_exc()
            return

    def download(self, args):
        """멀티프로세싱을 위한 다운로드 래퍼 함수"""
        self.download_from_site(keyword=args[0], site_code=args[1])

    def init_worker(self):
        """워커 초기화 함수 - Ctrl+C 처리"""
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def do_crawling(self):
        """크롤링을 실행합니다."""
        keywords = self.get_keywords()

        if not keywords:
            print("키워드가 없습니다. keywords.txt 파일을 확인하세요.")
            return

        tasks = []

        for keyword in keywords:
            # 경로에 공백이나 특수문자가 있으면 따옴표로 처리
            sanitized_keyword = keyword.replace('"', '')
            dir_name = '{}/{}'.format(self.download_path, sanitized_keyword)

            # 완료 파일 확인
            google_done_path = os.path.join(os.getcwd(), dir_name, 'google_done')
            naver_done_path = os.path.join(os.getcwd(), dir_name, 'naver_done')

            google_done = os.path.exists(google_done_path)
            naver_done = os.path.exists(naver_done_path)

            if google_done and naver_done and self.skip:
                print(f'이미 완료된 작업 건너뛰기: {dir_name}')
                continue

            if self.do_google and not google_done:
                if self.full_resolution:
                    tasks.append([keyword, Sites.GOOGLE_FULL])
                else:
                    tasks.append([keyword, Sites.GOOGLE])

            if self.do_naver and not naver_done:
                if self.full_resolution:
                    tasks.append([keyword, Sites.NAVER_FULL])
                else:
                    tasks.append([keyword, Sites.NAVER])

        if not tasks:
            print("모든 키워드가 이미 처리되었습니다.")
            return

        print(f"총 {len(tasks)}개 작업 대기 중")

        try:
            pool = Pool(self.n_threads, initializer=self.init_worker)
            pool.map(self.download, tasks)
        except KeyboardInterrupt:
            print("\n키보드 인터럽트 감지됨. 작업 중단...")
            pool.terminate()
            pool.join()
        else:
            pool.terminate()
            pool.join()
        print('작업 종료. 풀 종료.')

        self.imbalance_check()

        print('프로그램 종료')

    def imbalance_check(self):
        """데이터 불균형 여부를 확인합니다."""
        print('데이터 불균형 확인 중...')

        dict_num_files = {}

        for dir in self.all_dirs(self.download_path):
            n_files = len(self.all_files(dir))
            dict_num_files[dir] = n_files

        if not dict_num_files:
            print("다운로드된 디렉토리가 없습니다.")
            return

        avg = 0
        for dir, n_files in dict_num_files.items():
            avg += n_files / len(dict_num_files)
            print(f'디렉토리: {dir}, 파일 수: {n_files}')

        dict_too_small = {}

        for dir, n_files in dict_num_files.items():
            if n_files < avg * 0.5:
                dict_too_small[dir] = n_files

        if len(dict_too_small) >= 1:
            print('데이터 불균형이 감지되었습니다.')
            print('아래 키워드는 평균 파일 수의 50% 미만입니다.')
            print('이 디렉토리를 삭제하고 해당 키워드를 다시 다운로드하는 것이 좋습니다.')
            print('_________________________________')
            print('파일 수가 너무 적은 디렉토리:')
            for dir, n_files in dict_too_small.items():
                print(f'디렉토리: {dir}, 파일 수: {n_files}')

            print("위 디렉토리를 삭제하시겠습니까? (y/n)")
            answer = input()

            if answer.lower() == 'y':
                # 파일 수가 적은 디렉토리 삭제
                print("파일 수가 적은 디렉토리를 삭제합니다...")
                for dir, n_files in dict_too_small.items():
                    try:
                        shutil.rmtree(dir)
                        print(f'삭제됨: {dir}')
                    except Exception as e:
                        print(f"디렉토리 삭제 중 오류 발생: {e}")

                print('이제 이 프로그램을 다시 실행하여 삭제된 파일을 다시 다운로드하세요. (skip_already_exist=True 옵션 사용)')
        else:
            print('데이터 불균형이 감지되지 않았습니다.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip', type=str, default='true',
                        help='이미 다운로드된 키워드를 건너뜁니다. 재다운로드 시 필요합니다.')
    parser.add_argument('--threads', type=int, default=4, help='다운로드할 스레드 수.')
    parser.add_argument('--google', type=str, default='true', help='Google.com에서 다운로드 (boolean)')
    parser.add_argument('--naver', type=str, default='true', help='Naver.com에서 다운로드 (boolean)')
    parser.add_argument('--full', type=str, default='false',
                        help='썸네일 대신 전체 해상도 이미지 다운로드 (느림)')
    parser.add_argument('--face', type=str, default='false', help='얼굴 검색 모드')
    parser.add_argument('--no_gui', type=str, default='auto',
                        help='GUI 없는 모드. 전체 해상도 모드에서 가속화됩니다. '
                             '그러나 썸네일 모드에서는 불안정합니다. '
                             '기본값: "auto" - full=false이면 false, full=true이면 true')
    parser.add_argument('--limit', type=int, default=0,
                        help='사이트당 다운로드할 이미지의 최대 수.')
    parser.add_argument('--proxy-list', type=str, default='',
                        help='쉼표로 구분된 프록시 목록: "socks://127.0.0.1:1080,http://127.0.0.1:1081". '
                             '각 스레드는 목록에서 하나를 무작위로 선택합니다.')
    args = parser.parse_args()

    _skip = False if str(args.skip).lower() == 'false' else True
    _threads = args.threads
    _google = False if str(args.google).lower() == 'false' else True
    _naver = False if str(args.naver).lower() == 'false' else True
    _full = False if str(args.full).lower() == 'false' else True
    _face = False if str(args.face).lower() == 'false' else True
    _limit = int(args.limit)
    _proxy_list = args.proxy_list.split(',')

    no_gui_input = str(args.no_gui).lower()
    if no_gui_input == 'auto':
        _no_gui = _full
    elif no_gui_input == 'true':
        _no_gui = True
    else:
        _no_gui = False

    print(
        'Options - skip:{}, threads:{}, google:{}, naver:{}, full_resolution:{}, face:{}, no_gui:{}, limit:{}, proxy_list:{}'
        .format(_skip, _threads, _google, _naver, _full, _face, _no_gui, _limit, _proxy_list))

    crawler = AutoCrawler(skip_already_exist=_skip, n_threads=_threads,
                          do_google=_google, do_naver=_naver, full_resolution=_full,
                          face=_face, no_gui=_no_gui, limit=_limit, proxy_list=_proxy_list)
    crawler.do_crawling()