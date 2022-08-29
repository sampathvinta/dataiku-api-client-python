from ..utils import DataikuException
import json
from datetime import datetime
from .future import DSSFuture

class DSSWebAppListItem(object):
    """An item in a list of webapps. Do not instantiate this class, use :meth:`dataikuapi.dss.project.DSSProject.list_webapps`"""
    def __init__(self, client, project_key, data):
        self.client = client
        self.project_key = project_key
        self._data = data

    def to_webapps(self):
        """Gets the :class:`DSSCodeStudioObject` corresponding to this code studio object """
        return DSSWebApp(self.client, self.project_key, self._data["id"])

    @property
    def name(self):
        return self._data["name"]
    @property
    def id(self):
        return self._data["id"]
    @property
    def owner(self):
        return self._data["createdBy"]["displayName"]
    @property
    def status(self):
        return self._data["backendRunning"]


class DSSWebApp(object):
    """
    A handle to manage webapp object in Dataiku
    """
    def __init__(self, client, project_key, webapp_id):
        """Do not call directly, use :meth:`dataikuapi.dss.project.DSSProject.get_webapp`"""
        self.client = client
        self.project_key = project_key
        self.webapp_id = webapp_id

    def stop(self):
        """
        Stop a running webapp

        :returns: a future to wait on the stop, or None if already stopped
        :rtype: :class:`dataikuapi.dss.future.DSSFuture`
        """
        ret = self.client._perform_json("PUT", "/projects/%s/webapps/%s/backend/actions/stop" % (self.project_key, self.webapp_id))
        return DSSFuture.from_resp(self.client, ret)

    def restart(self):
        """
        Restart a running webapp

        :returns: a future to wait on the stop, or None if already stopped
        :rtype: :class:`dataikuapi.dss.future.DSSFuture`
        """
        ret = self.client._perform_json("PUT", "/projects/%s/webapps/%s/backend/actions/restart" % (self.project_key, self.webapp_id))
        return DSSFuture.from_resp(self.client, ret)

    def get_status(self):
        """
        Get the status of a webapp

        :returns: a handle to inspect the webapp state
        :rtype: :class:`dataikuapi.dss.webapp.DSSWebAppObjectStatus`
        """
        status = self.client._perform_json("GET", "/projects/%s/webapps/%s/backend/state" % (self.project_key, self.webapp_id))
        return DSSWebAppStatus(self.client, self.project_key, self.code_studio_id, status)

class DSSWebAppStatus(object):
    """
    Status of a webapp object
    """
    def __init__(self, client, project_key, webapp_id, status):
        """Do not call directly, use :meth:`dataikuapi.dss.codestudio.DSSWebAppObject.get_state`"""
        self.client = client
        self.project_key = project_key
        self.webapp_id = webapp_id
        self.status = status

    def get_raw(self):
        """
        Gets the status as a raw dictionary. This returns a reference to the raw status, not a copy,
        """
        return self.status

    @property
    def state(self):
        return self.status["futureInfo"]["alive"]
