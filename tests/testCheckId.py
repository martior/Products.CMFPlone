#
# Test id autogeneration related scripts
#

from Products.CMFPlone.tests import PloneTestCase
from Products.CMFPlone.tests import dummy

from AccessControl import Unauthorized
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError


class TestIsIDAutoGenerated(PloneTestCase.PloneContentLessTestCase):
    '''Tests the isIDAutoGenerated script'''

    def testAutoGeneratedId(self):
        plone_utils = getToolByName(self.portal, 'plone_utils')
        r = plone_utils.isIDAutoGenerated('document.2004-11-09.0123456789')
        self.assertEqual(r, True)

    def testAutoGeneratedIdWithUnderScores(self):
        plone_utils = getToolByName(self.portal, 'plone_utils')
        portal_types = getToolByName(self.portal, 'portal_types')
        portal_types.test_type=self.portal.portal_types.Event
        portal_types.test_type.id="test_type"

        r = plone_utils.isIDAutoGenerated('test_type.2004-11-09.0123456789')

        del portal_types.test_type

        self.assertEqual(r, True)

    def testEmptyId(self):
        plone_utils = getToolByName(self.portal, 'plone_utils')
        r = plone_utils.isIDAutoGenerated('')
        self.assertEqual(r, False)

    def testValidPortalTypeNameButNotAutoGeneratedId(self):
        plone_utils = getToolByName(self.portal, 'plone_utils')
        # This was raising an IndexError exception for
        # Zope < 2.7.3 (DateTime.py < 1.85.12.11) and a
        # SyntaxError for Zope >= 2.7.3 (DateTime.py >= 1.85.12.11)
        r = plone_utils.isIDAutoGenerated('document.tar.gz')
        self.assertEqual(r, False)
        # check DateError
        r = plone_utils.isIDAutoGenerated('document.tar.12/32/2004')
        self.assertEqual(r, False)
        # check TimeError
        r = plone_utils.isIDAutoGenerated('document.tar.12/31/2004 12:62')
        self.assertEqual(r, False)


