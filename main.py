import re
import traceback
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, unquote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class ZoomBot(object):
	def __init__(self, driver, meeting_url, bot_name):
		self.driver = driver
		self.meeting_url = meeting_url
		self.bot_name = bot_name
		self.participant_number = 0
		self.participants = []
		self.less_than_2 = 0
		self.stop_ongoing_meeting_override = False
    
	def _is_join_request_denied(self):
		"""Check if meeting join request was denied"""
		return False

	def join_meeting(self, join_attempts=0):
		"""join the meeting"""
		join_attempts += 1
		try:
			self.driver.get(self.meeting_url)
			print(f"LOADING: {self.bot_name}: {self.meeting_url} - {join_attempts} attempts")
			try:
				# Wait until the I Agree button shows
				i_agree_button = WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.ID, "wc_agree1")))
				# Click the element
				i_agree_button.click()
			except:
				pass
			try:
				launch_meeting_css_selector = 'div.mbTuDeF1[role="button"][tabindex="0"]'
				WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, launch_meeting_css_selector)))
				self.driver.find_elements(By.CSS_SELECTOR, launch_meeting_css_selector).click()
				print("clicked launch meeting Element.")
			except:
				pass
			try:
				# Wait until the continue element is visible and clickable
				continue_button_xpath = "//<button[contains(text(), 'Continue without audio or video')]"
				continue_button = WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, continue_button_xpath)))
				# Click the element
				continue_button.click()
			except:
				pass
			# Wait until the input field is visible
			name_input = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.ID, "input-for-name")))
			name_input.send_keys(self.bot_name)
			ask_to_join_button_xpath = "//button[contains(text(), 'Join')]"
			# Wait until the "Ask to join" button is clickable
			ask_to_join_button = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.XPATH, ask_to_join_button_xpath)))
			ask_to_join_button.click() 
			print("Joining the Zoom Meeting")
			# wait for the meeting page to open
			if self.is_meeting_ongoing(get_attempts=0, time_multiplier=3):
				print("join_meeting: Zoom bot joined the meeting successfully")
			else:
				raise AttributeError("CUSTOM CRITICAL ERROR: backend.py: join_meeting: Zoom bot did not join the Meeting")
		except Exception as e:
			# retry initialize 5 times
			if join_attempts >= 5:
				print(traceback.format_exc())
				# Get the HTML content inside the <body> tag
				try:
					WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
					body_html = self.driver.find_element(By.TAG_NAME, "body").get_attribute('innerHTML')
					print(body_html)
					print("join_meeting generated the full HTML of the page for debugging")
				except Exception as e:
					print("join_meeting Failed to generate the full HTML of the page {e}")
				raise
			else:
				print(f"An ERROR OCCURED: While Trying To Join Zoom Meeting, Retrying {join_attempts}.; {e}")
				if self._is_join_request_denied():
					print("Someone in the meeting denied bot's request to join the Zoom meeting, No longer retrying.")
					return
				return self.join_meeting(join_attempts)

	def is_meeting_ongoing(self, get_attempts=0, time_multiplier=1):
		"""Check if meeting is ongoing and Log new participants' names"""
		get_attempts+=1
		try:
			# manual override to make the bot think meeting has stopped
			if self.stop_ongoing_meeting_override:
				return False
			try:
				self.open_participants_window()
				users = self.driver.find_elements(By.CLASS_NAME, "participants-item__name-section")
				if len(users[1:]) < 2 :
					self.less_than_2 += 1
					print(f"less_than_2 = {self.less_than_2}")
					if self.less_than_2 > 10:
						print("Participants are less than 2, so meeting has ended. Hurray, Hurray.")
						return False
				for user in users[1:]:
					tempText = re.findall(r"^<span .*\">(.*)<\/span.*\">(.*)<\/span>", user.get_attribute("innerHTML").strip())
					uName = tempText[0][0] + tempText[0][1]
					if not uName in self.participants:
						self.participants.append(uName)
						print(f"New meeting participant found: {uName}")
				return True
			except Exception as e:
				print(f'WARNING: is_meeting_ongoing: Did not find meeting participants because {e}')
				try:
					WebDriverWait(self.driver, 3*time_multiplier).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Participants']")))
					return True
				except:
					try:
						WebDriverWait(self.driver, 3*time_multiplier).until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="open the chat panel"]')))
						return True
					except:
						pass
		except Exception as e:
			# retry initialize 5 times
			if get_attempts >= 5:
				print(f'ERROR: is_meeting_ongoing: {e}')
				return None
			else:
				print(f"An ERROR OCCURED: is_meeting_ongoing, Retrying {get_attempts}.")
				return self.is_meeting_ongoing(get_attempts)

	def send_chat_message(self, chat_message):
		""" Sends a message to everyone in the meeting, using the chat window """
		try:
			if chat_message.strip() == "":
				print(f"chat_message is empty, {chat_message}")
				return
			print(f"chat_message is {chat_message}")
			if self.js_code:
				print("CRITICAL WARNING/ERROR: You are running send_chat_message after the js_code starts running, this will cause the js_code to break because the meeting_participants window will close")
			# Locate and wait until the chat button is clickable and click it
			WebDriverWait(self.driver, 7).until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="open the chat panel"]'))).click()
			print("chat window button found and clicked")
			# Locate the text area using aria-label
			text_area = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.tiptap.ProseMirror")))
			text_area.send_keys(chat_message)  # Type the message
			print("textarea found and chat_message typed")
			# Locate the send button by its aria-label and click it
			WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.chat-rtf-box__send"))).click() 
			print("send chat button found and clicked")
			self.open_participants_window()
		except Exception as e:
			print(f"send_chat_message: {chat_message} failed because: {e}")
	
	def open_participants_window(self):
		"""used to open the participants window that js_code navigates to Log new participants' names"""
		try:
			WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH,  "//span[text()='Participants']")))
			self.driver.find_elements(By.XPATH, "//span[text()='Participants']")[0].click()
			print("participants window button, found and clicked")
		except Exception as e:
			print(f"ERROR: open_participants_window: failed because: {e}")
		


