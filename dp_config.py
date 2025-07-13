import time
from functools import wraps
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys
import os
from loguru import logger
import random
import json
import requests
import zipfile
import shutil

# 自定义日志格式
logger.add("logfile.log", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}")

# 插件下载地址配置
PLUGIN_URLS = {
    "cloudflare_ua_patch": "https://github.com/gua12345/DrissionPage_Base_Code/releases/download/v1/cloudflare_ua_patch.zip",
    "my-fingerprint-chrome": "https://github.com/gua12345/DrissionPage_Base_Code/releases/download/v1/my-fingerprint-chrome-v2.5.1.zip",
    "turnstilePatch": "https://github.com/gua12345/DrissionPage_Base_Code/releases/download/v1/turnstilePatch.zip"
}

def check_and_download_plugin(plugin_name):
    """
    检查插件是否存在，如果不存在则询问用户是否下载

    Args:
        plugin_name (str): 插件名称

    Returns:
        bool: 插件是否可用（存在或下载成功）
    """
    plugin_path = os.path.join(os.getcwd(), plugin_name)

    # 检查插件是否存在
    if os.path.exists(plugin_path):
        logger.info(f"插件 {plugin_name} 已存在")
        return True

    # 插件不存在，询问用户是否下载
    logger.warning(f"插件 {plugin_name} 不存在")

    if plugin_name not in PLUGIN_URLS:
        logger.error(f"未找到插件 {plugin_name} 的下载地址")
        return False

    # 询问用户是否下载
    while True:
        user_input = input(f"插件 {plugin_name} 不存在，是否自动下载？(y/n): ").strip().lower()
        if user_input in ['y', 'yes', '是']:
            return download_plugin(plugin_name)
        elif user_input in ['n', 'no', '否']:
            logger.info(f"用户选择不下载插件 {plugin_name}")
            return False
        else:
            print("请输入 y/yes/是 或 n/no/否")

def download_plugin(plugin_name):
    """
    下载并解压插件

    Args:
        plugin_name (str): 插件名称

    Returns:
        bool: 下载是否成功
    """
    try:
        url = PLUGIN_URLS[plugin_name]
        logger.info(f"开始下载插件 {plugin_name} 从 {url}")

        # 下载文件
        response = requests.get(url, stream=True)
        response.raise_for_status()

        zip_filename = f"{plugin_name}.zip"

        # 保存zip文件
        with open(zip_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"插件 {plugin_name} 下载完成")

        # 解压文件
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall('.')

        # 删除zip文件
        os.remove(zip_filename)

        # 验证解压后的文件夹是否存在
        plugin_path = os.path.join(os.getcwd(), plugin_name)
        if os.path.exists(plugin_path):
            logger.info(f"插件 {plugin_name} 安装成功")
            return True
        else:
            logger.error(f"插件 {plugin_name} 解压后未找到对应文件夹")
            return False

    except requests.RequestException as e:
        logger.error(f"下载插件 {plugin_name} 失败: {e}")
        return False
    except zipfile.BadZipFile as e:
        logger.error(f"解压插件 {plugin_name} 失败: {e}")
        return False
    except Exception as e:
        logger.error(f"安装插件 {plugin_name} 时发生未知错误: {e}")
        return False


