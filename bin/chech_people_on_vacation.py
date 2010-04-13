#!/usr/bin/python

import sys
import os
import ldap
import ConfigParser

vacation_conf = "/usr/local/simple_vacation/config/vacation.cfg"

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
      return vacation_path + "/log/"
    elif parameter == "ldap_host":
      return "localhost"
    elif parameter == "ldap_port":
      return 389
    else:
      log(syslog.LOG_ERR, "Parameter %s is missing" % parameter)
      sys.exit(1)

config_parameters = ["verbose", "vacation_home", "vacation_log_path", "ldap_host", "ldap_port", "ldap_base"]
for parameter in config_parameters:
  vars()[parameter] = read_config(parameter)


def is_on_vacation(email):
  l = ldap.initialize('ldap://%s:%d' % (ldap_host, int(ldap_port)))
  
  try:
    vacation_search = l.search_s(ldap_base, ldap.SCOPE_SUBTREE, "(mail=%s)" % email, ['vacationActive'])
  except ldap.SERVER_DOWN:
    log(syslog.LOG_ERR, "Can't connect to ldap server on %s address and %s port" % (ldap_host, ldap_port.__str__()))
    sys.exit(1)
  except ldap.NO_SUCH_OBJECT:
    return False
  
  if (not vacation_search[0][1].has_key('vacationActive')) or (vacation_search[0][1]['vacationActive'][0] != 'TRUE') :
    return False


def logged_emails():
  entries = os.listdir(vacation_log_path)
  for entry in entries[:]:
    if not os.path.isfile(vacation_log_path + entry):
      entries.remove(entry)
  return entries



for email in logged_emails(): 
  if is_on_vacation(email) == False:
    os.remove(vacation_log_path + email)
