#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime
from datetime import datetime
import time
import re
import selenium.webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from var_dump import var_dump

CONF = {
    "url": "http://www.trocdestrains.com/recherche-billet-train.html",
}

MONTH = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

def valid_date(s):
    try:
      date = datetime.strptime(s, "%d-%m-%Y")
      if date < datetime.today():
        msg = "Incorrect date %s" % args.date.strftime("%d/%m/%y")
        raise argparse.ArgumentTypeError(msg)
      return date
    except ValueError:
      msg = "Not a valid date: '{0}'. Format: dd-mm-yyyy".format(s)
      raise argparse.ArgumentTypeError(msg)

def valid_hour(s):
    hour = int(s)
    if hour >= 0 and hour <= 24:
      return hour
    else:
      msg = "Not a valid hour: '%s'." % s
      raise argparse.ArgumentTypeError(msg)


argparser = argparse.ArgumentParser()
argparser.add_argument('-d', '--departure', help='Departure city', required=True)
argparser.add_argument('-a', '--arrival', help='Destination city', required=True)
argparser.add_argument('-t', '--date', required=True, help='Date of departure. Format: dd-mm-yyyy', type=valid_date)
argparser.add_argument('-h1', '--min', help='minimim hour of departure.', type=valid_hour)
argparser.add_argument('-h2', '--max', help='maximum hour of departure.', type=valid_hour)

args = argparser.parse_args()

if args.min is None:
  args.min = 0;
if args.max is None:
  args.max = 24;


print "Recherche billet: %s => %s on %d %s entre %dh et %dh" %(args.departure, args.arrival, args.date.day, MONTH[args.date.month], args.min, args.max)

#init webdriver
options = selenium.webdriver.chrome.options.Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")

driver = selenium.webdriver.Chrome(executable_path="/usr/bin/chromedriver", chrome_options=options)

#enter travel infos
driver.get(CONF['url'])
depart_elt = driver.find_element_by_id('ville_dep')
depart_elt.clear()
depart_elt.send_keys(args.departure)
arrival_elt = driver.find_element_by_id('ville_arr')
arrival_elt.clear()
arrival_elt.send_keys(args.arrival)
#day
select = Select(driver.find_element_by_name('L_jour_dep'))
select.select_by_visible_text(str(args.date.day).zfill(2))
#month
select = Select(driver.find_element_by_name('L_mois_annee_dep'))
month_str = "%s %s" % (MONTH[args.date.month] , args.date.year)
select.select_by_visible_text(month_str)
#hour
select = Select(driver.find_element_by_name('L_h_deb_r'))
select.select_by_visible_text('%sh' % str(args.min).zfill(2))
select = Select(driver.find_element_by_name('L_h_fin_r'))
select.select_by_visible_text('%sh' % str(args.max).zfill(2))

#search it !
driver.find_element_by_name('choix_rech_billet').click()
time.sleep(1)

#wait for results
msg_xpath = "//div[@id='msg_rech_billets']//span"
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, msg_xpath))
  )

msg = driver.find_element_by_xpath(msg_xpath).text
print msg
match = re.match(r"^([0-9]+) billets? trouv", msg)
if match is not None:
  nb_tickets = int(match.group(1))
  if nb_tickets > 0:
    tickets = driver.find_elements_by_xpath("//div[@class='liste-billets']//div[1]//span[@class='billet arrondi-10']")

    #loop on tickets
    tickets_infos = []
    for billet_idx, ticket in enumerate(tickets, start=1):
      if billet_idx > nb_tickets:
        break
      print "Billet %d" % billet_idx

      #stations, time
      steps = []
      stations = ticket.find_elements_by_xpath(".//span[@class='col-gares']//span")
      for idx, station in enumerate(stations, start=1):
        if station.text != ' ':
          time = ticket.find_element_by_xpath(".//span[@class='col-heures']//span[%d]" % idx)
          station_info = {'station': station.text, 'time': time.text}
          steps.append(station_info)

      #price
      price_text = ticket.find_element_by_xpath(".//span[@class='col-date']//span[@class='prix']").text

      match = re.match(r"^([0-9]+\.?[0-9]+) . par place$", price_text)
      price = float(match.group(1))
      #var_dump(price)
      ticket_infos = {'steps': steps, 'price': price}
      pretty_msg = ' '
      #var_dump(ticket_infos)
      for idx, steps in enumerate(ticket_infos['steps'], start=1):
        pretty_msg += " %s: %s" % (steps['time'], steps['station'])
        if idx < len(ticket_infos['steps']):
          pretty_msg += " =>"
      print pretty_msg + " %0.2fEUR" % price
      tickets_infos.append(ticket_infos)
