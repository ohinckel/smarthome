#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2018-      Martin Sinn                         m.sinn@gmx.de
#########################################################################
#  This file is part of SmartHomeNG.
#
#  SmartHomeNG is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHomeNG is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHomeNG.  If not, see <http://www.gnu.org/licenses/>.
#########################################################################


import os
import shutil
import logging
import json
import cherrypy

import lib.shyaml as shyaml
import lib.config
from lib.module import Modules
from lib.plugin import Plugins
from lib.metadata import Metadata
from lib.model.smartplugin import SmartPlugin
from lib.constants import (KEY_CLASS_PATH, YAML_FILE)

from .rest import RESTResource


class PluginsController(RESTResource):

    def __init__(self, sh):
        self._sh = sh
        self.base_dir = self._sh.get_basedir()
        self.plugins_dir = os.path.join(self.base_dir, 'plugins')
        self.logger = logging.getLogger(__name__)

        self.plugin_data = {}
        return



    @cherrypy.expose
    def index(self, scheduler_name=False):
        """
        return an object with type info about all installed plugins
        """
        self.logger.info("PluginsController(): index")

        default_language = self._sh.get_defaultlanguage()

        if self.plugin_data == {}:
            plugins_list = sorted(os.listdir(self.plugins_dir))

            self.logger.info("- plugins_list_sorted = {}".format(plugins_list))
            for p in plugins_list:
                if not (p[0] in ['.', '_']):
                    if os.path.isfile(os.path.join(self.plugins_dir, p, 'plugin.yaml')):
                        plg_yaml = shyaml.yaml_load(os.path.join(os.path.join(self.plugins_dir, p, 'plugin.yaml')))
                        plg_data = plg_yaml.get('plugin', None)
                        if plg_data is None:
                            self.logger.info("- plugin.yaml has no section 'plugin': {}".format(p))
                        else:
                            self.plugin_data[p] = plg_data.get('type', '')
                    else:
                        self.logger.info("- no plugin.yaml: {}".format(p))

        return json.dumps(self.plugin_data)




class PluginsInstalledController(RESTResource):

    def __init__(self, sh):
        self._sh = sh
        self.base_dir = self._sh.get_basedir()
        self.plugins_dir = os.path.join(self.base_dir, 'plugins')
        self.logger = logging.getLogger(__name__)

        self.plugin_data = {}
        return



    @cherrypy.expose
    def index(self, scheduler_name=False):
        """
        return an object with data about all installed plugins
        """
        self.logger.info("PluginsInstalledController(): index")

        default_language = self._sh.get_defaultlanguage()

        if self.plugin_data == {}:
            plugins_list = sorted(os.listdir(self.plugins_dir))

            self.logger.info("- plugins_list_sorted = {}".format(plugins_list))
            for p in plugins_list:
                if not (p[0] in ['.', '_']):
                    if os.path.isfile(os.path.join(self.plugins_dir, p, 'plugin.yaml')):
                        plg_yaml = shyaml.yaml_load(os.path.join(os.path.join(self.plugins_dir, p, 'plugin.yaml')))
                        plg_data = plg_yaml.get('plugin', None)
                        if plg_data is None:
                            self.logger.info("- plugin.yaml has no section 'plugin': {}".format(p))
                        else:
                            self.plugin_data[p] = {}
                            self.plugin_data[p]['type'] = plg_data.get('type', '')
                            description = plg_data.get('description', {'de': '', 'en': ''})
                            self.plugin_data[p]['description'] = description[default_language]
                            self.plugin_data[p]['version'] = plg_data.get('version', '')
                            self.plugin_data[p]['documentation'] = plg_data.get('documentation', '')
                            self.plugin_data[p]['multi_instance'] = plg_data.get('multi_instance', '')
                    else:
                        self.logger.info("- no plugin.yaml: {}".format(p))

        return json.dumps(self.plugin_data)




