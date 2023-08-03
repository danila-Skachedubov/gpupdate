#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2023 BaseALT Ltd.
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

from .applier_frontend import applier_frontend, check_enabled
from util.logging import log
from util.util import get_homedir, string_to_literal_eval

import os
import subprocess

class kde_applier_user(applier_frontend):
    __module_name = 'KdeApplierUser'
    __module_experimental = False
    __module_enabled = True
    __hkcu_branch = 'Software\\BaseALT\\Policies\\KDE\\'
    __lock_branch = 'Software\\BaseALT\\Policies\\KDELocks\\'
    widget_utilities = {
            'colorscheme': 'plasma-apply-colorscheme',
            'cursortheme': 'plasma-apply-cursortheme',
            'desktoptheme': 'plasma-apply-desktoptheme',
            'wallpaperimage': 'plasma-apply-wallpaperimage'
        }


    def __init__(self, storage, sid=None, username=None):
        self.storage = storage
        self.username = username
        self.sid = sid
        self.locks_dict = {}
        kde_filter = '{}%'.format(self.__hkcu_branch)
        locks_filter = '{}%'.format(self.__lock_branch) 
        self.locks_settings = self.storage.filter_hkcu_entries(self.sid, locks_filter)
        self.kde_settings = self.storage.filter_hkcu_entries(self.sid, kde_filter)
        self.__module_enabled = check_enabled(
            self.storage,
            self.__module_name,
            self.__module_experimental
        )

    def parse_key(self):
        '''
        Method used to parse hive_key
        '''
        for locks in self.locks_settings:
            self.locks_dict[locks.valuename] = locks.data
        for setting in self.kde_settings:
            self.valuenameForDict = setting.valuename
            valuename = setting.valuename.split('.')
            self.file = valuename[0]
            self.value = valuename[1]
            self.data = string_to_literal_eval(setting.data)
            self.type = setting.type
            if self.file == 'plasma':
                self.edit_config_widget(self.data, self.value, self.valuenameForDict)
            else:
                self.edit_config(self.file, self.data, self.valuenameForDict)
           
            

    def edit_config(self, file, data, valuenameForDict):
        '''
        Method for editing INI configuration files responsible for KDE settings
        '''
        config_file_path = os.path.expanduser(f'{get_homedir(self.username)}/.config/{file}')
        with open(config_file_path, 'a') as config_file:
            for section, values in data.items():
                config_file.write(f"[{section}]\n")
            if valuenameForDict in self.locks_dict:
                if self.locks_dict[valuenameForDict] == '1':                  
                    for key, value in values.items():
                        config_line = f"{key}[$i]={value}\n"
                        config_file.write(config_line)
                elif self.locks_dict[valuenameForDict] == '0':
                    for key, value in values.items():
                        config_line = f"{key}={value}\n"
                        config_file.write(config_line)
            else:
                for key, value in values.items():
                        config_line = f"{key}={value}\n"
                        config_file.write(config_line)

    def edit_config_widget(self, data, value, valuenameForDict):
        '''
        Method for changing graphics settings in plasma context
        '''
        try:
            if value in self.widget_utilities:
                # TODO: Выявить и добавить,по надобности, нужные переменные окружения для выполнения plasma-apply-desktoptheme и plasma-apply-cursortheme
                os.environ["XDG_DATA_DIRS"] = f"{get_homedir(self.username)}.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share:/usr/share/kf5:/usr/share:/var/lib/snapd/desktop"#Variable for system detection of directories before files with .colors extension
                os.environ["DISPLAY"] = ":0"#Variable for command execution plasma-apply-colorscheme
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"#plasma-apply-wallpaperimage
                os.environ["PATH"] = f"{get_homedir(self.username)}/bin:/usr/local/bin:/usr/lib/kf5/bin:/usr/bin:/bin:/usr/games:/var/lib/snapd/snap/bin"#environment variable for accessing binary files without hard links
                command = [f"{self.widget_utilities[value]}", f"{data}"]
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                if proc.returncode == 0:
                    output = stdout.decode("utf-8").strip()
                else:
                    error = stderr.decode("utf-8").strip()
            else:
                pass
        except OSError as e:
            pass

    def run(self):
        pass

    def admin_context_apply(self):
        '''
        Change settings applied in admin context
        '''
    
    def user_context_apply(self):
        '''
        Change settings applied in user context
        '''
        # TODO: Добавить в файл /massages/__init__.py логи, в файл /local/gpoa.po перевод логов
        if self.__module_enabled:
            #log('')
            pass
            self.parse_key()
        else:
            pass
            #log('')


