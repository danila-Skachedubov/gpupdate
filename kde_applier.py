import os
import dbus
from enum import Enum

from .applier_frontend import applier_frontend, check_enabled
from util.logging import slogm, log
from util.users import is_root
from util.util import  get_homedir, string_to_literal_eval

import logging

class kde_applier_user(applier_frontend):
    __module_name_user = 'KdeApplierUser'
    __module_experimental = False
    __module_enabled = True
    __hkcu_branch = 'Software\\BaseALT\\Policies\\KDE\\'

    def __init__(self, storage, sid=None, username=None):
        print('start2')
        self.storage = storage
        self.username = username
        self.sid = sid
        
        kde_filter = '{}%'.format(self.__hkcu_branch)
        self.kde_settings = self.storage.filter_hkcu_entries(self.sid, kde_filter)
        # self.__module_enabled = check_enabled(
        #       self.storage
        #     , self.__module_name
        #     , self.__module_experimental
        # )

        self.parse_key()

    def parse_key(self):
        print('start3')
        for setting in self.kde_settings:
            valuename = setting.valuename.split('.')
            self.file = valuename[0]
            self.data = setting.data
            self.type = setting.type
            # TODO: добавить проверку на Lock
            if setting.type == 4 and setting.data == '0':  # заглушка для ключей блокировки
                pass
            #elif self.section == 'wallpaper':
            #   self.apply_for_user_wallpaper(self.file, self.section, self.value, self.type)
            else:
                self.apply_for_user(self.file, self.type, self.data)

    def apply_for_user(self, file, type, data):
        if is_root():
            print(data)
            config_file_path = os.path.expanduser(f'{get_homedir(self.username)}/.config/{file}')
            with open(config_file_path, 'a') as config_file:
                for section, values in data.items():
                     print(f"[{section}]\n")
                for key, value in values.items():
                    config_line = f"{key}={value}"
                    print(config_line)
                    print("\n")
                config_file.write()
                config_file.write()
        else:
            for applier_name, applier_object in self.user_appliers.items():
                try:
                    applier_object.user_context_apply()
                except Exception as exc:
                    logdata = dict({'applier_name': applier_name, 'message': str(exc)})
                    log('E11', logdata)

    def apply_for_user_wallpaper(self, file, section, value, type):
        bus = dbus.SessionBus()
        plasma_shell = bus.get_object('org.kde.plasmashell', '/PlasmaShell')
        remote_plasma = dbus.Interface(plasma_shell, dbus_interface='org.kde.PlasmaShell')
        image_path = f"Image=/usr/share/wallpapers/{self.data}/"

        script = """
            var allDesktops = desktops();
            for (i=0;i<allDesktops.length;i++) {{
                d = allDesktops[i];
                d.wallpaperPlugin = "org.kde.image";
                d.currentConfigGroup = Array("Wallpaper",
                                            "org.kde.image",
                                            "General");
                d.writeConfig("Image", "{0}")
            }}
        """.format(image_path)

        remote_plasma.evaluateScript(script)

    def run(self):
        pass

    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        pass
