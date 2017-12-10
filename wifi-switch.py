import subprocess
import os
import logging
from wifi import Cell
import json


client_mode_tasks = [
    ['sudo', 'service', 'dhcpcd', 'restart'],
    ['sudo', 'service', 'dnsmasq', 'stop'],
    ['sudo', 'service', 'hostapd', 'stop'],
    ['sudo', 'service', 'networking', 'restart'],
]

AP_mode_tasks = [
    ['sudo', 'service', 'dhcpcd', 'restart'],
    ['sudo', 'service', 'networking', 'restart'],
    ['sudo', 'service', 'dnsmasq', 'start'],
    ['sudo', 'service', 'hostapd', 'start'],
    ['sudo', 'service', 'networking', 'restart'],
]


setup_script_tasks = [
    ['sudo', 'apt-get', 'install', 'dnsmasq', 'hostapd'],
    ['systemctl', 'disable', 'hostapd.service'],
    ['systemctl', 'disable', 'dnsmasq.service']
]

def change_wifi_mode(mode, ssid='', passwd='', wep=0):
    """
    Switch the mode of the wifi adapter between client(0) and AP(1)
    :param mode: The mode of the wifi. 0 for client mode, 1 for AP/hotspot mode.
    :param ssid: SSID to connect to wifi in client mode.
            If no SSID is provided in client mode, it retrieves saved wifi credentials
    :param passwd: Password of the wifi that might be req in client mode.
            If no passwd is provided, it assumes an open network.
    :param wep: If the wifi ap is protected by wep instead of the usual wpa, set it to 1
    :return:None
    """
    logging.debug('Got switch request mode-{0} ssid-{1} pass-{2} wep-{3} '.format(mode, ssid, passwd, wep))
    if mode == 0:
        dhcpcd_conf = '''# A sample configuration for dhcpcd.
# See dhcpcd.conf(5) for details.

# Allow users of this group to interact with dhcpcd via the control socket.
#controlgroup wheel

# Inform the DHCP server of our hostname for DDNS.
hostname

# Use the hardware address of the interface for the Client ID.
clientid
# or
# Use the same DUID + IAID as set in DHCPv6 for DHCPv4 ClientID as per RFC4361.
#duid

# Persist interface configuration when dhcpcd exits.
persistent

# Rapid commit support.
# Safe to enable by default because it requires the equivalent option set
# on the server to actually work.
option rapid_commit

# A list of options to request from the DHCP server.
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
# Most distributions have NTP support.
option ntp_servers
# Respect the network MTU.
# Some interface drivers reset when changing the MTU so disabled by default.
#option interface_mtu

# A ServerID is required by RFC2131.
require dhcp_server_identifier

# Generate Stable Private IPv6 Addresses instead of hardware based ones
slaac private

# A hook script is provided to lookup the hostname if not set by the DHCP
# server, but it should not be run by default.
nohook lookup-hostname'''

        with open('/etc/dhcpcd.conf', 'w') as fp:
            fp.write(dhcpcd_conf)

        if ssid:
            # Update the saved wifi credentials
            with open('Hotspot/SavedWifiCredentials.json', 'r') as fp:
                saved_cred = json.load(fp)

            saved_cred[ssid] = {'passwd': passwd, 'wep': wep}

            with open('Hotspot/SavedWifiCredentials.json', 'w') as fp:
                json.dump(saved_cred, fp)

            if passwd:
                if wep:
                    interfaces_conf = """# interfaces(5) file used by ifup(8) and ifdown(8)

# Please note that this file is written to be used with dhcpcd
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf'

# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d
auto lo

iface lo inet loopback
iface eth0 inet dhcp

auto wlan0
allow-hotplug wlan0
iface wlan0 inet dhcp
      wireless-essid {0}
      wireless-key {1}

""".format(ssid, passwd)
                # If wep not marked, treat as wpa
                else:
                    interfaces_conf = """# interfaces(5) file used by ifup(8) and ifdown(8)

# Please note that this file is written to be used with dhcpcd
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf'

# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d
auto lo

iface lo inet loopback
iface eth0 inet dhcp

auto wlan0
allow-hotplug wlan0
iface wlan0 inet dhcp
      wpa-ssid "{0}"
      wpa-psk "{1}"
      wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf
""".format(ssid, passwd)

                with open('/etc/network/interfaces', 'w') as fp:
                    fp.write(interfaces_conf)
                logging.debug('Switching to client mode')
                for task in client_mode_tasks:
                    try:
                        logging.debug(' '.join(task[1:]) + ' - Exit Status : ' + str(subprocess.check_call(task)))

                    except Exception as e:
                        logging.error(str(e))

                return None

            # If no passwd given, treat as open network
            else:
                interfaces_conf = """# interfaces(5) file used by ifup(8) and ifdown(8)
# Please note that this file is written to be used with dhcpcd
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf'

# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d
auto lo

iface lo inet loopback
iface eth0 inet dhcp

auto wlan0
allow-hotplug wlan0
iface wlan0 inet dhcp
    wireless-essid {0}
    wireless-mode managed""".format(ssid)

                with open('/etc/network/interfaces', 'w') as fp:
                    fp.write(interfaces_conf)

                logging.debug('Switching to client mode')
                for task in client_mode_tasks:
                    try:
                        logging.debug(' '.join(task[1:]) + ' - Exit Status : ' + str(subprocess.check_call(task)))

                    except Exception as e:
                        logging.error(str(e))

                return None

        # If no ssid given, automatically choose a saved one
        else:
            logging.debug('Switching to client mode')
            if not client_mode():
                # Switch to client mode to start a wifi scan
                for task in client_mode_tasks:
                    try:
                        logging.debug(' '.join(task[1:]) + ' - Exit Status : ' + str(subprocess.check_call(task)))

                    except Exception as e:
                        logging.error(str(e))
                sleep(1)

            # scan until there is a wifi AP found
            logging.debug('Wifi Scan Started \n')
            retries = 0
            scan = None
            while retries < 20:
                # Search for AP's and store inside a file
                try:
                    scan = Cell.all(wifi_interface)

                except Exception as e:
                    logging.error(str(e))

                if scan:
                    break

                retries += 1
                sleep(1)

            if scan:
                # Sort in desc order acc to the quality and iterate over list to see if a cell is in saved wifi cred
                scan = sorted(scan, key=lambda cell: cell.quality, reverse=True)

                logging.debug('Wifi Scan Completed - ' + str(scan))

                try:
                    with open('Hotspot/SavedWifiCredentials.json', 'r') as fp:
                        wifi_credentials = json.load(fp)

                except FileNotFoundError as e:
                    logging.error('No saved wifi credentails were found')
                    return None

                ssid = None
                for cell in scan:
                    if cell.ssid in wifi_credentials.keys():
                        ssid = cell.ssid
                        break

                # ssid = sorted(scan, key=lambda cell: cell.quality)[-1].ssid
                if ssid:
                    change_wifi_mode(0, ssid, wifi_credentials[ssid]['passwd'], wifi_credentials[ssid]['wep'])

                else:
                    logging.debug('Couldn\'t match any scan with saved wifi credentials')

                return None

            else:
                logging.debug('Wifi Scan unsuccessful')

    elif mode == 1:
        dhcpcd_conf = '''# A sample configuration for dhcpcd.
# See dhcpcd.conf(5) for details.

# Allow users of this group to interact with dhcpcd via the control socket.
#controlgroup wheel

# Inform the DHCP server of our hostname for DDNS.
hostname

# Use the hardware address of the interface for the Client ID.
clientid
# or
# Use the same DUID + IAID as set in DHCPv6 for DHCPv4 ClientID as per RFC4361.
#duid

# Persist interface configuration when dhcpcd exits.
persistent

# Rapid commit support.
# Safe to enable by default because it requires the equivalent option set
# on the server to actually work.
option rapid_commit

# A list of options to request from the DHCP server.
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
# Most distributions have NTP support.
option ntp_servers
# Respect the network MTU.
# Some interface drivers reset when changing the MTU so disabled by default.
#option interface_mtu
foo
# A ServerID is required by RFC2131.
require dhcp_server_identifier

# Generate Stable Private IPv6 Addresses instead of hardware based ones
slaac private

# A hook script is provided to lookup the hostname if not set by the DHCP
# server, but it should not be run by default.
nohook lookup-hostname

denyinterfaces wlan0'''

        with open('/etc/dhcpcd.conf', 'w') as fp:
            fp.write(dhcpcd_conf)

        interfaces_conf = """# interfaces(5) file used by ifup(8) and ifdown(8)

# Please note that this file is written to be used with dhcpcd
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf'

# Include files from /etc/network/interfaces.d:
source-directory /etc/network/interfaces.d

auto lo

iface lo inet loopback
iface eth0 inet dhcp

allow-hotplug wlan0
iface wlan0 inet static
        address 10.0.0.1
        netmask 255.255.255.0
        network 10.0.0.0
"""
        with open('/etc/network/interfaces', 'w') as fp:
            fp.write(interfaces_conf)

        logging.debug('Switching to AP mode')

        for task in AP_mode_tasks:
            try:
                logging.debug(' '.join(task[1:]) + ' - Exit Status : ' + str(subprocess.check_call(task)))

            except Exception as e:
                logging.error(str(e))

        return None


def hostapd_active():
    return os.path.isfile('/var/run/hostapd.pid')
