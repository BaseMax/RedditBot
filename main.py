# @Name: bot crawler of reddit with database
# @Author: Max Base
# @Date: 2021-01-24
# @Repository: https://github.com/basemax/RedditBot, still private

import os
import re
import sys
import time
import pickle
import os.path
from os import path
from enum import Enum
import mysql.connector
from selenium import webdriver
from dotenv import load_dotenv, find_dotenv, dotenv_values
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

class ProgramMode(Enum):
  TEST       = 1 # only important messages: FATAL, WARNING
  DEBUG      = 2 # show details of all elements and actions: FATAL, WARNING, INFO
  PRODUCTION = 2 # without messages into stdout: FATAL

class Browser(Enum):
  FIREFOX    = 1
  CHROME     = 2 # chromium, chrome engine
  SAFARI     = 3 # future

class Message(Enum):
  FATAL    = 0
  WARNING  = 1
  INFO     = 2

class Reddit():
  def __init__(self):
    # init config
    # self.mode = ProgramMode.TEST
    self.mode = ProgramMode.DEBUG
    self.browser = Browser.FIREFOX

    # config browser options
    if self.browser == Browser.FIREFOX:
      self.options = webdriver.FirefoxOptions()

      '''
      check Active profile details at `about:support`

      Location of profile is as follows
        - For windows  > /AppData/MozillaFirefoxProfile_name.default
        - For Linux    > /.mozilla/firefox/profile_name.default/
        - For Mac OS X > ~/Library/ApplicationSupport/Firefox/Profiles/profile_name.default/
      '''
      self.profile_directory = 'firefox-profile'
      self.create_directory_if_not_exists(self.profile_directory)

      # get path via os.path.dirname(sys.argv[0])
      self.profile_path = os.getcwd() + os.sep + self.profile_directory
      self.log(Message.INFO, "init", "load profile from " + self.profile_path)

      # self.profile = webdriver.FirefoxProfile(profile_directory=self.profile_path)
      self.profile = webdriver.firefox.firefox_profile.FirefoxProfile(profile_directory=self.profile_path)      

      self.log(Message.INFO, "init", "set profile path to " + self.profile_path)

      self.options.log.level = "warn"
      self.options.set_preference("browser.link.open_newwindow", 3)
      self.options.set_preference("browser.link.open_newwindow.restriction", 0)

    elif self.browser == Browser.CHROME:
      self.options = webdriver.ChromeOptions()

      self.options.add_argument("--profile-directory=Default")
      self.options.add_argument("--disable-notifications")
      # self.options.add_argument("--user-data-dir=.")
      self.options.add_argument("user-data-dir=selenium") 

    # set applications variables and defaults
    self.base_url = "https://www.reddit.com/"
    # set database table names
    self.tables = [
      'post',
    ]
    self.COOKIE = "cookies.pkl"

    # find_dotenv() will be a string and empty when cannot find one file! print( find_dotenv(), len(find_dotenv()), type(find_dotenv()))
    self.env_path = find_dotenv()
    if self.env_path == "":
      self.env_path = "config.env"

    self.config = load_dotenv(dotenv_path=self.env_path)

    # debug information
    self.log(Message.INFO, "loading config .env", self.config)

    # set a database connection
    self.cursor = None
    self.db = mysql.connector.connect(
      host=os.getenv("DB_HOST"),
      user=os.getenv("DB_USERNAME"),
      password=os.getenv("DB_PASSWORD"),
      database=os.getenv("DB_NAME")
    )

  def create_directory(self, name):
    os.makedirs(name)

  def create_directory_if_not_exists(self, name):
    if not os.path.exists(name):
        self.create_directory(name)

  def browser_open(self, link):
    self.log(Message.INFO, "browser_open", link)
    self.driver.get(link)

    if self.browser == Browser.FIREFOX:
      if sys.platform.startswith('win32'):
        command = "xcopy " + self.profile_temp_path + " " + self.profile_path +" /Y /G /K /R /E /S /C /H"
      else: #linux, cygwin, darwin, freebsd
        command = "cp -R " + self.profile_temp_path + "/* " + self.profile_path
      
      self.log(Message.INFO, "browser_open", "running " + command)

      if os.system(command):
        self.log(Message.INFO, "browser_open", "browser profile files copied.")
      else:
        self.log(Message.FATAL, "browser_open", "browser profile files NOT copied.")

  def browser_cookies_load(self):
    # check cookie file exists or no
    if path.isfile(self.COOKIE):
      # read and load cookies from prev file
      cookies = pickle.load(open(self.COOKIE, "rb"))
      for cookie in cookies:
          self.driver.add_cookie(cookie)

  def browser_cookies_save(self):
    if self.driver != None:
      pickle.dump(self.driver.get_cookies() , open(self.COOKIE, "wb"))
    else:
      self.log(Message.INFO, "browser_cookie_save", "driver is none and we cannot get cookies!")

  def create_database(self, name):
    query = 'CREATE DATABASE `{0}`'.format(name)

  def db_exec(self, query, params = ()):
    if self.cursor != None:
      self.cursor.execute(query, params)
    else:
      self.execute(query, params)

  def db_cursor(self):
    if self.cursor != None:
      self.cursor = self.db.cursor()
    else:
      self.log(Message.INFO, "db_cursor", "cannot reopen a cursor on database connection two times!")

  def db_commit(self):
    self.cursor.close()
    self.db.commit()
    self.cursor = None

  def check_table(self, table):
    self.db_cursor()

    table = table.replace('\'', '\'\'')

    # query = 'SHOW TABLES LIKE `{0}`'.format(table)
    query = '''
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = '{0}'
        '''.format(table)

    self.db_exec(query)

    if self.cursor.fetchone()[0] == 1:
      return True
    return False

  def create_tables(self):
    if not check_table('post'):
      query = '''
        CREATE TABLE IF NOT EXISTS `post` (
          `id` bigint(50) NOT NULL,
          `title` text NOT NULL,
          `channel` varchar(52) NOT NULL,
          `vote` varchar(10) NOT NULL,
          `link` text NOT NULL,
          `datetime` timestamp NOT NULL DEFAULT current_timestamp()
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ALTER TABLE `post`
          ADD PRIMARY KEY (`id`);
        ALTER TABLE `post`
          MODIFY `id` bigint(50) NOT NULL AUTO_INCREMENT;
        COMMIT;
      '''
      self.db_exec(query)
      self.log(Message.INFO, "create_tables", "post table created")
    else:
      self.log(Message.INFO, "create_tables", "post table already exists")

  def empty_tables(self):
    for table in tables:
      empty_table(table)

  def empty_table(self, table):
    query = 'TRUNCATE `{0}`'.format(table)

  def drop_tables(self):
    for table in tables:
      drop_table(table)

  def drop_table(self, table):
    query = 'DROP TABLE `{0}`'.format(table)

  def log(self, typ, route, message):
    if self.mode == ProgramMode.DEBUG:
      print(typ, route, message)

  def start(self):
    # startup browser
    if self.browser == Browser.FIREFOX:
      self.driver = webdriver.Firefox(firefox_profile=self.profile, options=self.options)

      # get profile temp path
      self.profile_temp = self.driver.firefox_profile.path # Seems this not good for our purpose in Windows OS! (This directory only contains a `user.js` file with user_prefs)

      self.driver.get("about:support")
      box = self.driver.find_element_by_id("profile-dir-box")
      self.profile_temp_path = box.text
      self.log(Message.INFO, "start", "temp profile path is " + self.profile_temp_path)


    elif self.browser == Browser.CHROME:
      # TODO
      self.driver = webdriver.Chrome(options=self.options)

    # wait for browser to load and init
    self.driver.implicitly_wait(30)

  def login(self):
    '''
    Why we not use `os.getenv("KEY")` and we used `os.environ.get("KEY")`?
      because environ raises error exception if KEY not exists
    '''

    # read param from .env
    '''
    Why we use `ACCOUNT` for username and we did not use `USERNAME`?
      because USERNAME will rewrite on Windows OS and we will get windows-running-username and not from own .env file
    '''
    username = os.getenv("ACCOUNT")
    password = os.getenv("PASSWORD")

    # log
    self.log(Message.INFO, "login", "username is " + username)
    self.log(Message.INFO, "login", "password is " + password)

    # call loginManualy method
    return self.loginManualy(username, password)

  def home(self):
    try:
      # Your session has expired. Please refresh the page and try again.
      url = self.base_url
      self.browser_open(url)

      self.browser_cookies_load()

      self.driver.implicitly_wait(5)

      # find_element_by_id
      # find_elements_by_css_selector
      # find_element_by_xpath
      if self.driver.find_elements_by_css_selector("#post-composer-du-media"): # du = German refer to my IP or a fix word?
        self.log(Message.INFO, "home", "Seems we already logined to reddit :)")
      else:
        self.log(Message.INFO, "home", "compose post box not exists, so go to login...")
        return self.login()

      time.sleep(5)
      # Not works as well yet!
      accept_cookie = self.driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[3]/div[2]/form/div/button')
      print(accept_cookie)
      accept_cookie.click()

      # Read posts or more jobs...
      # TODO
      # self.db_cursor()
      # query = "INSERT INTO post (title) VALUES (%s)"
      # values = ("test")
      # self.db_exec(query, values)
      # self.db_commit()
      # print(self.cursor.rowcount)

    except NoSuchElementException:
      self.log(Message.FATAL, "home", "Error!")

  def loginManualy(self, username, password):
    # load cookies from cache files
    # Cannot call this function everywhere, we should use this function when we open same domain.
    # Why? selenium.common.exceptions.InvalidCookieDomainException: Message: Document is cookie-averse
    self.browser_cookies_load()

    try:
      # Your session has expired. Please refresh the page and try again.
      url = self.base_url + r"login/?dest=https%3A%2F%2Fwww.reddit.com%2F"
      self.browser_open(url)
      time.sleep(15)

      username_in = self.driver.find_element_by_class_name("AnimatedForm__textInput")
      username_in.send_keys(username, Keys.ENTER)

      pass_in = self.driver.find_element_by_xpath("//*[@id='loginPassword']")
      pass_in.send_keys(password, Keys.ENTER)

      time.sleep(20)


    except NoSuchElementException:
      self.log(Message.FATAL, "loginManualy", "Error: maybe you already loginned!")

