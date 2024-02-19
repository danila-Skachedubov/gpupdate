#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import subprocess
from samba import getopt as options
from samba import NTSTATUSError

try:
    from samba.gpclass import get_dc_hostname, check_refresh_gpo_list
except ImportError:
    from samba.gp.gpclass import get_dc_hostname, check_refresh_gpo_list

from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo

from .xdg import (
      xdg_get_desktop
)
from .util import get_homedir
from .logging import log
from .samba import smbopts
from gpoa.storage import registry_factory
from samba.samdb import SamDB
from samba.auth import system_session
import optparse
import ldb
import ipaddress
import netifaces


class smbcreds (smbopts):

    def __init__(self, dc_fqdn=None):
        smbopts.__init__(self, 'GPO Applier')
        self.credopts = options.CredentialsOptions(self.parser)
        self.creds = self.credopts.get_credentials(self.lp, fallback_machine=True)
        self.set_dc(dc_fqdn)
        self.dc_site = SiteDomainScanner(self.creds, self.selected_dc).select_servers()
        if self.dc_site is not None:
            self.selected_dc = self.dc_site

    def get_dc(self):
        return self.selected_dc

    def set_dc(self, dc_fqdn):
        '''
        Force selection of the specified DC
        '''
        self.selected_dc = None

        try:
            if dc_fqdn is not None:
                logdata = dict()
                logdata['user_dc'] = dc_fqdn
                log('D38', logdata)

                self.selected_dc = dc_fqdn
            else:
                self.selected_dc = get_dc_hostname(self.creds, self.lp)
        except Exception as exc:
            logdata = dict()
            logdata['msg'] = str(exc)
            log('E10', logdata)
            raise exc

    def get_domain(self):
        '''
        Get current Active Directory domain name
        '''
        dns_domainname = None
        try:
            # Get CLDAP record about domain
            # Look and python/samba/netcmd/domain.py for more examples
            res = netcmd_get_domain_infos_via_cldap(self.lp, None, self.selected_dc)
            dns_domainname = res.dns_domain
            logdata = dict({'domain': dns_domainname})
            log('D18', logdata)
        except Exception as exc:
            log('E15')
            raise exc

        return dns_domainname

    def get_gpos(self, username):
        '''
        Get GPO list for the specified username for the specified DC
        hostname
        '''
        gpos = list()

        try:
            log('D48')
            ads = samba.gpo.ADS_STRUCT(self.selected_dc, self.lp, self.creds)
            if ads.connect():
                log('D47')
                gpos = ads.get_gpo_list(username)
                logdata = dict({'username': username})
                log('I1', logdata)
                for gpo in gpos:
                    # These setters are taken from libgpo/pygpo.c
                    # print(gpo.ds_path) # LDAP entry
                    ldata = dict({'gpo_name': gpo.display_name, 'gpo_uuid': gpo.name, 'file_sys_path': gpo.file_sys_path})
                    log('I2', ldata)

        except Exception as exc:
            logdata = dict({'username': username, 'dc': self.selected_dc})
            log('E17', logdata)

        return gpos

    def update_gpos(self, username):
        gpos = self.get_gpos(username)

        list_selected_dc = set()
        list_selected_dc.add(self.selected_dc)

        while list_selected_dc:
            logdata = dict()
            logdata['username'] = username
            logdata['dc'] = self.selected_dc
            try:
                log('D49', logdata)
                check_refresh_gpo_list(self.selected_dc, self.lp, self.creds, gpos)
                log('D50', logdata)
                list_selected_dc.clear()
            except NTSTATUSError as smb_exc:
                logdata['smb_exc'] = str(smb_exc)
                if not check_scroll_enabled():
                    log('F1', logdata)
                    raise smb_exc
                self.selected_dc = get_dc_hostname(self.creds, self.lp)
                if self.selected_dc not in list_selected_dc:
                    logdata['action'] = 'Search another dc'
                    log('W11', logdata)
                    list_selected_dc.add(self.selected_dc)
                else:
                    log('F1', logdata)
                    raise smb_exc
            except Exception as exc:
                logdata['exc'] = str(exc)
                log('F1', logdata)
                raise exc
        return gpos


