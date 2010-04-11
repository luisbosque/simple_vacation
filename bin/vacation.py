#!/usr/bin/python

import sys
import os
from   email          import Utils
from   email.MIMEText import MIMEText
from   email          import Parser
import ldap
import smtplib
from   datetime       import datetime
import ConfigParser

vacation_conf = "/usr/local/simple_vacation/config/vacation.cfg"

config = ConfigParser.RawConfigParser()
config.read(vacation_conf)

vacation_home = config.get("Global", "vacation_home")
vacation_log_path = config.get("Global", "vacation_log_path")
ldap_host = config.get("Global", "ldap_host")
ldap_port = config.getint("Global", "ldap_port")
ldap_base = config.get("Global", "ldap_base")
default_vacation_message = config.get("Global", "default_vacation_message")

def pair_exists(local_addr, remote_addr):
  if os.path.isfile('%s%s' % (vacation_log_path, local_addr)):
    log = open('%s%s' % (vacation_log_path, local_addr), 'r')
    for line in log:
      if line.rstrip() == remote_addr:
        return True
    return False
  else:
    return False

def add_pair(local_addr, remote_addr):
  log = open('%s%s' % (vacation_log_path, local_addr), 'a')
  log.write(remote_addr)
  log.write("\n")
  log.close()


raw_email = sys.stdin.read()
p = Parser.Parser()
msg = p.parsestr(raw_email)

from_addr = Utils.parseaddr(msg.__getitem__('From'))
to_addr = Utils.parseaddr(msg.__getitem__('To'))
subject = msg.__getitem__('Subject')

l = ldap.initialize('ldap://%s:%d' % (ldap_host, ldap_port))

vacation_search = l.search_s(ldap_base, ldap.SCOPE_SUBTREE, "(mail=%s)" % to_addr[1], ['vacationActive', 'vacationInfo'])

if not vacation_search:
  sys.exit()

if vacation_search[0][1]['vacationActive'][0] == 'TRUE':
  if pair_exists(to_addr[1], from_addr[1]):
    sys.exit()
  
  if vacation_search[0][1].has_key('vacationInfo'):
    body = vacation_search[0][1]['vacationInfo'][0]
  else:
    body = default_vacation_message
  
  subject = "RE: " + subject
  
  response_email = MIMEText(body)
  response_email['Subject'] = subject
  response_email['From'] = to_addr[1]
  response_email['To'] = from_addr[1]
  
  s = smtplib.SMTP('localhost')
  s.sendmail(to_addr[1], from_addr[1], response_email.as_string())
  s.quit
  
  add_pair(to_addr[1], from_addr[1])