def retry_on_exception(retries=3, delay=2, backoff=1, jitter=0.1):
    """
    通用重试装饰器
    Args:
        retries (int): 最大重试次数
        delay (int): 基础延迟时间(秒)
        backoff (float): 退避系数(每次重试后延迟时间乘以这个系数)
        jitter (float): 随机抖动范围(0-1之间，为了防止同时重试)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            # 格式化参数
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            func_call_str = f"{func.__name__}({signature})"

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:  # 如果不是最后一次尝试
                        # 计算延迟时间
                        sleep_time = delay * (backoff ** attempt)
                        # 添加随机抖动
                        if jitter:
                            sleep_time += random.uniform(0, jitter * sleep_time)
                        logger.warning(f"函数 {func_call_str} 第 {attempt + 1} 次执行失败: {str(e)}")
                        logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"函数 {func_call_str} 重试耗尽，最后错误: {str(e)}")
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"函数 {func_call_str} 重试耗尽，但未捕获到异常")

        return wrapper

    return decorator

class GuaPage(ChromiumPage):
    def __init__(self, options=None):
        super().__init__(options)

    @retry_on_exception(retries=3, delay=3)
    def click_with_retry(self, selector: str, element = None, timeout: int = 10) -> bool:
        """
        带重试机制的点击方法

        Args:
            selector (str): 元素选择器
            element (WebElement, optional): 已找到的元素对象. Defaults to None.
            timeout (int, optional): 等待超时时间(秒). Defaults to 10.

        Returns:
            bool: 点击是否成功
        """
        if element is None:
            ele = self.ele(selector, timeout=timeout)
            ele.click()
            logger.info(f"成功点击元素: {selector}")
            return True
        else:
            ele = element
            ele.click()
            logger.info(f"成功点击元素: {selector}")
            return True

    @retry_on_exception(retries=3, delay=3)
    def input_with_retry(self, selector: str, text: str, element = None, timeout: int = 10) -> bool:
        """
        带重试机制的输入方法

        Args:
            selector (str): 元素选择器
            text (str): 要输入的文本
            element (WebElement, optional): 已找到的元素对象. Defaults to None.
            timeout (int, optional): 等待超时时间(秒). Defaults to 10.

        Returns:
            bool: 输入是否成功
        """
        if element is None:
            ele = self.ele(selector, timeout=timeout)
            ele.clear()
            ele.input(text)
            logger.info(f"成功输入文本到元素: {selector}")
            return True
        else:
            ele = element
            ele.clear()
            ele.input(text)
            logger.info(f"成功输入文本到元素: {selector}")
            return True

    @retry_on_exception(retries=5, delay=3)
    def actions_input_with_retry(self, selector: str, text: str, element = None, timeout: int = 10) -> bool:
        """
        带重试机制的动作链输入方法

        Args:
            selector (str): 元素选择器
            text (str): 要输入的文本
            element (WebElement, optional): 已找到的元素对象. Defaults to None.
            timeout (int, optional): 等待超时时间(秒). Defaults to 10.

        Returns:
            bool: 输入是否成功
        """
        if element is None:
            ele = self.ele(selector, timeout=timeout)
            self.actions.click(ele)
            self.actions.input(text)
            logger.info(f"成功通过动作链输入文本到元素: {selector}")
            return True
        else:
            ele = element
            self.actions.click(ele)
            self.actions.input(text)
            logger.info(f"成功通过动作链输入文本到元素 {selector}")
            return True

    @retry_on_exception(retries=5, delay=3)
    def actions_click_with_retry(self, selector: str, element= None, timeout: int = 10) -> bool:
        """
        带重试机制的动作链点击方法

        Args:
            selector (str): 元素选择器
            element (WebElement, optional): 已找到的元素对象. Defaults to None.
            timeout (int, optional): 等待超时时间(秒). Defaults to 10.

        Returns:
            bool: 点击是否成功
        """
        if element is None:
            ele = self.ele(selector, timeout=timeout)
            self.actions.click(ele)
            logger.info(f"成功通过动作链点击元素: {selector}")
            return True
        else:
            ele = element
            self.actions.click(ele)
            logger.info(f"成功通过动作链点击元素: {selector}")
            return True

def set_driver(headless=False, browser_path=None, user_agent=None, proxy=None, cf_bypass=True, random_fingerprint=True, ua_patch=True):
    # 系统判断
    is_windows = os.name == 'nt'

    # 浏览器默认路径
    windows_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    linux_paths = [
        '/usr/bin/google-chrome',  # Chrome默认路径
        '/usr/bin/chromium',  # Chromium默认路径
        '/usr/bin/chromium-browser',  # Ubuntu Chromium默认路径
        '/usr/bin/microsoft-edge',  # Edge默认路径
        '/snap/bin/chromium',  # Snap安装的Chromium路径
        '/usr/lib/chromium/chromium',  # 某些发行版的Chromium路径
        '/usr/lib/chromium-browser/chromium-browser'
    ]

    # 根据系统选择搜索路径
    default_paths = windows_paths if is_windows else linux_paths

    # 如果未指定路径，则自动检测
    if not browser_path:
        for path in default_paths:
            if os.path.exists(path):
                browser_path = path
                break
        if not browser_path:
            raise FileNotFoundError("未找到可用的浏览器，请手动指定browser_path参数")

    co = ChromiumOptions().set_paths(browser_path=browser_path)

    # 权限检测
    if is_windows:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    else:
        try:
            is_admin = os.geteuid() == 0
        except AttributeError:
            is_admin = False

    if is_admin:
        # 管理员/root环境下的必要设置
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        if not is_windows:
            co.set_argument('--disable-gpu')  # Linux环境可能需要
            co.set_argument('--disable-software-rasterizer')

    # 通用设置
    co.set_pref(arg='profile.default_content_settings.popups', value='0')
    co.set_pref('credentials_enable_service', False)
    co.set_argument('--hide-crash-restore-bubble')
    # 设置浏览器语言为英语
    co.set_argument('--lang=en-US')  # 设置浏览器界面语言
    co.set_argument('--accept-languages=en-US,en')  # 设置HTTP请求头语言偏好
    if proxy:
        co.set_proxy(proxy)
    co.headless(headless)

    #co.set_user_agent("Mozilla/5.0 (X11; Linux x86_64)  AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    if user_agent:
        co.set_user_agent(user_agent)
    else:
        co.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    co.new_env()

    # 检查并加载插件
    if cf_bypass:
        if check_and_download_plugin("turnstilePatch"):
            co.add_extension(r"turnstilePatch")
        else:
            logger.warning("turnstilePatch 插件不可用，跳过加载")

    if random_fingerprint:
        if check_and_download_plugin("my-fingerprint-chrome"):
            co.add_extension(r"my-fingerprint-chrome")
        else:
            logger.warning("my-fingerprint-chrome 插件不可用，跳过加载")

    if ua_patch:
        if check_and_download_plugin("cloudflare_ua_patch"):
            co.add_extension(r"cloudflare_ua_patch")
        else:
            logger.warning("cloudflare_ua_patch 插件不可用，跳过加载")

    # 检查并加载 gpt_rf 插件（如果存在）
    if os.path.exists("gpt_rf"):
        co.add_extension("gpt_rf")

    driver = GuaPage(co)
    return driver

def deletecookie(driver):
    driver.set.cookies.clear()
    return

