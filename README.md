# homeassistant-config
My homeassistant-config

# usefull commands
sudo hassbian-config upgrade hassbian-script
sudo hassbian-config upgrade homeassistant

sudo systemctl restart home-assistant@homeassistant.service

tail -f /home/homeassistant/.homeassistant/home-assistant.log
journalctl -fu home-assistant@homeassistant.service

# venv
sudo su -s /bin/bash homeassistant
cd /home/homeassistant/.homeassistant
source /srv/homeassistant/bin/activate