####### ----   REGION - Functions  ----   ####### 

def initialize_browser(self, browser_path, retries=3):
    """starts the chrome browser in stealth mode"""
    # Initialize chrome_options
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument("--disable-extensions")
    # UI chrome_options
    chrome_options.headless = False
    chrome_options.add_argument("--start-maximized")

    print("LOADING: Opening Chrome, this may take a while.")
    
    # Automatically manage the ChromeDriver with webdriver_manager
    try:
        # Initialize the Chrome WebDriver with the downloaded ChromeDriverManager
        driver = uc.Chrome(
            options=chrome_options,
            browser_executable_path=browser_path,
            driver_executable_path=ChromeDriverManager().install(),
            patcher_force_close=True
        )
        print("LOADING: Finished uc.Chrome.")
        return driver
    except Exception as e:
        print(f"CRITICAL WARNING: Opening Chrome failed because: {e}")
        time.sleep(2)
        raise e


def ensure_url_scheme(url):
    """All URLs passed to the WebDriver must explicitly include the scheme (http:// or https://)
        Web browsers address bar can automatically append the scheme but 
            the WebDriver requires a complete URL
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url
		



####### ----   REGION - Main  ----   ####### 

if __name__== "__main__":
    meeting_url = "PASTE YOUR ZOOM MEETING LINK HERE"
    browser_path = "/usr/local/bin/chrome" # THE FILE PATH TO WHERE YOUR CHROME BROWSER IS.
    bot_name = "ZoomBot"

    # Parse url
    parsed_url = urlparse(meeting_url) # break the url into its components
    if ('zoom.us' in parsed_url.netloc) or ('zoom.us/j/' in meeting_url):
        start_zoom_bot(browser_path, meeting_url, bot_name)
    else:
        print(f"This is an invalid link: {meeting_url}")

    # open chrome browser
    driver = initialize_browser(browser_path)
    # convert the Zoom meeting_url so it opens with zoom website client. 
    if '?' in meeting_url:
        base_url, query_string = meeting_url.split('?') # Split the meeting_url 
        # Replace '/j/' with '/wc/' in the base_url and append '/join'
        if '/j/' in base_url or '/wc/' in base_url:
            new_base_url = base_url.replace('/j/', '/wc/') + '/join'
            meeting_url = new_base_url + '?' + query_string # combine back the meeting_url
        else:
            print("zoom meeting link is wrong: Failed to process the zoom meeting link.")
    else:
        base_url = meeting_url
        query_string = ''
        # Replace '/j/' with '/wc/' in the base_url and append '/join'
        if '/j/' in base_url or '/wc/' in base_url:
            new_base_url = base_url.replace('/j/', '/wc/') + '/join'
            meeting_url = new_base_url # combine back the meeting_url
        else:
            print("zoom meeting link is wrong: Failed to process the zoom meeting link.")
    # start the zoom bot
    meeting_url = ensure_url_scheme(meeting_url)
    zoom_bot = ZoomBot(driver, meeting_url, bot_name)
    # Calling the automation methods
    zoom_bot.join_meeting()
    zoom_bot.send_chat_message("I AM A BOT AND I JUST JOINED THIS MEETING SUCCESSFULLY.")
  
    
