# py-learn-spam

Simple script to gather ham/spam mails from IMAP folder, pipe them through
rspamc and move them to a 'done' imap folder if successful.

## Configuration

There is a sample INI file with some basic comments to refer to. This should
be adapted to your configuration and put under /etc/py-learn-spam.ini.
As this file will contain credentials for your IMAP server, make sure to
minimize read access to the user account actually running this thing.

## Logging

Logging is done using python3 basic logging system.

## Systemd

There are sample files for a systemd-unit as well as a systemd-timer. If you
don't wand to use systemd-timer, feel free to use your favorite cron
mechanismn.

## Python

This tool needs Python3 and was tested on Python 3.8. You will need:

- logging
- subprocess
- re
- configparser
- imaplib
- time

All of these should come with your standard Python 3 environment.
