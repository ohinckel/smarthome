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


class PluginController(RESTResource):

    def __init__(self, sh, jwt_secret=False):
        self._sh = sh
        self.base_dir = self._sh.get_basedir()
        self.plugins_dir = os.path.join(self.base_dir, 'plugins')
        self.logger = logging.getLogger(__name__)
        self.logger.info("PluginController(): __init__")
        self.plugins = Plugins.get_instance()

        self.plugin_data = {}
        self.jwt_secret = jwt_secret
        return


    def get_body(self):
        """
        Get content body of received request header

        :return:
        """
        cl = cherrypy.request.headers.get('Content-Length', 0)
        if cl == 0:
            # cherrypy.reponse.headers["Status"] = "400"
            # return 'Bad request'
            raise cherrypy.HTTPError(status=411)
        rawbody = cherrypy.request.body.read(int(cl))
        self.logger.debug("PluginController(): ___(): rawbody = {}".format(rawbody))
        try:
            params = json.loads(rawbody.decode('utf-8'))
        except Exception as e:
            self.logger.warning("PluginController(): ___(): Exception {}".format(e))
            return None
        return params


    def test_for_old_config(self, config_filename):
        # make it 'readonly', if plugin.conf is used
        result = not(os.path.splitext(config_filename)[1].lower() == '.yaml')

        _etc_dir = os.path.dirname(config_filename)
        if not result:
            # for beta-testing: create a backup of ../etc/plugin.yaml
            if not os.path.isfile(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')):
                shutil.copy2(config_filename, os.path.join(_etc_dir, 'plugin_before_admin_config.yaml'))
                self.logger.warning('Created a backup copy of plugin.yaml ({})'.format(os.path.join(_etc_dir, 'plugin_before_admin_config.yaml')))

        return result


    def get_config_filename(self):

        if self.plugins is None:
            self.plugins = Plugins.get_instance()

        return self.plugins._get_plugin_conf_filename()



    @cherrypy.expose
    def index(self, plugin=None):
        """
        return an object with type info about all installed plugins
        """
        self.logger.info("PluginController(): index('{}')".format(plugin))

        config_filename = self.get_config_filename()

        info = {}
        info['_readonly'] = self.test_for_old_config(config_filename)

        # get path to plugin configuration file, without extension
        _conf = lib.config.parse_basename(os.path.splitext(config_filename)[0], configtype='plugin')

        plg_found = False
        for confplg in _conf:
            if (confplg == plugin) or (plugin == None):
                self.logger.info("PluginController(): index('{}') - confplg {}".format(plugin, confplg))
                info['config'] = _conf[confplg]
                plg_found = True

        if plg_found:
            return json.dumps(info)
        raise cherrypy.NotFound

    index.expose_resource = True


    @cherrypy.expose
    def add(self, plgsection=None):
        self.logger.info("PluginController(): add('{}')".format(plgsection))

        params = self.get_body()
        if params is None:
            self.logger.warning("PluginController(): add(): section '{}': Bad, add request".format(plgsection))
            raise cherrypy.HTTPError(status=411)
        self.logger.info("PluginController(): add(): section '{}' = {}".format(plgsection, params))

        config_filename = self.get_config_filename()

        if self.test_for_old_config(config_filename):
            # make it 'readonly', if plugin.conf is used
            response = {'result': 'error', 'description': 'Updateing .CONF files is not supported'}
        else:
            response = {}
            plugin_conf = shyaml.yaml_load_roundtrip(config_filename)
            sect = plugin_conf.get(plgsection)
            if sect is not None:
                response = {'result': 'error', 'description': "Configuration section '{}' already exists".format(plgsection)}
            else:
                plugin_conf[plgsection] = params.get('config', {})
                shyaml.yaml_save_roundtrip(config_filename, plugin_conf, False)
                response = {'result': 'ok'}

        self.logger.info("PluginController(): add(): response = {}".format(response))
        return json.dumps(response)

    add.expose_resource = True
    add.authentication_needed = True


    @cherrypy.expose
    def update(self, plgsection=None):
        self.logger.info("PluginController(): update('{}')".format(plgsection))

        params = self.get_body()
        if params is None:
            self.logger.warning("PluginController(): update(): section '{}': Bad, add request".format(plgsection))
            raise cherrypy.HTTPError(status=411)
        self.logger.info("PluginController(): update(): section '{}' = {}".format(plgsection, params))

        config_filename = self.get_config_filename()

        if self.test_for_old_config(config_filename):
            # make it 'readonly', if plugin.conf is used
            response = {'result': 'error', 'description': 'Updateing .CONF files is not supported'}
        else:
            response = {}
            plugin_conf = shyaml.yaml_load_roundtrip(config_filename)
            sect = plugin_conf.get(plgsection)
            if sect is None:
                response = {'result': 'error', 'description': "Configuration section '{}' does not exist".format(plgsection)}
            else:
                plugin_conf[plgsection] = params.get('config', {})
                shyaml.yaml_save_roundtrip(config_filename, plugin_conf, False)
                response = {'result': 'ok'}

        self.logger.info("PluginController(): update(): response = {}".format(response))
        return json.dumps(response)

    update.expose_resource = True
    update.authentication_needed = True


    def REST_instantiate(self, id=None):
        """ instantiate a REST resource based on the id

        this method MUST be overridden in your class. it will be passed
        the id (from the url fragment) and should return a model object
        corresponding to the resource.

        if the object doesn't exist, it should return None rather than throwing
        an error. if this method returns None and it is a PUT request,
        REST_create() will be called so you can actually create the resource.
        """
        # self.logger.info("PluginController(): REST_instantiate(id): id = {}".format(id))
        if id is not None:
            return id
        return None
#        raise cherrypy.NotFound

