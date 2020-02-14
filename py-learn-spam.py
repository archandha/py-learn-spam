#!/usr/bin/env python3

"""
Python 3 script to read imap folders and pipe mails into rspamd

- depending on imap folder they should be learned as ham or spam
- after rspamd training, they should me moved to an appropriate "done" folder

This software is licensed under the GNU Public License GPLv3. See LICENSE
file.
"""

import logging
import subprocess
import re
import configparser
from imaplib import IMAP4
import time


CONFIGFILE = '/etc/py-learn-spam.ini'

rspamd_success_string = "^success = true;$|^error.*has been already learned as.*$|^error = \"<.*> is skipped for bayes classifier: already in class (h|sp)am.*\";$"

rspamd_success_pattern = re.compile(rspamd_success_string)


def query_folder(host, wait, user, passwd, learn, done, task, command, rhost ):
    """
    queries all mails in folder named learn, passes this to rspamd
    and moves mail info done folder

    host: ip address or name of imapt host
    wait: time in seconds to wait between two messages
    user, passwd: imap credentials
    learn: imap folder to read from
    done: imap folder to move to after learn success
    task: one of ['ham'|'spam']
    command: executable to run for learning spam
    """

    con = IMAP4(host)
    con.starttls()

    try:
        con.enable("UTF8=ACCEPT")
    except IMAP4.error as e:
        logging.warning(e)


    con.login(user, passwd)

    # get number of messages to be learned
    try:
        typ, data = con.select(learn, readonly= False)
        num_msgs = int(data[0])
        logging.info("%d Messages in '%s'",  num_msgs, learn)
    except IMAP4.error as e:
        logging.warning(e)
        return

    # get message ids as list
    try:
        typ, message_ids = con.search(None, 'ALL')
    except IMAP4.error as e:
        logging.warning(e)

    # iterate over all messages in mailbox
    for num in message_ids[0].split():
        message = b""                  # empty raw message

        typ, mesg_head = con.fetch(num, '(BODY.PEEK[HEADER])')
        for response_part in mesg_head:
            if isinstance(response_part, tuple):
                message += response_part[1]     # add header lines

        typ, mesg_body = con.fetch(num, '(BODY.PEEK[TEXT])')
        for response_part in mesg_body:
            if isinstance(response_part, tuple):
                message += response_part[1]     # add body lines

        try:
            # decode raw bytes to utf-8 string
            mesg_text = "".join(message.decode('utf-8'))
        except UnicodeDecodeError as e:
            logging.error(e)


        # pipe assembled message through rspam cli
        with subprocess.Popen([
                command,
                '--connect',
                rhost,
                'learn_%s' % task,
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as rspamc:
            rspamc.stdin.write(bytearray(mesg_text, "utf-8"))
            rspamc.stdin.close()
            result = rspamc.stdout.read().decode("utf-8")
            rspamc.stdout.close()

        result_lines = result.split("\n")

        # test if learning succesfull or "already learned". If either one,
        # move to "done" imap folder
        if re.match(rspamd_success_pattern, result_lines[1]):
            logging.debug(result)
            result = con.copy(num, done)
            logging.info("copied mail %d to %s" % (int(num), done))

            if result[0] == 'OK':
                mov, data = con.store(num, '+FLAGS', '(\Deleted)')
                logging.debug("removed learned mail vom %s" % learn)
                con.expunge()
                logging.debug("expunged learned mail vom %s" % learn)

        else:
            logging.warning("mail not moved: %s", result)

        time.sleep(wait)

    con.logout()
    return



def main():
    """main run für learning ham/spam from IMAP"""

    # open and read config file
    config = configparser.ConfigParser()
    config.read(CONFIGFILE)

    # configure basic logging
    loglevel = int(config['logging'].get('level', 30))
    logfile = config['logging'].get('file', '/var/log/py-learn-spam.log')

    logging.basicConfig(
        filename=logfile, level=loglevel,
        format='%(asctime)s %(levelname)s - %(message)s')

    try:
        spamfolder = config['imap']['SPAMFOLDER']
        spamdonefolder = config['imap']['SPAMDONEFOLDER']
        hamfolder = config['imap']['HAMFOLDER']
        hamdonefolder = config['imap']['HAMDONEFOLDER']
        host = config['imap']['host']
        user = config['imap']['user']
        passwd = config['imap']['password']
        command = config['spam']['rspamc']
    except KeyError as e:
        logging.error(e)
        return

    rhost = config['spam'].get('host', '127.0.0.1')
    rport = config['spam'].get('port', '127.0.0.1')
    rhostport = "%s:%s" % (rhost, rport)

    wait = int(config['imap'].get('wait', 5))


    logging.info("starting with spam run")
    query_folder(
        host, wait, user, passwd, spamfolder,
        spamdonefolder, "spam", command, rhostport)
    logging.info("starting with ham run")
    query_folder(
        host, wait, user, passwd, hamfolder,
        hamdonefolder, "ham", command, rhostport)



if __name__ == '__main__':
    main()
