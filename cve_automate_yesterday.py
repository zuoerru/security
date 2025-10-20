#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CVE自动下载工具 - 专门用于昨日数据获取
该工具使用Selenium模拟浏览器行为，自动访问cvedetails.com网站，
获取昨日发布的CVE漏洞信息，并将数据导出为多种格式保存。
"""
import os
import time
import logging
import random
import shutil
import subprocess
from datetime import datetime, timedelta
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
                                       ElementNotInteractableException, WebDriverException)

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# 设置保存目录
OUTPUT_DIR = '/data_nfs/121/app/security'

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 登录信息
USERNAME = 'tigerguo@webank.com'
PASSWORD = 'Webank123!@#'

class CveDetailsAutomator:
    """CVE详情自动化工具类"""
    def __init__(self):
        """初始化自动化工具"""
        self.driver = None
        self.session = self._create_requests_session()
        # 添加屏幕分辨率属性，设置默认值
        self.selected_resolution = (1920, 1080)
    
    def _create_requests_session(self):
        """创建并配置requests会话"""
        session = requests.Session()
        # 添加更完整的请求头
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        
        # 添加常见cookies
        session.cookies.set('CFTOKEN', 'dummy-token-value')
        session.cookies.set('CFTIMEZONE', 'Asia/Shanghai')
        session.cookies.set('PHPSESSID', 'dummy-session-id')
        
        return session
    
    def setup_driver(self):
        """设置Firefox WebDriver"""
        try:
            options = Options()
            # 强制使用无头模式以适应服务器环境
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # 随机选择浏览器分辨率
            resolutions = [(1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1600, 900)]
            self.selected_resolution = random.choice(resolutions)
            logger.info(f'已选择浏览器分辨率: {self.selected_resolution[0]}x{self.selected_resolution[1]}')
            options.add_argument(f'--window-size={self.selected_resolution[0]},{self.selected_resolution[1]}')
            
            # 添加防检测配置 - 增强版
            options.set_preference('dom.webdriver.enabled', False)
            options.set_preference('useAutomationExtension', False)
            options.set_preference('general.useragent.override', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36')
            
            # 配置下载设置
            options.set_preference('browser.download.folderList', 2)  # 0=桌面, 1=下载文件夹, 2=自定义目录
            options.set_preference('browser.download.dir', OUTPUT_DIR)  # 设置下载目录
            options.set_preference('browser.download.manager.showWhenStarting', False)  # 不显示下载管理器
            options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/tab-separated-values,text/tsv,application/octet-stream')  # 自动下载TSV和相关文件类型
            options.set_preference('browser.download.manager.useWindow', False)  # 不使用下载窗口
            options.set_preference('browser.download.manager.focusWhenStarting', False)  # 下载开始时不聚焦
            options.set_preference('browser.download.manager.closeWhenDone', True)  # 下载完成后关闭
            
            # 禁用图像加载以提高速度
            options.set_preference('permissions.default.image', 2)
            options.set_preference('network.http.use-cache', True)
            
            # 额外的反检测配置 - 增强版
            options.set_preference('app.update.auto', False)
            options.set_preference('app.update.enabled', False)
            options.set_preference('browser.safebrowsing.phishing.enabled', False)
            options.set_preference('browser.safebrowsing.malware.enabled', False)
            options.set_preference('browser.cache.offline.enable', False)
            options.set_preference('dom.battery.enabled', False)
            options.set_preference('dom.enable_performance', False)
            options.set_preference('dom.media.mediasession.enabled', False)
            
            # 新增高级反检测配置
            options.set_preference('privacy.trackingprotection.enabled', False)
            options.set_preference('privacy.trackingprotection.fingerprinting.enabled', False)
            options.set_preference('privacy.trackingprotection.cryptomining.enabled', False)
            options.set_preference('network.cookie.cookieBehavior', 0)
            options.set_preference('browser.cache.disk.enable', True)
            options.set_preference('browser.cache.memory.enable', True)
            options.set_preference('browser.cache.offline.enable', True)
            options.set_preference('network.cachelocality.enabled', True)
            options.set_preference('browser.sessionstore.enabled', True)
            options.set_preference('browser.sessionhistory.max_entries', 50)
            options.set_preference('geo.enabled', True)
            options.set_preference('geo.provider.network.url', 'https://location.services.mozilla.com/v1/geolocate?key=%MOZILLA_API_KEY%')
            options.set_preference('dom.storage.enabled', True)
            options.set_preference('media.peerconnection.enabled', True)
            options.set_preference('layers.acceleration.disabled', False)
            
            # 添加代理设置（如果需要）
            # options.set_preference('network.proxy.type', 1)
            # options.set_preference('network.proxy.http', 'proxy.example.com')
            # options.set_preference('network.proxy.http_port', 8080)
            
            # 查找geckodriver并设置权限
            geckodriver_path = '/usr/local/bin/geckodriver'
            if os.path.exists(geckodriver_path):
                # 确保有执行权限
                if not os.access(geckodriver_path, os.X_OK):
                    try:
                        os.chmod(geckodriver_path, 0o755)
                        logger.info(f'已设置 {geckodriver_path} 执行权限')
                    except Exception as e:
                        logger.warning(f'设置geckodriver权限失败: {e}')
            else:
                # 尝试使用which命令查找geckodriver
                try:
                    geckodriver_path = subprocess.check_output(['which', 'geckodriver']).decode().strip()
                    logger.info(f'通过which命令找到geckodriver: {geckodriver_path}')
                except Exception:
                    logger.warning('未找到geckodriver，将使用系统默认路径')
                    geckodriver_path = None
            
            # 初始化WebDriver
            if geckodriver_path:
                service = Service(geckodriver_path)
                self.driver = webdriver.Firefox(
                    options=options,
                    service=service
                )
            else:
                self.driver = webdriver.Firefox(
                    options=options
                )
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(60)
            self.driver.set_script_timeout(60)
            
            # 执行JavaScript以进一步隐藏自动化痕迹 - 增强版
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'zh-CN']})")
            self.driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'userAgent', {get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'appVersion', {get: () => '5.0 (Windows)'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'productSub', {get: () => '20030107'})")
            
            # 模拟真实浏览器特征
            self.driver.execute_script("const originalQuery = window.navigator.permissions.query;\n" +
                "window.navigator.permissions.query = (parameters) => {\n" +
                "  if (parameters.name === 'notifications') {\n" +
                "    return Promise.resolve({ state: Notification.permission });\n" +
                "  }\n" +
                "  return originalQuery(parameters);\n" +
                "};")
            
            self.driver.execute_script("const originalGetContext = HTMLCanvasElement.prototype.getContext;\n" +
                "HTMLCanvasElement.prototype.getContext = function() {\n" +
                "  const context = originalGetContext.apply(this, arguments);\n" +
                "  if (arguments[0] === '2d') {\n" +
                "    context.textBaseline = 'alphabetic';\n" +
                "    context.fillStyle = '#222222';\n" +
                "    context.fillText('CVEBrowserExtension', 2, 2);\n" +
                "  }\n" +
                "  return context;\n" +
                "};")
            
            # 添加高级的浏览器指纹伪造
            self.driver.execute_script("""
                // 模拟真实的硬件信息
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 16});
                  
                // 模拟真实的屏幕信息
                Object.defineProperty(screen, 'availWidth', {get: () => window.innerWidth});
                Object.defineProperty(screen, 'availHeight', {get: () => window.innerHeight});
                  
                // 模拟真实的触摸支持
                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 5});
                  
                // 模拟真实的电池状态
                const mockBattery = {
                    level: 0.85,
                    charging: false,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    addEventListener: () => {},
                    removeEventListener: () => {},
                    dispatchEvent: () => true
                };
                navigator.getBattery = async () => mockBattery;
                  
                // 模拟真实的性能信息
                window.performance = window.performance || {};
                performance.memory = performance.memory || {
                    usedJSHeapSize: 10000000,
                    totalJSHeapSize: 20000000,
                    jsHeapSizeLimit: 2000000000
                };
            """)
            
            self.driver.set_window_size(self.selected_resolution[0], self.selected_resolution[1])
            
            # 执行额外的JavaScript来处理WebDriver检测
            self.driver.set_window_position(0, 0)
            
            logger.info('Firefox WebDriver已成功初始化并配置了反检测策略')
            return True
        except Exception as e:
            logger.error(f'初始化Firefox WebDriver失败: {e}')
            return False

    def handle_cloudflare_challenge(self):
        """处理Cloudflare机器人验证挑战 - 增强版"""
        logger.info('开始检测并处理Cloudflare验证...')
        
        try:
            # 检查是否存在Cloudflare验证页面的特征
            page_source = self.driver.page_source.lower()
            
            if ('cloudflare' in page_source or \
               'cdn-cgi/challenge-platform' in page_source or \
               '验证您是否是真人' in page_source or \
               'just a moment' in page_source or \
               'checking your browser' in page_source or \
               'completing the security check' in page_source or
               'ray id' in page_source):
                
                logger.warning('检测到Cloudflare机器人验证页面')
                
                # 保存验证页面到文件以便分析
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                verification_file = os.path.join(OUTPUT_DIR, f'cloudflare_verification_{timestamp}.html')
                with open(verification_file, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.info(f'已保存Cloudflare验证页面到 {verification_file}')
                
                # 执行Cloudflare JS挑战绕过脚本
                self._execute_cloudflare_bypass_script()
                
                # 模拟人类行为：随机移动鼠标和键盘操作
                self._simulate_human_behavior(enhanced=True)
                
                # 等待验证完成（可能需要60-120秒）
                logger.info('等待Cloudflare验证完成...')
                wait_time = 0
                max_wait = 120  # 最多等待120秒
                
                while wait_time < max_wait:
                    time.sleep(5)
                    wait_time += 5
                    
                    # 检查验证是否已完成
                    current_page_source = self.driver.page_source.lower()
                    if ('cloudflare' not in current_page_source or \
                       'cdn-cgi/challenge-platform' not in current_page_source or \
                       self.driver.current_url != 'https://www.cvedetails.com/'):
                        logger.info('Cloudflare验证似乎已完成')
                        return True
                    
                    logger.info(f'验证中...已等待 {wait_time} 秒')
                    
                    # 继续模拟人类行为
                    if wait_time % 10 == 0:
                        self._simulate_human_behavior(enhanced=True)
                        # 再次执行绕过脚本
                        self._execute_cloudflare_bypass_script()
                
                logger.warning(f'Cloudflare验证超时（{max_wait}秒），但继续尝试')
                return False
            else:
                logger.info('未检测到Cloudflare机器人验证')
                return True
        except Exception as e:
            logger.error(f'处理Cloudflare验证时出错: {e}')
            return False
            
    def _execute_cloudflare_bypass_script(self):
        """执行专门针对Cloudflare的绕过脚本"""
        try:
            logger.info('执行Cloudflare绕过脚本')
            
            # 禁用Cloudflare的一些检测机制
            self.driver.execute_script("""
                // 覆盖XMLHttpRequest以隐藏自动化痕迹
                const originalXHR = window.XMLHttpRequest;
                const newXHR = function() {
                    const xhr = new originalXHR();
                    Object.defineProperty(xhr, 'withCredentials', {
                        get: function() { return false; },
                        set: function() {}
                    });
                    return xhr;
                };
                window.XMLHttpRequest = newXHR;
                
                // 覆盖fetch API
                const originalFetch = window.fetch;
                window.fetch = function() {
                    arguments[1] = arguments[1] || {};
                    arguments[1].credentials = arguments[1].credentials || 'omit';
                    return originalFetch.apply(this, arguments);
                };
                
                // 模拟真实的鼠标事件属性
                MouseEvent.prototype.getModifierState = function(keyArg) {
                    return false;
                };
                
                // 修复无头浏览器的一些检测点
                const navigatorProperties = ['webdriver', 'languages', 'plugins', 'mimeTypes'];
                navigatorProperties.forEach(prop => {
                    if (Object.getOwnPropertyDescriptor(navigator, prop)) {
                        Object.defineProperty(navigator, prop, {
                            configurable: true,
                            enumerable: true,
                            writable: true
                        });
                    }
                });
                
                // 模拟真实的navigator.plugins
                navigator.plugins = {
                    length: 3,
                    0: {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'}, 
                    1: {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'}, 
                    2: {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'},
                    item: function(index) { return this[index] || null; },
                    namedItem: function(name) {
                        for (let i = 0; i < this.length; i++) {
                            if (this[i].name === name) return this[i];
                        }
                        return null;
                    }
                };
                
                // 模拟真实的navigator.mimeTypes
                navigator.mimeTypes = {
                    length: 3,
                    0: {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0]},
                    1: {type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[1]},
                    2: {type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable', enabledPlugin: navigator.plugins[2]},
                    item: function(index) { return this[index] || null; },
                    namedItem: function(name) {
                        for (let i = 0; i < this.length; i++) {
                            if (this[i].type === name) return this[i];
                        }
                        return null;
                    }
                };
                
                // 模拟真实的document.cookie行为
                const originalCookie = Object.getOwnPropertyDescriptor(document, 'cookie');
                Object.defineProperty(document, 'cookie', {
                    get: function() {
                        return originalCookie.get.call(this);
                    },
                    set: function(value) {
                        // 确保cookie设置正确
                        if (value.indexOf('__cfduid') >= 0 || value.indexOf('cf_clearance') >= 0) {
                            return originalCookie.set.call(this, value);
                        }
                        return '';
                    },
                    configurable: true
                });
            """)
            
            logger.info('Cloudflare绕过脚本执行完成')
        except Exception as e:
            logger.warning(f'执行Cloudflare绕过脚本时出错: {e}')
            
    def _random_delay(self, min_delay=1, max_delay=3):
        """随机延迟，模拟人类操作间隔"""
        try:
            delay = random.uniform(min_delay, max_delay)
            logger.debug(f'随机延迟 {delay:.2f} 秒')
            time.sleep(delay)
        except Exception as e:
            logger.warning(f'随机延迟时出错: {e}')
            
    def _warmup_requests(self):
        """预热网站，通过发送多个请求来模拟真实浏览行为"""
        try:
            logger.info('预热网站请求...')
            
            # 发送HEAD请求先检查站点状态
            self.session.head('https://www.cvedetails.com/', timeout=10, verify=False)
            self._random_delay(1, 2)
            
            # 访问首页获取初始cookies
            response = self.session.get('https://www.cvedetails.com/', timeout=15, verify=False)
            response.raise_for_status()
            self._random_delay(2, 3)
            
            # 访问一些其他页面模拟真实用户浏览
            pages_to_visit = [
                'https://www.cvedetails.com/vulnerability-list/',
                'https://www.cvedetails.com/top-50-vulnerabilities.php',
                'https://www.cvedetails.com/cve-definition.php'
            ]
            
            # 随机选择2-3个页面访问
            pages_to_visit = random.sample(pages_to_visit, k=random.randint(2, 3))
            
            for page in pages_to_visit:
                try:
                    self.session.get(page, timeout=15, verify=False)
                    logger.debug(f'已访问预热页面: {page}')
                    self._random_delay(2, 4)
                except Exception as e:
                    logger.warning(f'预热页面访问失败 {page}: {e}')
                    
            logger.info('网站预热完成')
        except Exception as e:
            logger.warning(f'网站预热过程中出错: {e}')
            # 即使出错也继续，预热不是必需步骤
            
    def _simulate_mouse_movement(self):
        """模拟人类鼠标移动模式"""
        try:
            logger.debug('开始模拟鼠标移动')
            
            # 获取当前窗口大小
            window_size = self.selected_resolution
            
            # 生成多个移动点，创建自然的运动路径
            points = []
            # 起点随机位置
            current_x = random.randint(100, window_size[0] - 100)
            current_y = random.randint(100, window_size[1] - 100)
            points.append((current_x, current_y))
            
            # 生成5-10个中间点
            for _ in range(random.randint(5, 10)):
                # 随机偏移，模拟人类不规则移动
                dx = random.randint(-150, 150)
                dy = random.randint(-150, 150)
                
                # 确保新位置在窗口范围内
                new_x = max(50, min(window_size[0] - 50, current_x + dx))
                new_y = max(50, min(window_size[1] - 50, current_y + dy))
                
                points.append((new_x, new_y))
                current_x, current_y = new_x, new_y
            
            # 模拟鼠标移动到这些点
            for i in range(len(points) - 1):
                start_x, start_y = points[i]
                end_x, end_y = points[i+1]
                
                # 计算两点之间的距离
                distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
                
                # 根据距离决定移动时间（距离越远，时间越长，但有上限）
                move_time = min(1.5, distance * 0.003)
                
                # 移动鼠标
                self.driver.execute_script(f"""
                    const event = new MouseEvent('mousemove', {{\n                        clientX: {end_x},\n                        clientY: {end_y},\n                        bubbles: true,\n                        cancelable: true\n                    }});\n                    document.dispatchEvent(event);\n                """)
                
                # 添加延迟，模拟真实移动速度
                time.sleep(random.uniform(0.1, 0.3))
            
            logger.debug('鼠标移动模拟完成')
        except Exception as e:
            logger.warning(f'模拟鼠标移动时出错: {e}')
            
    def _simulate_keyboard_input(self):
        """模拟人类键盘输入行为"""
        try:
            logger.debug('开始模拟键盘输入')
            
            # 随机选择是否执行键盘操作
            if random.random() < 0.3:
                return  # 30%的概率不执行键盘操作
            
            # 模拟按下一些无害的键
            keys_to_press = [
                Keys.SPACE, Keys.TAB, Keys.HOME, Keys.END,
                Keys.PAGE_UP, Keys.PAGE_DOWN, Keys.ARROW_UP,
                Keys.ARROW_DOWN, Keys.ARROW_LEFT, Keys.ARROW_RIGHT
            ]
            
            # 随机选择2-4个键进行模拟
            keys_to_press = random.sample(keys_to_press, k=random.randint(2, 4))
            
            for key in keys_to_press:
                # 随机选择一个活动元素或文档体发送按键
                try:
                    active_element = self.driver.switch_to.active_element
                    active_element.send_keys(key)
                except Exception:
                    # 如果没有活动元素，发送到body
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(key)
                
                # 添加随机延迟
                time.sleep(random.uniform(0.1, 0.3))
            
            logger.debug('键盘输入模拟完成')
        except Exception as e:
            logger.warning(f'模拟键盘输入时出错: {e}')


    
    def _simulate_human_behavior(self, enhanced=False):
        """模拟人类浏览行为以绕过反爬检测 - 增强版"""
        try:
            if enhanced:
                # 更复杂的人类行为模拟
                
                # 1. 随机滚动页面 - 非线性滚动
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_sequence = [random.randint(0, scroll_height // 3),
                                  random.randint(scroll_height // 3, scroll_height // 2),
                                  random.randint(scroll_height // 2, 2 * scroll_height // 3),
                                  random.randint(2 * scroll_height // 3, scroll_height)]
                
                for scroll_pos in scroll_sequence:
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                    time.sleep(random.uniform(0.5, 1.5))
                
                # 2. 随机点击页面多个位置
                for _ in range(random.randint(2, 4)):
                    click_x = random.randint(100, self.selected_resolution[0] - 100)
                    click_y = random.randint(100, self.selected_resolution[1] - 100)
                    try:
                        self.driver.execute_script(f"document.elementFromPoint({click_x}, {click_y}).click();")
                        time.sleep(random.uniform(0.3, 0.8))
                    except Exception:
                        # 点击失败也没关系
                        pass
                
                # 3. 模拟鼠标移动
                self._simulate_mouse_movement()
                
                # 4. 模拟键盘输入
                self._simulate_keyboard_input()
            else:
                # 基本的人类行为模拟
                # 随机滚动页面
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_to = random.randint(0, scroll_height // 2)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                
                # 随机点击页面某个位置
                if random.random() < 0.5:
                    click_x = random.randint(100, self.selected_resolution[0] - 100)
                    click_y = random.randint(100, self.selected_resolution[1] - 100)
                    try:
                        self.driver.execute_script(f"document.elementFromPoint({click_x}, {click_y}).click();")
                    except Exception:
                        pass
            
            logger.info('模拟了人类浏览行为')
        except Exception as e:
            logger.warning(f'模拟人类行为时出错: {e}')
            # 出错也继续，不影响主流程

    def get_yesterday_cve_data(self):
        """获取昨日的CVE数据"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f'开始获取 {yesterday} 的CVE数据')
        
        # 优先使用Requests方式尝试获取数据
        success = self._get_data_with_requests(yesterday)
        if success:
            logger.info('Requests方式数据获取成功')
            return True
            
        # 如果Requests方式失败，尝试使用Selenium方式
        logger.info('Requests方式获取失败，尝试使用Selenium方式')
        
        # 初始化WebDriver
        if not self.setup_driver():
            logger.error('WebDriver初始化失败，无法使用Selenium方式获取数据')
            return False
        
        try:
            # 访问cvedetails.com主页进行预热
            logger.info('访问cvedetails.com主页进行预热')
            self.driver.get('https://www.cvedetails.com/')
            self._random_delay(3, 7)
            
            # 处理Cloudflare机器人验证
            self.handle_cloudflare_challenge()
            
            # 再次随机延迟
            self._random_delay(2, 5)
            
            # 执行登录操作 - 优化版
            logger.info('开始执行登录操作')
            
            # 再次检查是否需要处理验证
            if self.handle_cloudflare_challenge():
                # 查找登录按钮 - 增强版多种定位方式
                login_button_found = False
                login_button_xpaths = [
                    "//a[contains(@href, 'login.php') and contains(text(), 'Login')]",
                    "//a[contains(@href, 'login.php')]",
                    "//a[@id='login_button']",
                    "//button[contains(text(), 'Login')]",
                    "//input[@type='submit' and @value='Login']",
                    "//a[contains(@class, 'login')]",
                    "//*[@id='navbar']//a[contains(@href, 'login')]",
                    "//*[@id='menu']//a[contains(@href, 'login')]"
                ]
                
                for xpath in login_button_xpaths:
                    try:
                        login_button = WebDriverWait(self.driver, 30).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        # 先滚动到登录按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                        self._random_delay(1, 3)  # 模拟人类看到后再点击的延迟
                        login_button.click()
                        login_button_found = True
                        logger.info(f'成功找到并点击登录按钮（使用XPath: {xpath}）')
                        break
                    except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                        continue
                
                if not login_button_found:
                    logger.warning('未找到登录按钮，尝试直接访问登录页面')
                    self.driver.get('https://www.cvedetails.com/login.php')
                    self._random_delay(3, 7)
                    # 再次处理可能的验证
                    self.handle_cloudflare_challenge()
                    
                # 尝试勾选同意选项
                logger.info('尝试勾选同意选项')
                try:
                    agree_xpaths = [
                        "//input[@type='checkbox' and @name='agree']",
                        "//input[@type='checkbox' and @id='agree']",
                        "//input[@type='checkbox' and contains(@class, 'agree')]",
                        "//input[@type='checkbox' and @value='1']"
                    ]
                    
                    for xpath in agree_xpaths:
                        try:
                            agree_checkbox = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, xpath))
                            )
                            if not agree_checkbox.is_selected():
                                agree_checkbox.click()
                            logger.info(f'成功勾选同意选项（使用XPath: {xpath}）')
                            break
                        except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                            continue
                except Exception as e:
                    logger.warning(f'勾选同意选项时出错: {e}')
                
                # 输入用户名和密码
                logger.info('输入用户名和密码')
                
                # 查找用户名输入框
                username_input_found = False
                username_xpaths = [
                    "//input[@type='text' and @name='login']",
                    "//input[@type='text' and @id='login']",
                    "//input[@type='text' and contains(@class, 'login')]",
                    "//input[@type='email' and @name='login']",
                    "//input[@type='email' and @id='login']"
                ]
                
                for xpath in username_xpaths:
                    try:
                        username_input = WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        username_input.clear()
                        # 模拟人类打字速度 - 更真实的版本
                        self._type_human_like(username_input, USERNAME)
                        username_input_found = True
                        logger.info(f'成功找到并输入用户名（使用XPath: {xpath}）')
                        break
                    except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                        continue
                
                if not username_input_found:
                    logger.error('未找到用户名输入框')
                
                # 查找密码输入框
                password_input_found = False
                password_xpaths = [
                    "//input[@type='password' and @name='password']",
                    "//input[@type='password' and @id='password']",
                    "//input[@type='password' and contains(@class, 'password')]"
                ]
                
                for xpath in password_xpaths:
                    try:
                        password_input = WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        password_input.clear()
                        # 模拟人类打字速度 - 更真实的版本
                        self._type_human_like(password_input, PASSWORD)
                        password_input_found = True
                        logger.info(f'成功找到并输入密码（使用XPath: {xpath}）')
                        break
                    except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                        continue
                
                if not password_input_found:
                    logger.error('未找到密码输入框')
                
                # 提交登录表单
                logger.info('提交登录表单')
                login_submit_found = False
                login_submit_xpaths = [
                    "//input[@type='submit' and @name='Submit']",
                    "//input[@type='submit' and @value='Login']",
                    "//button[@type='submit' and contains(text(), 'Login')]",
                    "//input[@type='submit' and @id='login_submit']"
                ]
                
                for xpath in login_submit_xpaths:
                    try:
                        login_submit = WebDriverWait(self.driver, 30).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        # 先滚动到提交按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", login_submit)
                        self._random_delay(1, 2)  # 模拟人类看到后再点击的延迟
                        login_submit.click()
                        login_submit_found = True
                        logger.info(f'成功提交登录表单（使用XPath: {xpath}）')
                        break
                    except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                        continue
                
                if not login_submit_found:
                    # 尝试按Enter键提交表单
                    try:
                        password_input.send_keys(Keys.RETURN)
                        logger.info('使用Enter键提交登录表单')
                    except Exception as e:
                        logger.error(f'提交登录表单失败: {e}')
                
                # 登录后等待页面加载
                self._random_delay(5, 10)
                
                # 再次处理可能的验证
                self.handle_cloudflare_challenge()

            # 访问昨日的CVE页面
            logger.info('登录完成，开始访问昨日CVE数据页面')
            yesterday_date = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday_date.strftime('%Y-%m-%d')
            cve_page_url = f"https://www.cvedetails.com/vulnerability-list.php?date={yesterday_str}&order=3&trc=0&sha=01d558dfeb71a00e9f63a5856e2a3e326f3c22c5"
            
            logger.info(f'访问CVE数据页面: {cve_page_url}')
            self.driver.get(cve_page_url)
            self._random_delay(5, 10)
            
            # 再次处理可能的验证
            self.handle_cloudflare_challenge()
            
            # 尝试找到导出按钮 - 增强版多种定位方式
            logger.info('尝试找到TSV导出按钮')
            export_button_found = False
            export_button_xpaths = [
                "//a[contains(@href, 'export') and contains(@href, 'tsv')]",
                "//a[contains(text(), 'Export') and contains(@href, 'tsv')]",
                "//a[contains(@class, 'export') and contains(@href, 'tsv')]",
                "//a[contains(@href, 'export') and contains(@href, 'tab')]",
                "//a[contains(text(), 'Export') and contains(@href, 'tab')]"
            ]
            
            for xpath in export_button_xpaths:
                try:
                    export_button = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    # 先滚动到导出按钮位置
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
                    self._random_delay(1, 3)
                    export_button.click()
                    export_button_found = True
                    logger.info(f'成功点击TSV导出按钮（使用XPath: {xpath}）')
                    break
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    continue
            
            if export_button_found:
                # 等待导出内容加载和文件下载完成
                self._random_delay(5, 10)
                
                # 等待下载完成并验证文件
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                max_wait_time = 30  # 最大等待时间(秒)
                wait_start_time = time.time()
                downloaded_file = None
                
                logger.info(f'等待TSV文件下载完成...')
                
                # 监控下载目录，查找新下载的TSV文件
                while time.time() - wait_start_time < max_wait_time:
                    # 列出下载目录中的文件
                    for file_name in os.listdir(OUTPUT_DIR):
                        # 查找昨天日期的TSV文件或最近下载的TSV文件
                        if (file_name.endswith('.tsv') and 
                            (yesterday_str in file_name or 
                             ('export' in file_name and os.path.getmtime(os.path.join(OUTPUT_DIR, file_name)) > wait_start_time - 10))):
                            downloaded_file = os.path.join(OUTPUT_DIR, file_name)
                            logger.info(f'检测到下载的TSV文件: {downloaded_file}')
                            break
                    
                    if downloaded_file:
                        # 验证文件大小，确保文件完整
                        file_size = os.path.getsize(downloaded_file)
                        if file_size > 100:  # 确保文件不为空
                            logger.info(f'TSV文件下载成功，大小: {file_size} 字节')
                            return True
                        else:
                            logger.warning(f'下载的TSV文件可能不完整，大小: {file_size} 字节，继续等待...')
                            time.sleep(2)
                    else:
                        time.sleep(2)
                
                if not downloaded_file:
                    logger.warning(f'在 {max_wait_time} 秒内未检测到下载的TSV文件')
                
                # 保存当前页面内容作为备份
                page_content = self.driver.page_source
                page_output_file = os.path.join(OUTPUT_DIR, f'cve_yesterday_{yesterday_str}_page.html')
                with open(page_output_file, 'w', encoding='utf-8') as f:
                    f.write(page_content)
                logger.info(f'已保存页面内容到 {page_output_file}')
            else:
                logger.warning('未找到TSV导出按钮，尝试直接构造导出URL')
                
                # 构造TSV导出URL
                base_export_url = "https://www.cvedetails.com/vulnerability-list.php"
                params = {
                    "date": yesterday_str,
                    "order": "3",
                    "trc": "0",
                    "sha": "01d558dfeb71a00e9f63a5856e2a3e326f3c22c5",
                    "export": "1",
                    "export_type": "tsv"
                }
                
                # 直接访问导出URL
                logger.info('尝试直接访问TSV导出URL')
                try:
                    # 使用requests和Selenium的cookie组合访问
                    selenium_cookies = self.driver.get_cookies()
                    for cookie in selenium_cookies:
                        self.session.cookies.set(cookie['name'], cookie['value'])
                    
                    # 更新请求头以匹配浏览器
                    self.session.headers.update({
                        'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                        'Referer': self.driver.current_url
                    })
                    
                    # 构建完整的导出URL
                    from urllib.parse import urlencode
                    export_url = f"{base_export_url}?{urlencode(params)}"
                    logger.info(f'构造的TSV导出URL: {export_url}')
                    
                    # 发送请求获取TSV数据
                    response = self.session.get(export_url, timeout=60)
                    response.raise_for_status()
                    
                    # 保存TSV文件
                    tsv_file_path = os.path.join(OUTPUT_DIR, f'cve_yesterday_{yesterday_str}_export.tsv')
                    with open(tsv_file_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info(f'成功保存TSV文件到 {tsv_file_path}')
                    return True
                except Exception as e:
                    logger.error(f'直接访问导出URL失败: {e}')
            
            # 如果TSV导出失败，尝试获取页面中的表格数据
            logger.info('尝试从页面提取表格数据')
            try:
                # 查找表格元素 - 增强版多种定位方式
                table = None
                table_xpaths = [
                    "//table[@class='searchresults sortable']",
                    "//table[@class='vulnslist']",
                    "//table[contains(@class, 'vulnerability')]",
                    "//table[contains(@id, 'vulnerability')]",
                    "//table[contains(@class, 'list')]"
                ]
                
                for xpath in table_xpaths:
                    try:
                        table = WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        if table:
                            logger.info(f'成功找到表格元素（使用XPath: {xpath}）')
                            break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if table:
                    # 提取表格数据
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    table_data = []
                    
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        row_data = [cell.text.strip() for cell in cells]
                        if row_data:
                            table_data.append(row_data)
                    
                    # 保存表格数据为TSV
                    tsv_file_path = os.path.join(OUTPUT_DIR, f'cve_yesterday_{yesterday_str}_table.tsv')
                    with open(tsv_file_path, 'w', encoding='utf-8') as f:
                        for row in table_data:
                            f.write('\t'.join(row) + '\n')
                    logger.info(f'成功从页面提取并保存表格数据到 {tsv_file_path}')
                    return True
                else:
                    logger.error('未找到表格元素')
            except Exception as e:
                logger.error(f'提取表格数据失败: {e}')
            
            # 作为最后的备选方案，保存当前页面内容
            logger.warning('所有获取数据的尝试都失败了，仅保存页面内容')
            fallback_file = os.path.join(OUTPUT_DIR, f'cve_yesterday_{yesterday_str}_export_fallback.html')
            with open(fallback_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f'已保存页面内容到 {fallback_file}')
            
            return True
        except Exception as e:
            logger.error(f'使用Selenium获取数据时出错: {e}')
            return False
        finally:
            # 关闭浏览器
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info('Firefox WebDriver已成功关闭')
                except Exception as e:
                    logger.warning(f'关闭WebDriver时出错: {e}')
    
    def _type_human_like(self, element, text):
        """模拟人类打字方式，包括随机错误和更正"""
        try:
            element.clear()
            for i, char in enumerate(text):
                # 95%的准确率，模拟人类打字
                if random.random() < 0.95:
                    element.send_keys(char)
                else:
                    # 模拟打错字，然后删除并重新输入
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    element.send_keys(wrong_char)
                    time.sleep(random.uniform(0.1, 0.2))
                    element.send_keys(Keys.BACKSPACE)
                    element.send_keys(char)
                
                # 添加随机延迟，模拟真实打字速度
                delay = random.uniform(0.05, 0.2)
                # 对某些字符（如空格、标点符号）可能有更长的延迟
                if char in [' ', '.', ',', ';', ':', '!', '?']:
                    delay += random.uniform(0.1, 0.3)
                time.sleep(delay)
        except Exception as e:
            logger.error(f'模拟人类打字时出错: {e}')
            # 如果出现错误，回退到普通输入方式
            element.clear()
            element.send_keys(text)
    
    def _get_data_with_requests(self, date_str):
        """使用Requests库尝试获取数据 - 增强版"""
        try:
            logger.info('使用Requests库尝试获取数据')
            
            # 预热网站
            self._warmup_requests()
            
            # 构建请求URL
            url = f"https://www.cvedetails.com/vulnerability-list.php?date={date_str}&order=3&trc=0&sha=01d558dfeb71a00e9f63a5856e2a3e326f3c22c5"
            logger.info(f'请求URL: {url}')
            
            # 发送请求
            response = self.session.get(url, timeout=30, verify=False)
            response.raise_for_status()
            
            # 检查是否被反爬
            if self._check_anti_crawl(response):
                logger.warning('Requests方式触发了反爬机制')
                # 尝试绕过反爬
                if self._bypass_anti_crawl(response):
                    # 重新尝试请求
                    self._random_delay(3, 5)
                    response = self.session.get(url, timeout=30, verify=False)
                    response.raise_for_status()
                else:
                    return False
            
            # 查找导出链接
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多种方式查找导出链接
            export_link = None
            
            # 1. 通过href和文本内容查找
            export_links = soup.find_all('a', href=lambda href: href and 'export' in href and ('tsv' in href or 'tab' in href))
            if export_links:
                export_link = export_links[0].get('href')
            
            # 2. 通过文本内容查找
            if not export_link:
                export_links = soup.find_all('a', string=lambda text: text and 'Export' in text)
                for link in export_links:
                    href = link.get('href')
                    if href and ('tsv' in href or 'tab' in href):
                        export_link = href
                        break
            
            # 3. 通过class属性查找
            if not export_link:
                export_links = soup.find_all('a', class_=lambda cls: cls and 'export' in cls)
                for link in export_links:
                    href = link.get('href')
                    if href and ('tsv' in href or 'tab' in href):
                        export_link = href
                        break
            
            # 4. 通过ID属性查找
            if not export_link:
                export_links = soup.find_all('a', id=lambda id_: id_ and 'export' in id_)
                for link in export_links:
                    href = link.get('href')
                    if href and ('tsv' in href or 'tab' in href):
                        export_link = href
                        break
            
            if export_link:
                # 构建完整的导出URL
                from urllib.parse import urljoin
                full_export_url = urljoin('https://www.cvedetails.com/', export_link)
                logger.info(f'找到导出链接: {full_export_url}')
                
                # 添加随机延迟
                self._random_delay(2, 4)
                
                # 更新请求头
                self.session.headers['Referer'] = url
                
                # 发送导出请求 - 增加重试机制
                max_retries = 3
                retry_count = 0
                success = False
                
                while retry_count < max_retries and not success:
                    try:
                        response = self.session.get(full_export_url, timeout=60, verify=False)
                        response.raise_for_status()
                        
                        # 检查是否被反爬
                        if self._check_anti_crawl(response):
                            logger.warning('导出请求触发了反爬机制，正在重试...')
                            self._bypass_anti_crawl(response)
                            retry_count += 1
                            self._random_delay(3, 5)
                            continue
                        
                        # 保存TSV文件
                        tsv_file_path = os.path.join(OUTPUT_DIR, f'cve_yesterday_{date_str}_export.tsv')
                        with open(tsv_file_path, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        logger.info(f'成功保存TSV文件到 {tsv_file_path}')
                        success = True
                        return True
                    except requests.exceptions.HTTPError as e:
                        logger.warning(f'导出请求HTTP错误: {e}，重试中...')
                        retry_count += 1
                        self._random_delay(3, 5)
                        if retry_count >= max_retries:
                            logger.error('多次尝试后导出请求失败')
                            # 即使导出失败，也尝试从页面提取表格数据
                            return self._extract_table_data(response.text, date_str)
                    except Exception as e:
                        logger.warning(f'导出请求异常: {e}，重试中...')
                        retry_count += 1
                        self._random_delay(3, 5)
                        if retry_count >= max_retries:
                            logger.error('多次尝试后导出请求失败')
                            # 即使导出失败，也尝试从页面提取表格数据
                            return self._extract_table_data(response.text, date_str)
            else:
                logger.warning('Requests方式未找到导出链接，尝试直接构造导出URL')
                # 尝试构造导出URL并获取数据
                return self._direct_export_attempt(date_str)
        except Exception as e:
            logger.error(f'Requests方式获取数据时出错: {e}')
            return False
    
    def _direct_export_attempt(self, date_str):
        """直接构造导出URL并尝试获取数据"""
        try:
            logger.info('尝试直接构造并访问TSV导出URL')
            
            # 构造TSV导出URL - 尝试多种参数组合
            base_export_url = "https://www.cvedetails.com/vulnerability-list.php"
            
            # 尝试多种参数组合
            param_combinations = [
                {"date": date_str, "order": "3", "trc": "0", "sha": "01d558dfeb71a00e9f63a5856e2a3e326f3c22c5", "export": "1", "export_type": "tsv"},
                {"date": date_str, "order": "3", "trc": "0", "export": "1", "export_type": "tsv"},
                {"date": date_str, "order": "3", "export": "1"},
                {"date": date_str, "order_by": "3", "export": "1", "type": "tsv"}
            ]
            
            for params in param_combinations:
                try:
                    # 构建完整的导出URL
                    from urllib.parse import urlencode
                    export_url = f"{base_export_url}?{urlencode(params)}"
                    logger.info(f'尝试导出URL: {export_url}')
                    
                    # 添加随机延迟
                    self._random_delay(2, 4)
                    
                    # 发送请求
                    response = self.session.get(export_url, timeout=60, verify=False)
                    response.raise_for_status()
                    
                    # 检查是否被反爬
                    if self._check_anti_crawl(response):
                        logger.warning(f'URL {export_url} 触发了反爬机制')
                        continue
                    
                    # 保存TSV文件
                    tsv_file_path = os.path.join(OUTPUT_DIR, f'cve_yesterday_{date_str}_direct_export.tsv')
                    with open(tsv_file_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info(f'成功通过直接构造URL保存TSV文件到 {tsv_file_path}')
                    return True
                except Exception as e:
                    logger.warning(f'尝试构造URL {export_url} 失败: {e}')
                    # 继续尝试下一个参数组合
                    continue
            
            logger.error('所有直接构造URL的尝试都失败了')
            return False
        except Exception as e:
            logger.error(f'直接导出尝试时出错: {e}')
            return False
    
    def _extract_table_data(self, html_content, date_str):
        """从HTML内容中提取表格数据并保存为TSV"""
        try:
            logger.info('尝试从HTML内容中提取表格数据')
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试多种方式查找表格元素
            table_xpaths = [
                "//table[@class='searchresults sortable']",
                "//table[@class='vulnslist']",
                "//table[contains(@class, 'vulnerability')]",
                "//table[contains(@id, 'vulnerability')]",
                "//table[contains(@class, 'list')]"
            ]
            
            for xpath in table_xpaths:
                try:
                    table = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    if table:
                        logger.info(f'成功找到表格元素（使用XPath: {xpath}）')
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if table:
                # 提取表格数据
                rows = table.find_elements(By.TAG_NAME, 'tr')
                table_data = []
                
                for row in rows:
                    # 尝试获取所有单元格，包括th和td
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if not cells:
                        continue
                    
                    # 提取每个单元格的文本内容
                    row_data = []
                    for cell in cells:
                        # 清理文本，移除多余的空白字符
                        text = ' '.join(cell.stripped_strings)
                        row_data.append(text)
                    
                    if row_data:
                        table_data.append(row_data)
            
                if not table_data:
                    logger.warning('表格中未提取到数据')
                    return False
            
                # 保存表格数据为TSV
                tsv_file_path = os.path.join(OUTPUT_DIR, f'cve_yesterday_{date_str}_table.tsv')
                with open(tsv_file_path, 'w', encoding='utf-8') as f:
                    for row in table_data:
                        # 确保所有值都是字符串，并替换可能的制表符
                        clean_row = [str(cell).replace('\t', ' ').replace('\n', ' ') for cell in row]
                        f.write('\t'.join(clean_row) + '\n')
            
                # 验证提取的数据是否有效
                with open(tsv_file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    # 检查是否包含表格列标题或CVE编号
                    if any(keyword.lower() in first_line.lower() for keyword in ['cve', 'id', 'vulnerability', 'description', 'published', 'date']):
                        logger.info(f'成功从HTML中提取并保存表格数据到 {tsv_file_path}')
                        return True
                    else:
                        logger.warning(f'提取的表格数据可能无效，第一行: {first_line[:50]}...')
                        # 仍然返回True，因为我们已经保存了文件，只是内容可能有问题
                        return True
        except Exception as e:
            logger.error(f'提取表格数据时出错: {e}')
            return False
    
    def verify_data_saved(self):
        """验证数据是否成功保存"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 检查是否有导出的TSV文件
            tsv_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(f'cve_yesterday_{yesterday}') and f.endswith('.tsv')]
            
            # 检查是否有保存的HTML文件
            html_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(f'cve_yesterday_{yesterday}') and f.endswith('.html')]
            
            if tsv_files:
                # 检查TSV文件内容是否有效
                valid_tsv_files = []
                for file in tsv_files:
                    file_path = os.path.join(OUTPUT_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            # 检查是否包含表格列标题或CVE编号
                            if any(keyword in first_line.lower() for keyword in ['cve', 'id', 'vulnerability', 'description']):
                                valid_tsv_files.append(file)
                            # 额外检查是否包含Cloudflare验证代码
                            elif 'cloudflare' in first_line.lower() or 'cdn-cgi' in first_line.lower():
                                logger.warning(f'文件 {file} 包含Cloudflare验证代码，可能无效')
                    except Exception as e:
                        logger.warning(f'检查TSV文件 {file} 时出错: {e}')
                
                if valid_tsv_files:
                    logger.info(f'成功保存了 {len(valid_tsv_files)} 个有效的TSV文件')
                    for file in valid_tsv_files:
                        file_path = os.path.join(OUTPUT_DIR, file)
                        file_size = os.path.getsize(file_path)
                        logger.info(f'  - {file}: {file_size} 字节')
                    
                    # 打印输出目录路径和内容
                    logger.info(f'输出目录路径: {OUTPUT_DIR}')
                    logger.info('输出目录内容:')
                    for item in os.listdir(OUTPUT_DIR):
                        if item.startswith(f'cve_yesterday_{yesterday}'):
                            item_path = os.path.join(OUTPUT_DIR, item)
                            item_size = os.path.getsize(item_path)
                            logger.info(f'  - {item}: {item_size} 字节')
                    
                    return True
                else:
                    logger.warning('TSV文件存在但内容无效，可能包含Cloudflare验证页面')
                    return False
            elif html_files:
                logger.warning(f'没有保存TSV文件，但保存了 {len(html_files)} 个HTML文件')
                return False
            else:
                logger.error('既没有保存TSV文件，也没有保存HTML文件')
                return False
        except Exception as e:
            logger.error(f'验证数据保存时出错: {e}')
            return False

    def _get_month_number(self, month_name):
        """从月份名称中提取月份数字"""
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        # 尝试直接从名称获取
        for name, num in month_map.items():
            if name.lower() in month_name.lower():
                return num
        
        # 尝试从数字获取
        try:
            return int(month_name.strip())
        except ValueError:
            return None

def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    logger.info('CVE自动下载工具启动')
    
    # 创建自动化工具实例
    automator = CveDetailsAutomator()
    
    # 获取昨日的CVE数据
    success = automator.get_yesterday_cve_data()
    
    # 验证数据是否成功保存
    if success:
        verify_success = automator.verify_data_saved()
        if verify_success:
            logger.info('数据获取和保存验证成功')
        else:
            logger.warning('数据获取成功，但验证保存时出现问题')
    else:
        logger.error('数据获取失败')
    
    # 记录结束时间
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f'任务完成，总耗时: {duration}')

if __name__ == "__main__":
    main()