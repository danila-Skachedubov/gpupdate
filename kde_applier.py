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

    def __init__(self, storage, sid=None, username=None):
        self.storage = storage
        self.username = username
        self.sid = sid
        kde_filter = '{}%'.format(self.__hkcu_branch)
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
        for setting in self.kde_settings:
            valuename = setting.valuename.split('.')
            self.file = valuename[0]
            self.value = valuename[1]
            self.data = string_to_literal_eval(setting.data)
            self.type = setting.type
            if self.file == 'plasma':
                self.edit_config_widget(self.data, self.value)
            else:
                self.edit_config(self.file, self.data)

    def edit_config(self, file, data):
        '''
        Method for editing INI configuration files responsible for KDE settings
        '''
        config_file_path = os.path.expanduser(f'{get_homedir(self.username)}/.config/{file}')
        with open(config_file_path, 'a') as config_file:
            for section, values in data.items():
                config_file.write(f"[{section}]\n")
                for key, value in values.items():
                    config_line = f"{key}={value}\n"
                    config_file.write(config_line)

    def edit_config_widget(self, data, value):
        '''
        Method for changing graphics settings in plasma context
        '''
        '''
        Dictionary with key and binary value in a file for executing a command
        '''
        widget_utilities = {
            'colorscheme': 'plasma-apply-colorscheme',
            'cursortheme': 'plasma-apply-cursortheme',
            'desktoptheme': 'plasma-apply-desktoptheme',
            'wallpaperimage': 'plasma-apply-wallpaperimage'
        }
        try:
            if value in widget_utilities:
                # TODO: Выявить и добавить,по надобности, нужные переменные окружения для выполнения plasma-apply-desktoptheme и plasma-apply-cursortheme
                os.environ["XDG_DATA_DIRS"] = f"{get_homedir(self.username)}.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share:/usr/share/kf5:/usr/share:/var/lib/snapd/desktop"#Variable for system detection of directories before files with .colors extension
                os.environ["DISPLAY"] = ":0"#Variable for command execution plasma-apply-colorscheme
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"#plasma-apply-wallpaperimage
                command_path = os.path.join("/usr/lib/kf5/bin", widget_utilities[value])
                if os.path.exists(command_path):
                    command = [f"{command_path}", f"{data}"]
                    print(command)
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                    if proc.returncode == 0:
                        output = stdout.decode("utf-8").strip()
                    else:
                        error = stderr.decode("utf-8").strip()
                else:
                    pass
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


