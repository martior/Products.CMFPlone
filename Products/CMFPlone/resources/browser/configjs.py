from Products.Five.browser import BrowserView
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import IResourceRegistry
from zope.component import getMultiAdapter
from zope.component import getUtility

import re


configjs = """requirejs.config({
    baseUrl: '%s',
    paths: %s,
    shim: %s,
    optimize: 'uglify',
    wrapShim: true
});

"""


class RequireJsView(BrowserView):
    """
    This view creates the config.js for requirejs with all the registered
    resources

    It's used on development for the config.js and on compilation for the
    optimize.js
    """

    @property
    def registry(self):
        return getUtility(IRegistry)

    def registryResources(self):
        return self.registry.collectionOfInterface(
            IResourceRegistry, prefix="plone.resources")

    def base_url(self):
        portal_state = getMultiAdapter((self.context, self.request),
                                       name=u'plone_portal_state')
        site_url = portal_state.portal_url()
        return site_url

    def get_requirejs_config(self):
        """
        Returns the information for requirejs configuration
        """
        registry = self.registryResources()
        paths = {}
        shims = {}
        for requirejs, script in registry.items():
            if script.js:
                # Main resource js file
                src = re.sub(r"\.js$", "", script.js)
                paths[requirejs] = src
                exports = script.export
                deps = script.deps
                inits = script.init
                if exports != '' or deps != '' or inits != '':
                    shims[requirejs] = {}
                    if exports != '' and exports is not None:
                        shims[requirejs]['exports'] = exports
                    if deps != '' and deps is not None:
                        shims[requirejs]['deps'] = deps.split(',')
                    if inits != '' and inits is not None:
                        shims[requirejs]['init'] = inits
            if script.url:
                # Resources available under name-url name
                src = script.url
                paths[requirejs + '-url'] = src
        return (self.base_url(), paths, shims)

    def get_requirejs_config_str(self):
        base, paths, shims = self.get_requirejs_config()
        shims_str = str(shims).replace('\'deps\'', 'deps').replace(
            '\'exports\'', 'exports').replace(
            '\'init\': \'', 'init: ').replace('}\'}', '}}')
        return (self.base_url(), str(paths), shims_str)


class ConfigJsView(RequireJsView):
    """ config.js for requirejs for script rendering. """

    def __call__(self):
        (baseUrl, paths, shims) = self.get_requirejs_config_str()
        self.request.response.setHeader("Content-Type",
                                        "application/javascript")
        return configjs % (baseUrl, paths, shims)