class TestCheckId(PloneTestCase.PloneTestCase):
    '''Tests the check_id script'''

    def testGoodId(self):
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testEmptyId(self):
        r = self.folder.check_id('')
        self.assertEqual(r, None)   # success

    def testRequiredId(self):
        r = self.folder.check_id('', required=1)
        self.assertEqual(r, u'Please enter a name.')

    def testAlternativeId(self):
        r = self.folder.check_id('', alternative_id='foo')
        self.assertEqual(r, None)   # success

    def testBadId(self):
        r = self.folder.check_id('=')
        #self.assertEqual(r, "'=' is not a legal name.")
        self.assertEqual(r, u'${name} is not a legal name. The following characters are invalid: ${characters}')
        self.assertEqual(r.mapping[u'name'], '=')
        self.assertEqual(r.mapping[u'characters'], '=')

    def testCatalogIndex(self):
        # TODO: Tripwire
        portal_membership = getToolByName(self.portal, 'portal_membership')
        have_permission = portal_membership.checkPermission
        self.failUnless(have_permission('Search ZCatalog', self.portal.portal_catalog),
                        'Expected permission "Search ZCatalog"')

        r = self.folder.check_id('created')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'created')

    def testCatalogMetadata(self):
        portal_catalog = getToolByName(self.portal, 'portal_catalog')
        portal_catalog.addColumn('new_metadata')
        self.failUnless('new_metadata' in portal_catalog.schema())
        self.failIf('new_metadata' in portal_catalog.indexes())
        r = self.folder.check_id('new_metadata')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'new_metadata')

    def testCollision(self):
        self.folder.invokeFactory('Document', id='foo')
        self.folder.invokeFactory('Document', id='bar')
        r = self.folder.foo.check_id('bar')
        self.assertEqual(r, u'There is already an item named ${name} in this folder.')
        self.assertEqual(r.mapping[u'name'], 'bar')

    def testTempObjectCollision(self):
        foo = self.folder.restrictedTraverse('portal_factory/Document/foo')
        self.folder._setObject('bar', dummy.Item('bar'))
        r = foo.check_id('bar')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'bar')

    def testReservedId(self):
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('portal_catalog')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'portal_catalog')

    def testHiddenObjectId(self):
        # If a parallel object is not in content-space, should get 'reserved'
        # instead of 'taken'
        r = self.folder.check_id('portal_skins')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'portal_skins')

    def testCanOverrideParentNames(self):
        self.folder.invokeFactory('Document', id='item1')
        self.folder.invokeFactory('Folder', id='folder1')
        self.folder.invokeFactory('Document', id='foo')
        r = self.folder.folder1.foo.check_id('item1')
        self.assertEqual(r, None)

    def testInvalidId(self):
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('_foo')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], '_foo')

    def testContainerHook(self):
        # Container may have a checkValidId method; make sure it is called
        self.folder._setObject('checkValidId', dummy.Raiser(dummy.Error))
        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('whatever')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'whatever')

    def testContainerHookRaisesUnauthorized(self):
        # check_id should not swallow Unauthorized errors raised by hook
        self.folder._setObject('checkValidId', dummy.Raiser(Unauthorized))
        self.folder._setObject('foo', dummy.Item('foo'))
        self.assertRaises(Unauthorized, self.folder.foo.check_id, 'whatever')

    def testContainerHookRaisesConflictError(self):
        # check_id should not swallow ConflictErrors raised by hook
        self.folder._setObject('checkValidId', dummy.Raiser(ConflictError))
        self.folder._setObject('foo', dummy.Item('foo'))
        self.assertRaises(ConflictError, self.folder.foo.check_id, 'whatever')

    def testMissingUtils(self):
        # check_id should not bomb out if the plone_utils tool is missing
        self.portal._delObject('plone_utils')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testMissingCatalog(self):
        # check_id should not bomb out if the portal_catalog tool is missing
        self.portal._delObject('portal_catalog')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testMissingFactory(self):
        # check_id should not bomb out if the portal_factory tool is missing
        self.portal._delObject('portal_factory')
        r = self.folder.check_id('foo')
        self.assertEqual(r, None)   # success

    def testCatalogIndexSkipped(self):
        # Note that the check is skipped when we don't have
        # the "Search ZCatalogs" permission.
        self.portal.manage_permission('Search ZCatalog', ['Manager'], acquire=0)

        r = self.folder.check_id('created')
        # But now the final hasattr check picks this up
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'created')

    def testCollisionSkipped(self):
        # Note that check is skipped when we don't have
        # the "Access contents information" permission.
        self.folder.manage_permission('Access contents information', [], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        self.folder._setObject('bar', dummy.Item('bar'))
        r = self.folder.foo.check_id('bar')
        self.assertEqual(r, None)   # success

    def testReservedIdSkipped(self):
        # This check is picked up by the checkIdAvailable, unless we don't have
        # the "Add portal content" permission, in which case it is picked up by
        # the final hasattr check.
        self.folder.manage_permission('Add portal content', [], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('portal_catalog')
        self.assertEqual(r, u'${name} is reserved.')
        self.assertEqual(r.mapping[u'name'], 'portal_catalog')

    def testInvalidIdSkipped(self):
        # Note that the check is skipped when we don't have
        # the "Add portal content" permission.
        self.folder.manage_permission('Add portal content', [], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        r = self.folder.foo.check_id('_foo')
        self.assertEqual(r, None)   # success


    def testParentMethodAliasDisallowed(self):
        # Note that the check is skipped when we don't have
        # the "Add portal content" permission.
        self.folder.manage_permission('Add portal content', ['Manager'], acquire=0)

        self.folder._setObject('foo', dummy.Item('foo'))
        for alias in self.folder.getTypeInfo().getMethodAliases().keys():
            r = self.folder.foo.check_id(alias)
            self.assertEqual(r, u'${name} is reserved.')
            self.assertEqual(r.mapping[u'name'], alias)

    def testCheckingMethodAliasesOnPortalRoot(self):
        # Test for bug http://dev.plone.org/plone/ticket/4351
        self.setRoles(['Manager'])
        self.portal.manage_permission('Add portal content', ['Manager'], acquire=0)

        # Should not raise: Before we were using obj.getTypeInfo(), which is
        # not defined on the portal root.
        try:
            self.portal.check_id('foo')
        except AttributeError, e:
            self.fail(e)


class TestVisibleIdsEnabled(PloneTestCase.PloneContentLessTestCase):
    '''Tests the visibleIdsEnabled script'''

    def afterSetUp(self):
        portal_membership = getToolByName(self.portal, 'portal_membership')
        portal_properties = getToolByName(self.portal, 'portal_properties')
        self.member = portal_membership.getAuthenticatedMember()
        self.props = portal_properties.site_properties

    def testFailsWithSitePropertyDisabled(self):
        # Set baseline
        self.member.setProperties(visible_ids=False)
        self.props.manage_changeProperties(visible_ids=False)
        # Should fail when site property is set false
        self.failIf(self.portal.visibleIdsEnabled())
        self.member.setProperties(visible_ids=True)
        self.failIf(self.portal.visibleIdsEnabled())

    def testFailsWithMemberPropertyDisabled(self):
        # Should fail when member property is false
        self.member.setProperties(visible_ids=False)
        self.props.manage_changeProperties(visible_ids=True)
        self.failIf(self.portal.visibleIdsEnabled())

    def testSucceedsWithMemberAndSitePropertyEnabled(self):
        # Should succeed only when site property and member property are true
        self.props.manage_changeProperties(visible_ids=True)
        self.member.setProperties(visible_ids=True)
        self.failUnless(self.portal.visibleIdsEnabled())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCheckId))
    suite.addTest(makeSuite(TestIsIDAutoGenerated))
    suite.addTest(makeSuite(TestVisibleIdsEnabled))
    return suite
