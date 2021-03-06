#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import json
from threading import Thread

import Log as log
from Process import Process

class Plugin(Process):
    """Plugin - common interface to run plugins"""
    def __init__(self, **kwargs):
        log.debug("Initializing plugin %s" % self.__class__.__name__)

        config = kwargs.get('config', {})

        self._init_done = False
        self._process_stdout_thread = None
        self._plugin_dir = config.get('path', None)

        if self._plugin_dir:
            self._plugin_dir = os.path.expanduser(self._plugin_dir)
        else:
            plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
            self._plugin_dir = os.path.join(plugins_dir, self.__class__.__name__.lower(), config.get('type'))

        plugin_runfile = os.path.join(self._plugin_dir, 'run')

        if os.path.exists(plugin_runfile):
            self._command_cwd = self._plugin_dir
            self._command = [plugin_runfile]
            if 'args' in config.get('config', {}):
                self._command += config['config']['args']
        else:
            log.error("Unable to locate plugin executable '%s'" % plugin_runfile)

        # We need stdout to handle messages from plugin
        Process.__init__(self, config=config,
                logout=None, logerr=kwargs.get('logerr'), pidpath=kwargs.get('pidpath'))
        self._logout = kwargs.get('logout')

    def _processStdout(self):
        log.debug("%s: Stdout processing started" % self.__class__.__name__)
        while self._process.poll() is None:
            try:
                line = self._process.stdout.readline()
                message = self._parseMessage(line)
                if not self._processMessageCommonTypes(message):
                    self.processMessage(message)
            except Exception, e:
                log.error("Unable to process message due to error: %s" % str(e))
                log.info("Message: %s" % line.strip())
        log.debug("%s: Stdout processing done" % self.__class__.__name__)

    def _clientConnect(self):
        if not self._process_stdout_thread:
            self._process_stdout_thread = Thread(target=self._processStdout)
            self._process_stdout_thread.daemon = True
            self._process_stdout_thread.start()
        if not self._init_done:
            raise Exception("Init of plugin %s/%s still not done" % (self.__class__.__name__, self._cfg.get('type', '[unknown plugin type]')))

        self._client = True

    def _parseMessage(self, data):
        return json.loads(data)

    def _processMessageCommonTypes(self, msg):
        if msg['type'] == 'init-done':
            self._init_done = True
            log.log('INFO', msg['msg'], self._logout)
        elif msg['type'] in ['info', 'warn']:
            log.log(msg['type'], msg['msg'], self._logout)
        elif msg['type']  == 'error':
            log.log(msg['type'], msg['msg'], self._logerr)
        else:
            return False

        return True

    def processMessage(self, msg):
        log.warn("Messages processor not provided for object %s" % self.__class__.__name__)
        log.info("Message: %s" % msg)
        pass
