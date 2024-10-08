#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

from .util import (
      get_backends
    , get_default_policy_name
)

class GPConfig:

    __config_path = '/etc/dconf/db/local.d/gpupdate.ini'
    __dconf_db_path = "/etc/dconf/db/local"
    __dconf_locald_path = "/etc/dconf/db/local.d/"
    __gpupdate_entry = "/Software/BaseALT/Configuration/gpupdate/"
    __gpoa_entry = 'Software/BaseALT/Configuration/gpupdate/gpoa'
    __dc_entry = 'Software/BaseALT/Configuration/gpupdate/samba'

    def __init__(self, config_path=None):
        from storage.dconf_registry import Dconf_registry, create_dconf_ini_file
        self.writer= create_dconf_ini_file
        self.registry = Dconf_registry()
        if config_path:
            self.__config_path = config_path

        self.dict_backend = self.registry.get_dictionary_from_dconf(self.__gpupdate_entry)

    def get_backend(self):
        '''
        Fetch the name of the backend from configuration file.
        '''
        if self.__gpoa_entry in self.dict_backend:
            if 'backend' in self.dict_backend[self.__gpoa_entry]:
                if self.dict_backend[self.__gpoa_entry]['backend'] in get_backends():
                    return self.dict_backend[self.__gpoa_entry]['backend']

        return 'samba'

    def set_backend(self, backend_name='local'):
        self.dict_backend[self.__gpoa_entry]['backend'] = backend_name
        self.write_config(self.dict_backend)

    # This function is not expected corresponding "set_dc()" function
    # because we have no way to automatically determine such kind
    # of setting.
    def get_dc(self):
        '''
        Fetch Domain Controller from configuration file.
        '''
        if self.__dc_entry in self.dict_backend:
            if 'dc' in self.dict_backend[self.__dc_entry]:
                return self.dict_backend[self.__dc_entry]['dc']

    def get_local_policy_template(self):
        '''
        Fetch the name of chosen Local Policy template from
        configuration file.

        '''
        if self.__gpoa_entry in self.dict_backend:
            if 'local-policy' in self.dict_backend[self.__gpoa_entry]:
                return self.dict_backend[self.__gpoa_entry]['local-policy']

        return get_default_policy_name()

    def set_local_policy_template(self, template_name='default'):
        self.dict_backend[self.__gpoa_entry]['local-policy'] = template_name
        self.write_config(self.dict_backend)

    def write_config(self, data):
        self.writer(self.__config_path, data)
        self.registry.dconf_update(custom_db_file=self.__dconf_db_path, custom_path=self.__dconf_locald_path)