class SiteDomainScanner:
    def __init__(self, smbcreds, dc):
        self.smbcreds = smbcreds
        parser = optparse.OptionParser(None)
        sambaopts = options.SambaOptions(parser)
        lp = sambaopts.get_loadparm()
        self.samdb = SamDB(url='ldap://{}'.format(dc), session_info=system_session(), credentials=smbcreds, lp=lp)

    def get_ip_addresses(self):
        interface_list = netifaces.interfaces()
        addresses = []
        for iface in interface_list:
            address_entry = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in address_entry:
                addresses.extend(ipaddress.ip_address(ipv4_address_entry['addr']) for ipv4_address_entry in address_entry[netifaces.AF_INET])
            if netifaces.AF_INET6 in address_entry:
                addresses.extend(ipaddress.ip_address(ipv6_address_entry['addr']) for ipv6_address_entry in address_entry[netifaces.AF_INET6])
        return addresses

    def get_ad_subnets_sites(self):
        subnet_dn = ldb.Dn(self.samdb, "CN=Subnets,CN=Sites")
        config_dn = self.samdb.get_config_basedn()
        subnet_dn.add_base(config_dn)
        res = self.samdb.search(subnet_dn, ldb.SCOPE_ONELEVEL, expression='objectClass=subnet', attrs=['cn', 'siteObject'])
        subnets = {ipaddress.ip_network(msg['cn'][0].decode('utf8')): msg['siteObject'][0].decode('utf8') for msg in res}
        return subnets

    def get_ad_site_servers(self, site):
        servers_dn = ldb.Dn(self.samdb, "CN=Servers")
        site_dn = ldb.Dn(self.samdb, site)
        servers_dn.add_base(site_dn)
        res = self.samdb.search(servers_dn, ldb.SCOPE_ONELEVEL, expression='objectClass=server', attrs=['dNSHostName'])
        servers = [msg['dNSHostName'][0].decode('utf8') for msg in res]
        return servers[0] if servers else None

    def check_ip_in_subnets(self, ip_addresses, subnets_sites):
        return next((subnets_sites[subnet] for subnet in subnets_sites.keys()
                     if any(ip_address in subnet for ip_address in ip_addresses)), None)

    def select_servers(self):
        try:
            ip_addresses = self.get_ip_addresses()
            subnets_sites = self.get_ad_subnets_sites()

            our_site = self.check_ip_in_subnets(ip_addresses, subnets_sites)

            if our_site:
                servers = self.get_ad_site_servers(our_site)
                return servers
            else:
                return None
        except Exception as e:
            return None

def expand_windows_var(text, username=None):
    '''
    Scan the line for percent-encoded variables and expand them.
    '''
    variables = dict()
    variables['HOME'] = '/etc/skel'
    variables['HOMEPATH'] = '/etc/skel'
    variables['HOMEDRIVE'] = '/'
    variables['SystemRoot'] = '/'
    variables['StartMenuDir'] = '/usr/share/applications'
    variables['SystemDrive'] = '/'
    variables['DesktopDir'] = xdg_get_desktop(username, variables['HOME'])

    if username:
        variables['LogonUser'] = username
        variables['HOME'] = get_homedir(username)
        variables['HOMEPATH'] = get_homedir(username)

        variables['StartMenuDir'] = os.path.join(
            variables['HOME'], '.local', 'share', 'applications')

    result = text
    for var in variables.keys():
        result = result.replace('%{}%'.format(var),
                                 variables[var] if variables[var][-1] == '/'
                                 else variables[var] +'/').replace('//','/')

    return result


def transform_windows_path(text):
    '''
    Try to make Windows path look like UNIX.
    '''
    result = text

    if text.lower().endswith('.exe'):
        result = text.lower().replace('\\', '/').replace('.exe', '').rpartition('/')[2]

    return result

def check_scroll_enabled():
    storage = registry_factory('registry')
    enable_scroll = 'Software\\BaseALT\\Policies\\GPUpdate\\ScrollSysvolDC'
    if storage.get_hklm_entry(enable_scroll):
        data = storage.get_hklm_entry(enable_scroll).data
        return bool(int(data))
    else:
        return False
