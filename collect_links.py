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
#for South-Korea & for MAC(arm64)
#brew install --cask chromedriver

import time
import os
import sys
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotVisibleException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


class CollectLinks:
    def __init__(self, no_gui=False, proxy=None):
        # 디버깅 정보 출력
        print("=== 디버깅 정보 ===")
        print(f"Python 버전: {sys.version}")
        print(f"운영체제: {platform.system()} {platform.release()}")
        print(f"아키텍처: {platform.machine()}")
        print(f"현재 작업 디렉토리: {os.getcwd()}")

        # Chrome 브라우저 버전 확인 시도
        try:
            if platform.system() == 'Darwin':  # macOS
                chrome_version_cmd = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version']
                chrome_version = subprocess.check_output(chrome_version_cmd).decode('utf-8').strip()
                print(f"설치된 Chrome 버전: {chrome_version}")
        except Exception as e:
            print(f"Chrome 버전 확인 실패: {e}")
            chrome_version = "unknown"

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')

        # Mac ARM64에서는 추가 옵션 설정
        is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
        if is_mac_arm:
            print("Mac ARM64 아키텍처에 최적화된 설정 적용")
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--ignore-certificate-errors')

        if no_gui:
            chrome_options.add_argument('--headless=new')  # 새로운 헤드리스 모드 사용

        if proxy:
            chrome_options.add_argument("--proxy-server={}".format(proxy))

        try:
            # 수동으로 크롬드라이버 경로 찾기 시도
            chrome_driver_path = None

            # 가능한 경로들 리스트
            possible_paths = [
                '/opt/homebrew/bin/chromedriver',  # Homebrew 설치 경로
                './chromedriver',  # 현재 디렉토리
                '/usr/local/bin/chromedriver',  # 일반적인 설치 경로
                os.path.expanduser('~/.wdm/drivers/chromedriver/mac64/latest/chromedriver'),  # WebDriver Manager 최신 버전
            ]

            # Chrome 버전 기반으로 특정 WebDriver Manager 경로 추가
            if 'Chrome' in chrome_version:
                chrome_ver = chrome_version.split(' ')[-1].split('.')[0]  # 메이저 버전만 추출 (예: 135)
                wdm_path = os.path.expanduser(f'~/.wdm/drivers/chromedriver/mac64/{chrome_ver}')

                # 디렉토리가 존재하면 탐색
                if os.path.exists(wdm_path):
                    for root, dirs, files in os.walk(wdm_path):
                        for file in files:
                            if file == 'chromedriver':
                                possible_paths.append(os.path.join(root, file))

            # WebDriver Manager가 저장한 정확한 경로 추가
            wdm_exact_path = "/Users/junhoha/.wdm/drivers/chromedriver/mac64/135.0.7049.95/chromedriver-mac-arm64/chromedriver"
            possible_paths.append(wdm_exact_path)

            # 첫 번째 유효한 경로 사용
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"유효한 ChromeDriver 경로 발견: {path}")
                    chrome_driver_path = path

                    # 실행 권한 확인 및 설정
                    if not os.access(path, os.X_OK):
                        print(f"ChromeDriver에 실행 권한 부여: {path}")
                        os.chmod(path, 0o755)

                    # 검역 속성 제거 시도 (Mac용)
                    try:
                        print(f"검역 속성 제거 시도: {path}")
                        subprocess.run(['xattr', '-d', 'com.apple.quarantine', path],
                                       check=False, stderr=subprocess.PIPE)
                    except Exception as e:
                        print(f"검역 속성 제거 오류 (무시됨): {e}")

                    # 파일 상태 확인
                    file_info = subprocess.run(['file', path], capture_output=True, text=True)
                    print(f"ChromeDriver 파일 정보: {file_info.stdout.strip()}")

                    # 서명 확인 (Mac용)
                    if platform.system() == 'Darwin':
                        try:
                            codesign = subprocess.run(['codesign', '-v', path],
                                                      capture_output=True, text=True)
                            print(f"CodeSign 상태: {codesign.stderr if codesign.stderr else '정상'}")
                        except Exception as e:
                            print(f"CodeSign 확인 오류: {e}")

                    break

            if not chrome_driver_path:
                print("유효한 ChromeDriver를 찾을 수 없습니다.")
                print("직접 다운로드: https://chromedriver.chromium.org/downloads")
                self.browser = None
                return

            # 서비스 생성 및 브라우저 초기화
            service = Service(executable_path=chrome_driver_path)

            print("Chrome 브라우저 실행 시도...")
            self.browser = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome 브라우저 실행 성공!")

            # 브라우저 및 드라이버 버전 확인
            browser_version = 'Failed to detect version'
            chromedriver_version = 'Failed to detect version'
            major_version_different = False

            if 'browserVersion' in self.browser.capabilities:
                browser_version = str(self.browser.capabilities['browserVersion'])

            if 'chrome' in self.browser.capabilities:
                if 'chromedriverVersion' in self.browser.capabilities['chrome']:
                    chromedriver_version = str(self.browser.capabilities['chrome']['chromedriverVersion']).split(' ')[0]

            if browser_version.split('.')[0] != chromedriver_version.split('.')[0]:
                major_version_different = True

            print('_________________________________')
            print('Current web-browser version:\t{}'.format(browser_version))
            print('Current chrome-driver version:\t{}'.format(chromedriver_version))
            if major_version_different:
                print('warning: Version different')
                print(
                    'Download correct version at "http://chromedriver.chromium.org/downloads" and place in "./chromedriver"')
            print('_________________________________')

        except Exception as e:
            print(f"브라우저 초기화 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            # 예외가 발생해도 계속 진행할 수 있도록 None 설정
            self.browser = None

    # 나머지 메소드는 이전과 동일하게 유지...
    def get_scroll(self):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return 0
        pos = self.browser.execute_script("return window.pageYOffset;")
        return pos

    def wait_and_click(self, xpath):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return None
        #  Sometimes click fails unreasonably. So tries to click at all cost.
        try:
            w = WebDriverWait(self.browser, 15)
            elem = w.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            elem.click()
            self.highlight(elem)
        except Exception as e:
            print(f'Click time out - {xpath}. 오류: {e}')
            print('Refreshing browser...')
            self.browser.refresh()
            time.sleep(2)
            return self.wait_and_click(xpath)

        return elem

    def highlight(self, element):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return
        try:
            self.browser.execute_script("arguments[0].setAttribute('style', arguments[1]);", element,
                                        "background: yellow; border: 2px solid red;")
        except Exception as e:
            print(f"하이라이트 오류: {e}")

    @staticmethod
    def remove_duplicates(_list):
        return list(dict.fromkeys(_list))

    def google(self, keyword, add_url=""):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return []

        try:
            print(f"Google 검색 시작: {keyword}")
            self.browser.get("https://www.google.com/search?q={}&source=lnms&tbm=isch{}".format(keyword, add_url))
            time.sleep(1)
            print('Scrolling down')
            elem = self.browser.find_element(By.TAG_NAME, "body")
            last_scroll = 0
            scroll_patience = 0
            NUM_MAX_SCROLL_PATIENCE = 50

            while True:
                elem.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)
                scroll = self.get_scroll()
                if scroll == last_scroll:
                    scroll_patience += 1
                else:
                    scroll_patience = 0
                    last_scroll = scroll
                if scroll_patience >= NUM_MAX_SCROLL_PATIENCE:
                    break

            print('Scraping links')
            imgs = self.browser.find_elements(By.XPATH, '//div[@jsname="dTDiAc"]/div[@jsname="qQjpJ"]//img')
            print(f"이미지 요소 {len(imgs)}개 찾음")

            links = []
            for idx, img in enumerate(imgs):
                try:
                    src = img.get_attribute("src")
                    if src:
                        links.append(src)
                        if idx < 5:  # 처음 5개 링크만 로그 출력
                            print(f"이미지 링크 #{idx}: {src[:50]}...")
                except Exception as e:
                    print(f'[Exception occurred while collecting links from google] {e}')

            links = self.remove_duplicates(links)
            print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google', keyword, len(links)))
            try:
                self.browser.close()
            except Exception as e:
                print(f"브라우저 종료 중 오류: {e}")
            return links
        except Exception as e:
            print(f"Google 검색 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.browser:
                    self.browser.close()
            except:
                pass
            return []

    def naver(self, keyword, add_url=""):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return []

        try:
            print(f"Naver 검색 시작: {keyword}")
            self.browser.get(
                "https://search.naver.com/search.naver?where=image&sm=tab_jum&query={}{}".format(keyword, add_url))
            time.sleep(1)
            print('Scrolling down')
            elem = self.browser.find_element(By.TAG_NAME, "body")

            for i in range(60):
                elem.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)

            # XPath 패턴 디버깅
            print("XPath로 이미지 요소 찾는 중...")
            try:
                # 여러 XPath 패턴 시도
                xpath_patterns = [
                    '//div[@class="tile_item _fe_image_tab_content_tile"]//img[@class="_fe_image_tab_content_thumbnail_image"]',
                    '//div[contains(@class, "tile_item")]//img[contains(@class, "thumbnail_image")]',
                    '//img[contains(@class, "thumbnail_image")]'
                ]

                imgs = []
                for pattern in xpath_patterns:
                    print(f"XPath 패턴 시도: {pattern}")
                    imgs = self.browser.find_elements(By.XPATH, pattern)
                    if len(imgs) > 0:
                        print(f"패턴 {pattern}으로 {len(imgs)}개 요소 찾음")
                        break

                if len(imgs) == 0:
                    print("모든 XPath 패턴으로 요소를 찾지 못함. CSS 선택자 시도...")
                    imgs = self.browser.find_elements(By.CSS_SELECTOR,
                                                      'img.thumbnail_image, img._fe_image_tab_content_thumbnail_image')
                    print(f"CSS 선택자로 {len(imgs)}개 요소 찾음")
            except Exception as e:
                print(f"XPath/CSS 선택자 검색 중 오류: {e}")
                imgs = []

            print('Scraping links')
            links = []

            for idx, img in enumerate(imgs):
                try:
                    src = img.get_attribute("src")
                    if src and src[0] != 'd':  # data URL 제외
                        links.append(src)
                        if idx < 5:  # 처음 5개 링크만 로그 출력
                            print(f"이미지 링크 #{idx}: {src[:50]}...")
                except Exception as e:
                    print(f'[Exception occurred while collecting links from naver] {e}')

            links = self.remove_duplicates(links)
            print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('naver', keyword, len(links)))
            try:
                self.browser.close()
            except Exception as e:
                print(f"브라우저 종료 중 오류: {e}")
            return links
        except Exception as e:
            print(f"Naver 검색 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.browser:
                    self.browser.close()
            except:
                pass
            return []

    def google_full(self, keyword, add_url="", limit=100):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return []

        try:
            print('[Full Resolution Mode] Google')
            self.browser.get("https://www.google.com/search?q={}&tbm=isch{}".format(keyword, add_url))
            time.sleep(1)

            # 첫 번째 이미지 요소 찾기 시도
            print("첫 번째 이미지 클릭 시도...")
            try:
                # 여러 가능한 XPath 패턴 시도
                xpath_patterns = [
                    '//div[@jsname="dTDiAc"]',
                    '//div[contains(@jsname, "dTDiAc")]',
                    '//div[contains(@class, "isv-r")]//img'
                ]

                clicked = False
                for pattern in xpath_patterns:
                    print(f"XPath 패턴 시도: {pattern}")
                    try:
                        self.wait_and_click(pattern)
                        clicked = True
                        print(f"패턴 {pattern}으로 이미지 클릭 성공")
                        break
                    except Exception as e:
                        print(f"패턴 {pattern} 클릭 실패: {e}")

                if not clicked:
                    print("모든 XPath 패턴으로 이미지를 클릭하지 못함")
                    # 이미지가 없을 경우 빈 배열 반환
                    return []
            except Exception as e:
                print(f"이미지 클릭 중 오류: {e}")
                return []

            time.sleep(1)
            body = self.browser.find_element(By.TAG_NAME, "body")
            print('Scraping links')

            links = []
            limit = 10000 if limit == 0 else limit
            count = 1
            last_scroll = 0
            scroll_patience = 0
            NUM_MAX_SCROLL_PATIENCE = 100

            while len(links) < limit:
                try:
                    # XPath 패턴 여러 개 시도
                    xpath_patterns = [
                        '//div[@jsname="figiqf"]//img[not(contains(@src,"gstatic.com"))]',
                        '//div[contains(@jsname, "figiqf")]//img[not(contains(@src,"gstatic.com"))]',
                        '//div[contains(@class, "isv-r")]//img[not(contains(@src,"gstatic.com"))]'
                    ]

                    imgs = []
                    t1 = time.time()
                    xpath_used = ""

                    while True:
                        for pattern in xpath_patterns:
                            imgs = body.find_elements(By.XPATH, pattern)
                            if len(imgs) > 0:
                                xpath_used = pattern
                                break

                        t2 = time.time()
                        if len(imgs) > 0:
                            break
                        if t2 - t1 > 5:
                            print(f"5초 내에 이미지를 찾지 못함")
                            break
                        time.sleep(0.1)

                    if len(imgs) > 0:
                        print(f"패턴 {xpath_used}으로 이미지 찾음")
                        self.highlight(imgs[0])
                        src = imgs[0].get_attribute('src')

                        if src is not None and src not in links:
                            links.append(src)
                            print('%d: %s' % (count, src[:50] + '...'))
                            count += 1
                except KeyboardInterrupt:
                    print("키보드 인터럽트로 중단")
                    break
                except StaleElementReferenceException:
                    # 예상된 예외라 무시
                    pass
                except Exception as e:
                    print(f'[Exception occurred while collecting links from google_full] {e}')

                scroll = self.get_scroll()
                if scroll == last_scroll:
                    scroll_patience += 1
                else:
                    scroll_patience = 0
                    last_scroll = scroll

                if scroll_patience >= NUM_MAX_SCROLL_PATIENCE:
                    print(f"최대 스크롤 인내심({NUM_MAX_SCROLL_PATIENCE})에 도달하여 종료")
                    break

                body.send_keys(Keys.RIGHT)

            links = self.remove_duplicates(links)
            print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google_full', keyword, len(links)))
            try:
                self.browser.close()
            except Exception as e:
                print(f"브라우저 종료 중 오류: {e}")
            return links
        except Exception as e:
            print(f"Google Full 검색 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.browser:
                    self.browser.close()
            except:
                pass
            return []

    def naver_full(self, keyword, add_url=""):
        if self.browser is None:
            print("브라우저가 초기화되지 않았습니다.")
            return []

        try:
            print('[Full Resolution Mode] Naver')
            self.browser.get(
                "https://search.naver.com/search.naver?where=image&sm=tab_jum&query={}{}".format(keyword, add_url))
            time.sleep(1)

            elem = self.browser.find_element(By.TAG_NAME, "body")
            print('첫 번째 이미지 클릭 시도...')

            # 여러 XPath 패턴 시도
            xpath_patterns = [
                '//div[@class="tile_item _fe_image_tab_content_tile"]//img[@class="_fe_image_tab_content_thumbnail_image"]',
                '//div[contains(@class, "tile_item")]//img[contains(@class, "thumbnail_image")]',
                '//img[contains(@class, "thumbnail_image")]'
            ]

            clicked = False
            for pattern in xpath_patterns:
                print(f"XPath 패턴 시도: {pattern}")
                try:
                    self.wait_and_click(pattern)
                    clicked = True
                    print(f"패턴 {pattern}으로 이미지 클릭 성공")
                    break
                except Exception as e:
                    print(f"패턴 {pattern} 클릭 실패: {e}")

            if not clicked:
                print("모든 XPath 패턴으로 이미지를 클릭하지 못함")
                return []

            time.sleep(1)
            print('Scraping links')

            links = []
            count = 1
            last_scroll = 0
            scroll_patience = 0

            while True:
                try:
                    # 여러 XPath 패턴 시도
                    xpath_patterns = [
                        '//img[@class="_fe_image_viewer_image_fallback_target"]',
                        '//img[contains(@class, "_fe_image_viewer_image")]',
                        '//img[contains(@class, "image__image")]'
                    ]

                    imgs = []
                    for pattern in xpath_patterns:
                        imgs = self.browser.find_elements(By.XPATH, pattern)
                        if len(imgs) > 0:
                            print(f"패턴 {pattern}으로 {len(imgs)}개 이미지 찾음")
                            break

                    for img in imgs:
                        self.highlight(img)
                        src = img.get_attribute('src')

                        if src not in links and src is not None:
                            links.append(src)
                            print('%d: %s' % (count, src[:50] + '...'))
                            count += 1

                except StaleElementReferenceException:
                    # 예상된 예외라 무시
                    pass
                except Exception as e:
                    print(f'[Exception occurred while collecting links from naver_full] {e}')

                scroll = self.get_scroll()
                if scroll == last_scroll:
                    scroll_patience += 1
                else:
                    scroll_patience = 0
                    last_scroll = scroll

                if scroll_patience >= 100:
                    print("최대 스크롤 인내심(100)에 도달하여 종료")
                    break

                elem.send_keys(Keys.RIGHT)

            links = self.remove_duplicates(links)
            print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('naver_full', keyword, len(links)))
            try:
                self.browser.close()
            except Exception as e:
                print(f"브라우저 종료 중 오류: {e}")
            return links
        except Exception as e:
            print(f"Naver Full 검색 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.browser:
                    self.browser.close()
            except:
                pass
            return []


if __name__ == '__main__':
    try:
        print("테스트 실행 중...")
        # 추가 테스트: WebDriverManager 의존성 제거
        collect = CollectLinks(no_gui=False)  # GUI 모드로 디버깅
        if collect.browser:
            links = collect.google('test')  # 간단한 테스트 키워드
            print(f"총 {len(links)}개 링크 수집 완료")
            print(links[:5])  # 처음 5개 링크만 출력
        else:
            print("브라우저가 초기화되지 않았습니다. 아래 방법을 시도해보세요:")
            print("\n1. Chrome 브라우저와 ChromeDriver 버전이 일치하는지 확인하세요.")
            print("2. ChromeDriver를 직접 다운로드하여 프로젝트 폴더에 저장하세요:")
            print("   - 다운로드: https://chromedriver.chromium.org/downloads")
            print("3. 다운로드 후 실행 권한을 부여하세요:")
            print("   - chmod +x ./chromedriver")
            print("4. 검역 속성을 제거하세요:")
            print("   - xattr -d com.apple.quarantine ./chromedriver")
            print("\n또는 아래 명령으로 Homebrew를 통해 설치할 수 있습니다:")
            print("   brew install --cask chromedriver")
            print("   xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver")
    except Exception as e:
        print(f"전체 프로그램 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()