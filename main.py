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