class PluginsConfigController(RESTResource):

    def __init__(self, sh):
        self._sh = sh
        self.base_dir = self._sh.get_basedir()
        self.plugins_dir = os.path.join(self.base_dir, 'plugins')
        self.logger = logging.getLogger(__name__)

        self.plugins = Plugins.get_instance()

        self.plugin_data = {}
        return


    def _get_pluginname_and_metadata(self, plg_section, plg_conf):
        """
        Return the actual plugin name and the metadata instance

        :param plg_conf: loaded section of the plugin.yaml for the actual plugin
        :type plg_conf: dict

        :return: plugin_name and metadata_instance
        :rtype: string, object
        """
        plugin_name = plg_conf.get('plugin_name', '').lower()
        plugin_version = plg_conf.get('plugin_version', '').lower()
        if plugin_version != '':
            plugin_version = '._pv_' + plugin_version.replace('.', '_')
        if plugin_name != '':
            meta = Metadata(self._sh, (plugin_name + plugin_version).replace('.', os.sep), 'plugin')
        else:
            classpath = plg_conf.get(KEY_CLASS_PATH, '')
            if classpath != '':
                plugin_name = classpath.split('.')[len(classpath.split('.')) - 1].lower()
                if plugin_name.startswith('_pv'):
                    plugin_name = classpath.split('.')[len(classpath.split('.')) - 2].lower()
                self.logger.debug("Plugins __init__: pluginname = '{}', classpath '{}'".format(plugin_name, classpath))
                meta = Metadata(self._sh, plugin_name, 'plugin', (classpath + plugin_version).replace('.', os.sep))
            else:
                self.logger.error(
                    "Plugin configuration section '{}': Neither 'plugin_name' nor '{}' are defined.".format(plg_section,
                                                                                                            KEY_CLASS_PATH))
                meta = Metadata(self._sh, plugin_name, 'plugin', classpath)
        return (plugin_name + plugin_version, meta)


    @cherrypy.expose
    def index(self, id=False):
        """
        return an object with data about all installed plugins
        """
        if self.plugins is None:
            self.plugins = Plugins.get_instance()

        config_filename = self.plugins._get_plugin_conf_filename()
        _etc_dir = os.path.dirname(config_filename)

        info = {}
        # make it 'readonly', if plugin.conf is used
        info['readonly'] = not(os.path.splitext(config_filename)[1].lower() == '.yaml')

        if not info['readonly']:
            # for beta-testing: create a backup of ../etc/plugin.yaml
            if not os.path.isfile(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')):
                shutil.copy2(config_filename, os.path.join(_etc_dir, 'plugin_before_admin_config.yaml'))
                self.logger.warning('Created a backup copy of plugin.yaml ({})'.format(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')))

        # get path to plugin configuration file, withou extension
        _conf = lib.config.parse_basename(os.path.splitext(config_filename)[0], configtype='plugin')


        for confplg in _conf:
            plg = _conf[confplg].get('plugin_name', '?')
            if plg == '?':
                plg = _conf[confplg].get('class_path', '?')
            plginstance = self.plugins.return_plugin(confplg)
            typ = '?'
            if plginstance != None:
                # self.logger.warning("confplg {}: type(plginstance) = {}".format(confplg, type(plginstance)))
                # self.logger.warning("confplg {}: type(plginstance.metadata) = {}".format(confplg, type(plginstance.metadata)))
                try:
                    typ = plginstance.metadata.get_string('type')
                    _conf[confplg]['_meta'] = plginstance.metadata.meta
                    _conf[confplg]['_description'] = plginstance.metadata.meta['plugin']['description']
                except:
                    self.logger.warning('confplg {}: Passed for plginstance = {}'.format(confplg, plginstance))
            else:
                # nicht geladene Plugins
                # self.logger.warning("confplg {}: type(plginstance) = None".format(confplg))
                plugin_name, metadata = self._get_pluginname_and_metadata(confplg, _conf[confplg])
                # self.logger.warning("plugin_name = {}, meta = {}".format(plugin_name, metadata.meta))

                typ = metadata.get_string('type')
                _conf[confplg]['_meta'] = metadata.meta
                try:
                    _conf[confplg]['_description'] = metadata.meta['plugin']['description']
                except:
                    _conf[confplg]['_description'] = {}
                    _conf[confplg]['_description']['de'] = ''
                    _conf[confplg]['_description']['en'] = ''


        info['plugin_config'] = _conf

        return json.dumps(info)



class PluginsInfoController(RESTResource):

    def __init__(self, sh, module, shng_url_root):
        self._sh = sh
        self.module = module
        self.shng_url_root = shng_url_root

        self.base_dir = self._sh.get_basedir()
        self.plugins_dir = os.path.join(self.base_dir, 'plugins')
        self.logger = logging.getLogger(__name__)

        self.plugins = Plugins.get_instance()

        self.plugin_data = {}
        return


    @cherrypy.expose
    def index(self, scheduler_name=False):
        """
        return a list of all configured plugin instances
        """
        self.logger.info("PluginsInfoController (index)")
        if self.plugins == None:
            self.plugins = Plugins.get_instance()

        # get data for display of page
        conf_plugins = {}
        _conf = lib.config.parse(self.plugins._get_plugin_conf_filename())

        for plugin in _conf:
            conf_plugins[plugin] = {}
            conf_plugins[plugin] = _conf[plugin]

        plugin_list = []
        for x in self.plugins.return_plugins():
            plugin = dict()
            plugin['metadata'] = {}

            plugin['stopped'] = False
            # Update(s) triggered by < strong > {{p.instance._itemlist | length}} < / strong > items
            plugin['triggers'] = str(x._itemlist)

            if isinstance(x, SmartPlugin):
                plugin['pluginname'] = x.get_shortname()
                plugin['configname'] = x.get_configname()
                plugin['version'] = x.get_version()
                plugin['smartplugin'] = True
                plugin['multiinstance'] = x.is_multi_instance_capable()
                plugin['instancename'] = x.get_instance_name()

                plugin['webif_url'] = ''
                if self.module.mod_http.get_webifs_for_plugin(x.get_shortname()) != []:
                    for webif in self.module.mod_http.get_webifs_for_plugin(x.get_shortname()):
                        if webif['Instance'] == plugin['instancename']:
                            plugin['webif_url'] = self.shng_url_root + webif['Mount']

                plugin['parameters'] = []
                if bool(x._parameters):
                    #                    for p in x._parameters:
                    for p in x._metadata.get_parameterlist():
                        p_dict = {}
                        p_dict['name'] = str(p)
                        p_dict['type'] = x._metadata.get_parameter_type_with_subtype(p)
                        p_dict['value'] = str(x._parameters[p])
                        p_dict['default'] = x._metadata.get_parameter_defaultvalue(p)
                        plugin['parameters'].append(p_dict)

                plugin['attributes'] = []
                for a in x._metadata.get_itemdefinitionlist():
                    a_dict = {}
                    a_dict['name'] = str(a)
                    a_dict['type'] = x._metadata.get_itemdefinition_type_with_subtype(a)
                    plugin['attributes'].append(a_dict)

                plugin['metadata']['classpath'] = x._classpath  # str
                plugin['metadata']['classname'] = x.get_classname()
            else:
                plugin['pluginname'] = x._shortname
                plugin['configname'] = x._configname
                plugin['version'] = ''
                plugin['smartplugin'] = False
                plugin['multiinstance'] = False
                plugin['instancename'] = ''
                plugin['webif_url'] = ''
                plugin['parameters'] = []
                plugin['attributes'] = []

                plugin['metadata']['classpath'] = str(x._classpath)  # str
                plugin['metadata']['classname'] = str(x._classname)  # str
                plugin['stopped'] = False

            plugin['metadata']['type'] = x._metadata.get_string('type')
            plugin['metadata']['description'] = x._metadata.get_mlstring('description')
            plugin['metadata']['description_long'] = x._metadata.get_mlstring('description_long')
            plugin['metadata']['keywords'] = x._metadata.get_string('keywords')
            plugin['metadata']['documentation'] = x._metadata.get_string('documentation')
            plugin['metadata']['support'] = x._metadata.get_string('support')
            plugin['metadata']['maintainer'] = x._metadata.get_string('maintainer')
            plugin['metadata']['tester'] = x._metadata.get_string('tester')

            try:
                plugin['stopped'] = not x.alive
                plugin['stoppable'] = True
            except:
                plugin['stopped'] = False
                plugin['stoppable'] = False
            if plugin['pluginname'] == 'backend':
                plugin['stoppable'] = False

            plugin_list.append(plugin)
        #        plugins_sorted = sorted(plugin_list, key=lambda k: k['classpath'])
        plugins_sorted = sorted(plugin_list, key=lambda k: k['pluginname'] + k['instancename'])

        return json.dumps(plugins_sorted)





        if self.plugins is None:
            self.plugins = Plugins.get_instance()

        config_filename = self.plugins._get_plugin_conf_filename()
        _etc_dir = os.path.dirname(config_filename)

        info = {}
        # make it 'readonly', if plugin.conf is used
        info['readonly'] = not(os.path.splitext(config_filename)[1].lower() == '.yaml')

        if not info['readonly']:
            # for beta-testing: create a backup of ../etc/plugin.yaml
            if not os.path.isfile(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')):
                shutil.copy2(config_filename, os.path.join(_etc_dir, 'plugin_before_admin_config.yaml'))
                self.logger.warning('Created a backup copy of plugin.yaml ({})'.format(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')))

        # get path to plugin configuration file, withou extension
        _conf = lib.config.parse_basename(os.path.splitext(config_filename)[0], configtype='plugin')


        for confplg in _conf:
            plg = _conf[confplg].get('plugin_name', '?')
            if plg == '?':
                plg = _conf[confplg].get('class_path', '?')
            plginstance = self.plugins.return_plugin(confplg)
            typ = '?'
            if plginstance != None:
                # self.logger.warning("confplg {}: type(plginstance) = {}".format(confplg, type(plginstance)))
                # self.logger.warning("confplg {}: type(plginstance.metadata) = {}".format(confplg, type(plginstance.metadata)))
                try:
                    typ = plginstance.metadata.get_string('type')
                    _conf[confplg]['_meta'] = plginstance.metadata.meta
                    _conf[confplg]['_description'] = plginstance.metadata.meta['plugin']['description']
                except:
                    self.logger.warning('confplg {}: Passed for plginstance = {}'.format(confplg, plginstance))
            else:
                # nicht geladene Plugins
                # self.logger.warning("confplg {}: type(plginstance) = None".format(confplg))
                plugin_name, metadata = self._get_pluginname_and_metadata(confplg, _conf[confplg])
                # self.logger.warning("plugin_name = {}, meta = {}".format(plugin_name, metadata.meta))

                typ = metadata.get_string('type')
                _conf[confplg]['_meta'] = metadata.meta
                try:
                    _conf[confplg]['_description'] = metadata.meta['plugin']['description']
                except:
                    _conf[confplg]['_description'] = {}
                    _conf[confplg]['_description']['de'] = ''
                    _conf[confplg]['_description']['en'] = ''


        info['plugin_config'] = _conf

        return json.dumps(info)

