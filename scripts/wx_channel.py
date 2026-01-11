import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, BrowserContext, Playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class VideoPublishTask:
    """Data class representing a video publishing task."""
    video_path: Path
    description: str
    title: str = ""  # Added title field
    cover_path: Optional[Path] = None
    # Potential future fields: tags, location, schedule_time, etc.

    def validate(self):
        """Validates that the necessary files exist."""
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        if self.cover_path and not self.cover_path.exists():
            raise FileNotFoundError(f"Cover file not found: {self.cover_path}")


class WeChatChannelPublisher:
    """
    Automates publishing videos to WeChat Channels (视频号) using Playwright.
    """
    
    BASE_URL = "https://channels.weixin.qq.com"
    CREATOR_URL = "https://channels.weixin.qq.com/platform/post/create"
    AUTH_FILE = "auth_wx.json"

    def __init__(self, headless: bool = False, auth_path: str = ".", debug: bool = False):
        """
        Initialize the publisher.

        Args:
            headless: Whether to run the browser in headless mode. 
                      Defaults to False for visibility during potential manual login.
            auth_path: Directory to store the authentication state file.
            debug: Whether to generate debug files (screenshots, HTML dumps). 
                   Defaults to False.
        """
        self.headless = headless
        self.debug = debug
        self.auth_file_path = Path(auth_path) / self.AUTH_FILE
        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Starts the Playwright browser and context."""
        logger.info("Starting Playwright...")
        self._playwright = sync_playwright().start()
        
        # Launch browser
        # We use channel="chrome" or just chromium. Chromium is usually bundled.
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--start-maximized"] # Open maximized to ensure elements are visible
        )
        
        # Load auth state if exists
        if self.auth_file_path.exists():
            logger.info(f"Loading auth state from {self.auth_file_path}")
            self._context = self._browser.new_context(
                storage_state=str(self.auth_file_path),
                no_viewport=True  # Allow window to determine viewport
            )
        else:
            logger.info("No auth state found. Starting fresh context.")
            self._context = self._browser.new_context(no_viewport=True)

        self._page = self._context.new_page()

    def close(self):
        """Closes the browser and Playwright."""
        if self._context:
            # Save state before closing if we are logged in
            try:
                self._save_auth_state()
            except Exception as e:
                logger.warning(f"Failed to save auth state on close: {e}")
            self._context.close()
        
        if self._browser:
            self._browser.close()
        
        if self._playwright:
            self._playwright.stop()
        
        logger.info("Browser closed.")

    def _save_auth_state(self):
        """Saves the current browser context storage state to file."""
        if self._context:
            self._context.storage_state(path=str(self.auth_file_path))
            logger.info(f"Auth state saved to {self.auth_file_path}")

    def login(self, timeout: int = 60):
        """
        Checks if logged in. If not, waits for user to scan QR code.
        
        Args:
            timeout: How long to wait for login (in seconds) if manual intervention is needed.
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        logger.info("Navigating to WeChat Channels...")
        self._page.goto(self.BASE_URL)
        
        try:
            # Adjust this selector based on actual DOM of logged-in state
            logger.info("Checking login status...")
            
            # Wait a moment for load - use domcontentloaded instead of networkidle which can be flaky
            self._page.wait_for_load_state("domcontentloaded")
            
            # Check current URL. If it contains 'login', we definitely need to login.
            
            if "login" in self._page.url:
                 logger.info("Not logged in (url contains 'login'). Please scan the QR code.")
                 # Wait for user to scan and login. 
                 # We assume successful login redirects away from a URL containing 'login'
                 # or redirects to /platform
                 self._page.wait_for_url(lambda url: "login" not in url, timeout=timeout * 1000)
                 logger.info("Login detected (URL changed)!")
                 
                 # Wait a bit more for the post-login page to stabilize
                 self._page.wait_for_load_state("domcontentloaded")
                 self._save_auth_state()
            else:
                logger.info(f"URL does not contain 'login': {self._page.url}. Assuming logged in.")

        except Exception as e:
            logger.error(f"Login check failed or timed out: {e}")
            # Capture screenshot for debugging
            if self.debug:
                try:
                    self._page.screenshot(path="login_error.png")
                    logger.info("Saved screenshot to login_error.png")
                except:
                    pass
            raise

    def publish(self, task: VideoPublishTask):
        """
        Executes the publishing workflow.
        
        Args:
            task: The video publishing task containing file paths and metadata.
        """
        task.validate()
        
        if not self._page:
            raise RuntimeError("Browser not started.")

        logger.info("Navigating to creation page...")
        try:
            self._page.goto(self.CREATOR_URL)
            self._page.wait_for_load_state("domcontentloaded")
            # Debug: Snapshot after navigation
            if self.debug:
                self._page.screenshot(path="create_page_loaded.png")
        except Exception as e:
            logger.error(f"Navigation to create page failed: {e}")
            if self.debug:
                self._page.screenshot(path="nav_error.png")
            raise e

        # Check if we were redirected to login
        if "login" in self._page.url:
             logger.warning("Redirected to login page during publish. Session might have expired.")
             if self.debug:
                 self._page.screenshot(path="session_expired.png")
             raise RuntimeError("Session expired. Please re-login.")

        # 1. Upload Video
        # We need to find the file input for video.
        logger.info(f"Uploading video: {task.video_path}")

        try:
            # Direct input setting (faster if input exists)
            self._page.set_input_files('input[type="file"]', str(task.video_path))
            
        except Exception as e:
            logger.error(f"Failed to initiate video upload: {e}")
            raise e

        logger.info("Waiting for upload to complete (timeout: 300s)...")
        
        # 2. Fill Description
        logger.info("Waiting for description editor to appear...")
        
        # Hard wait to let upload start and UI stabilize
        time.sleep(10)
        
        try:
            # 2.1 Fill Description using the specific selector provided by user
            logger.info("Looking for description editor...")
            
            # Wait for either the editor or the placeholder text which might be inside it
            self._page.wait_for_selector('div.input-editor, div[data-placeholder="添加描述"]', state="visible", timeout=300000)
            
            editor = self._page.locator('div.input-editor, div[data-placeholder="添加描述"]').first
            editor.click()
            editor.type(task.description)
            logger.info("Description filled.")
            
            # 2.2 Fill Short Title (if available)
            if task.title:
                logger.info(f"Filling title: {task.title}")
                try:
                    title_input = self._page.locator('input.weui-desktop-form__input[placeholder*="概括视频主要内容"]')
                    if title_input.is_visible():
                        title_input.fill(task.title)
                    else:
                        logger.info("Title input not visible, skipping.")
                except Exception as e:
                    logger.warning(f"Failed to fill title: {e}")

        except Exception as e:
            logger.warning(f"Failed to fill description: {e}")

            if self.debug:
                self._page.screenshot(path="publish_error.png")
            raise e

        # 3. Check "Original" (勾选原创) - 放在最后避免弹窗干扰
        logger.info("Checking 'Original' checkbox...")
        try:
            # Try multiple possible selectors for the original checkbox
            original_selectors = [
                'input[type="checkbox"]:near(text="原创")',
                'label:has-text("原创") input[type="checkbox"]',
                'input[type="checkbox"]',
                '.weui-desktop-checkbox:has-text("原创")',
                'text=原创',
            ]
            
            original_checked = False
            for selector in original_selectors:
                try:
                    checkbox = self._page.locator(selector).first
                    if checkbox.is_visible(timeout=2000):
                        # Check if already checked
                        if checkbox.get_attribute('checked') != 'true':
                            checkbox.click()
                            logger.info("Original checkbox checked.")
                        else:
                            logger.info("Original checkbox already checked.")
                        original_checked = True
                        break
                except Exception:
                    continue
            
            if not original_checked:
                # Fallback: try to find by text and click nearby checkbox
                try:
                    original_text = self._page.locator('text=原创').first
                    if original_text.is_visible(timeout=2000):
                        # Click the text or nearby element
                        original_text.click()
                        logger.info("Clicked 'Original' text.")
                        original_checked = True
                except Exception:
                    pass
            
            if not original_checked:
                logger.warning("Could not find or check 'Original' checkbox. Please check manually.")
        except Exception as e:
            logger.warning(f"Failed to check 'Original' checkbox: {e}")

        
        # 4. Submit
        # logger.info("Clicking publish...")
        # self._page.click('button:has-text("发表")')
        
        # For safety in this demo, we do NOT actually click publish.
        logger.info("DRY RUN: Ready to publish. Skipping actual click on 'Publish' button.")
        
        # Wait a bit to observe result in non-headless mode
        if not self.headless:
            time.sleep(5)
