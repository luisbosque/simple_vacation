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
import syslog


syslog.openlog('vacation', syslog.LOG_PID)


vacation_conf = "/usr/local/simple_vacation/config/vacation.cfg"

def log(level, message):
  if (level == syslog.LOG_ERR) or (verbose == True):
    syslog.syslog(level|syslog.LOG_MAIL, message)


config = ConfigParser.RawConfigParser()
try:
  config.read(vacation_conf)
except ConfigParser.MissingSectionHeaderError:
  log(syslog.LOG_ERR, "Section Global is missing in configuration file")
  sys.exit(1)


def read_config(parameter):
  try:
    return config.get("Global", parameter)
  except ConfigParser.NoSectionError:
    print "Section Global is missing in configuration file\n"
    sys.exit(1)
  except ConfigParser.NoOptionError:
    if parameter == "verbose":
      return False
    elif parameter == "vacation_log_path":
      return vacation_home + "/log/"
    elif parameter == "ldap_host":
      return "localhost"
    elif parameter == "ldap_port":
      return 389
    else:
      log(syslog.LOG_ERR, "Parameter %s is missing" % parameter)
      sys.exit(1)

config_parameters = ["verbose", "vacation_home", "vacation_log_path", "ldap_host", "ldap_port", "ldap_base", "default_vacation_message"]
for parameter in config_parameters:
  vars()[parameter] = read_config(parameter)


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

l = ldap.initialize('ldap://%s:%d' % (ldap_host, int(ldap_port)))

try:
  vacation_search = l.search_s(ldap_base, ldap.SCOPE_SUBTREE, "(mail=%s)" % to_addr[1], ['vacationActive', 'vacationInfo'])
except ldap.NO_SUCH_OBJECT:
  log(syslog.LOG_ERR, "The user with email: %s was not found in the LDAP tree" % to_addr[1])
  sys.exit(1)
except ldap.SERVER_DOWN:
  log(syslog.LOG_ERR, "Can't connect to ldap server on %s address and %s port" % (ldap_host, ldap_port.__str__()))
  sys.exit(1)

if not vacation_search[0][1].has_key('vacationActive'):
  log(syslog.LOG_INFO, "The user %s has not the LDAP attribute vacationActive set" % to_addr[1])
  sys.exit()

if vacation_search[0][1]['vacationActive'][0] == 'TRUE':
  if pair_exists(to_addr[1], from_addr[1]):
    log(syslog.LOG_INFO, "Pair already exists. Don't send auto-respond")
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

  try:
    s.sendmail(to_addr[1], from_addr[1], response_email.as_string())
  except:
    log(syslog.LOG_ERR, "It wasn't possible to send the email. See the mail system log for more information")

  s.quit
  
  log(syslog.LOG_INFO, "Auto-respond sent to %s" % from_addr[1])
  
  add_pair(to_addr[1], from_addr[1])


syslog.closelog()
