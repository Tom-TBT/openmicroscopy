#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
   Copyright 2009-2013 Glencoe Software, Inc. All rights reserved.
   Use is subject to license terms supplied in LICENSE.txt

   pytest fixtures used as defined in conftest.py:
   - gatewaywrapper
   - author_testimg

"""

import omero
import Ice
from omero.gateway import BlitzGateway
from omero.gateway.scripts import dbhelpers
import pytest


class TestConnectionMethods(object):

    def testMultiProcessSession(self, gatewaywrapper):
        # 120 amongst other things trying to getSession() twice for the same
        # session dies. Also in separate processes.
        # we mimic this by calling setGroupForSession, which calls
        # sessionservice.getSession, 2 times on cloned connections
        gatewaywrapper.loginAsAuthor()
        assert gatewaywrapper.gateway.getSession() is not None
        c2 = gatewaywrapper.gateway.clone()
        assert c2.connect(sUuid=gatewaywrapper.gateway._sessionUuid)
        assert c2.getSession() is not None
        a = c2.getAdminService()
        g = omero.gateway.ExperimenterGroupWrapper(
            c2, a.containedGroups(c2.getUserId())[-1])
        c2.setGroupForSession(g)
        c3 = gatewaywrapper.gateway.clone()
        assert c3.connect(sUuid=gatewaywrapper.gateway._sessionUuid)
        assert c3.getSession() is not None
        a = c3.getAdminService()
        g = omero.gateway.ExperimenterGroupWrapper(
            c3, a.containedGroups(c3.getUserId())[1])
        c3.setGroupForSession(g)

    # seppuku is deprecated: testClose below supersedes this test
    @pytest.mark.filterwarnings("ignore:.*U.*close.*:DeprecationWarning")
    def testSeppuku(self, gatewaywrapper, author_testimg):
        # author_testimg in args to make sure the image has been imported
        gatewaywrapper.loginAsAuthor()
        assert gatewaywrapper.getTestImage() is not None
        gatewaywrapper.gateway.seppuku()
        pytest.raises(Ice.ConnectionLostException, gatewaywrapper.getTestImage)
        gatewaywrapper._has_connected = False
        gatewaywrapper.doDisconnect()
        gatewaywrapper.loginAsAuthor()
        assert gatewaywrapper.getTestImage() is not None
        gatewaywrapper.gateway.seppuku(softclose=False)
        pytest.raises(Ice.ConnectionLostException, gatewaywrapper.getTestImage)
        gatewaywrapper._has_connected = False
        gatewaywrapper.doDisconnect()
        # Also make sure softclose does the right thing
        gatewaywrapper.loginAsAuthor()
        g2 = gatewaywrapper.gateway.clone()

        def g2_getTestImage():
            return dbhelpers.getImage(g2, 'testimg1')
        assert g2.connect(gatewaywrapper.gateway._sessionUuid)
        assert gatewaywrapper.getTestImage() is not None
        assert g2_getTestImage() is not None
        g2.seppuku(softclose=True)
        pytest.raises(Ice.ConnectionLostException, g2_getTestImage)
        assert gatewaywrapper.getTestImage() is not None
        g2 = gatewaywrapper.gateway.clone()
        assert g2.connect(gatewaywrapper.gateway._sessionUuid)
        assert gatewaywrapper.getTestImage() is not None
        assert g2_getTestImage() is not None
        g2.seppuku(softclose=False)
        pytest.raises(Ice.ConnectionLostException, g2_getTestImage)
        pytest.raises(Ice.ObjectNotExistException, gatewaywrapper.getTestImage)
        gatewaywrapper._has_connected = False
        gatewaywrapper.doDisconnect()

    def testClose(self, gatewaywrapper, author_testimg):
        # author_testimg in args to make sure the image has been imported
        gatewaywrapper.loginAsAuthor()
        assert gatewaywrapper.getTestImage() is not None
        gatewaywrapper.gateway.close()
        pytest.raises(Ice.ConnectionLostException, gatewaywrapper.getTestImage)
        gatewaywrapper._has_connected = False
        gatewaywrapper.doDisconnect()
        gatewaywrapper.loginAsAuthor()
        g2 = gatewaywrapper.gateway.clone()

        def g2_getTestImage():
            return dbhelpers.getImage(g2, 'testimg1')
        assert g2.connect(gatewaywrapper.gateway._sessionUuid)
        assert gatewaywrapper.getTestImage() is not None
        assert g2_getTestImage() is not None
        g2.close()
        pytest.raises(Ice.ConnectionLostException, g2_getTestImage)
        pytest.raises(Ice.ObjectNotExistException, gatewaywrapper.getTestImage)
        gatewaywrapper._has_connected = False
        gatewaywrapper.doDisconnect()

    def testTopLevelObjects(self, gatewaywrapper, author_testimg):
        ##
        # Test listProjects as root (sees, does not own)
        parents = author_testimg.getAncestry()
        project_id = parents[-1].getId()
        # Original (4.1) test fails since 'admin' is logged into group 0, but
        # the project created above is in new group.
        # gatewaywrapper.loginAsAdmin()
        # test passes if we remain logged in as Author
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id in ids
        # test passes if we NOW log in as Admin (different group)
        gatewaywrapper.loginAsAdmin()
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id not in ids
        ##
        # Test listProjects as author (sees, owns)
        gatewaywrapper.loginAsAuthor()
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id in ids
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id in ids
        ##
        # Test listProjects as guest (does not see, does not own)
        gatewaywrapper.doLogin(gatewaywrapper.USER)
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id not in ids
        ids = [x.getId() for x in gatewaywrapper.gateway.listProjects()]
        assert project_id not in ids
        ##
        # Test getProject
        gatewaywrapper.loginAsAuthor()
        assert gatewaywrapper.gateway.getObject(
            "Project", project_id).getId() == project_id
        ##
        # Test getDataset
        dataset_id = parents[0].getId()
        assert gatewaywrapper.gateway.getObject(
            "Dataset", dataset_id).getId() == dataset_id
        ##
        # Test listExperimenters
        # exps = map(lambda x: x.omeName,
        # gatewaywrapper.gateway.listExperimenters())  # removed from blitz
        # gateway
        for exp, login in [
                (gatewaywrapper.USER, gatewaywrapper.loginAsUser),
                (gatewaywrapper.AUTHOR, gatewaywrapper.loginAsAuthor),
                (gatewaywrapper.ADMIN, gatewaywrapper.loginAsAdmin)]:
            login()
            exps = [x.omeName for x in
                    gatewaywrapper.gateway.getObjects("Experimenter")]
            omeName = exp.name
            assert omeName in exps
            assert len(list(gatewaywrapper.gateway.getObjects(
                "Experimenter", attributes={'omeName': omeName}))) > 0
        comboName = gatewaywrapper.USER.name + \
            gatewaywrapper.AUTHOR.name + gatewaywrapper.ADMIN.name
        assert len(list(gatewaywrapper.gateway.getObjects(
            "Experimenter", attributes={'omeName': comboName}))) == 0
        ##
        # Test lookupExperimenter
        gatewaywrapper.loginAsUser()
        assert gatewaywrapper.gateway.getObject(
            "Experimenter",
            attributes={'omeName': gatewaywrapper.USER.name}).omeName == \
            gatewaywrapper.USER.name
        assert gatewaywrapper.gateway.getObject(
            "Experimenter", attributes={'omeName': comboName}) is None
        ##
        # logged in as Author, test listImages(ns)

        def listImages(ns=None):
            imageAnnLinks = gatewaywrapper.gateway.getAnnotationLinks("Image",
                                                                      ns=ns)
            return [omero.gateway.ImageWrapper(gatewaywrapper.gateway,
                    link.parent) for link in imageAnnLinks]
        gatewaywrapper.loginAsAuthor()
        ns = 'weblitz.test_annotation'
        obj = gatewaywrapper.getTestImage()
        # Make sure it doesn't yet exist
        obj.removeAnnotations(ns)
        assert obj.getAnnotation(ns) is None
        # Check without the ann
        assert len(listImages(ns=ns)) == 0
        annclass = omero.gateway.CommentAnnotationWrapper
        # createAndLink
        annclass.createAndLink(target=obj, ns=ns, val='foo')
        imgs = listImages(ns=ns)
        assert len(imgs) == 1
        assert imgs[0] == obj
        # and clean up
        obj.removeAnnotations(ns)
        assert obj.getAnnotation(ns) is None

    def testCloseSession(self, gatewaywrapper):
        # 74 the failed connection for a user not in the system group does not
        # get closed
        gatewaywrapper.gateway.setIdentity(
            gatewaywrapper.USER.name, gatewaywrapper.USER.passwd)
        setprop = gatewaywrapper.gateway.c.ic.getProperties().setProperty
        list(map(lambda x: setprop(x[0], str(x[1])),
             list(gatewaywrapper.gateway._ic_props.items())))
        gatewaywrapper.gateway.c.ic.getImplicitContext().put(
            omero.constants.GROUP, gatewaywrapper.gateway.group)
        # I'm not certain the following assertion is as intended.
        # This should be reviewed, see ticket #6037
        # assert gatewaywrapper.gateway._sessionUuid ==  None
        pytest.raises(omero.ClientError, gatewaywrapper.gateway._createSession)
        assert gatewaywrapper.gateway._sessionUuid is not None
        # 74 bug found while fixing this, the uuid passed to closeSession was
        # not wrapped in rtypes, so logout didn't
        gatewaywrapper.gateway._closeSession()  # was raising ValueError
        gatewaywrapper.gateway = None

    def testMiscellaneous(self, gatewaywrapper):
        gatewaywrapper.loginAsUser()
        assert gatewaywrapper.gateway.getUser().omeName == \
            gatewaywrapper.USER.name

    def testConnectUsingClient(self, gatewaywrapper):
        gatewaywrapper.loginAsAdmin()
        username = "connect_test_user6"
        password = "foobar"
        last_name = "ConnectUsingClient"
        test_user = dbhelpers.UserEntry(username, password,
                                        firstname='User',
                                        lastname=last_name)
        test_user.create(gatewaywrapper.gateway, dbhelpers.ROOT.passwd)
        gatewaywrapper.doDisconnect()

        client = omero.client()
        client.createSession(username, password)
        with BlitzGateway(client_obj=client) as conn:
            assert conn.connect(), "Should be connected"

    def testConnectUsingClientNoSessionWithIdentity(self, gatewaywrapper):
        gatewaywrapper.loginAsAdmin()
        username = "connect_test_user7"
        password = "foobar"
        last_name = "ConnectUsingClientNoSessionWithIdentity"
        test_user = dbhelpers.UserEntry(username, password,
                                        firstname='User',
                                        lastname=last_name)
        test_user.create(gatewaywrapper.gateway, dbhelpers.ROOT.passwd)
        gatewaywrapper.doDisconnect()

        client = omero.client()
        with BlitzGateway(client_obj=client) as conn:
            conn.setIdentity(username, password)
            assert conn.connect(), "Should be connected"

    def testConnectUsingClientSessionWithoutIdentity(self, gatewaywrapper):
        gatewaywrapper.loginAsAdmin()
        username = "connect_test_user8"
        password = "foobar"
        last_name = "ConnectUsingClientSessionWithoutIdentity"
        test_user = dbhelpers.UserEntry(username, password,
                                        firstname='User',
                                        lastname=last_name)
        test_user.create(gatewaywrapper.gateway, dbhelpers.ROOT.passwd)
        gatewaywrapper.doDisconnect()

        client = omero.client()
        with BlitzGateway(client_obj=client) as conn:
            assert not conn.connect()

    def testSessionId(self, gatewaywrapper):
        gatewaywrapper.loginAsAdmin()
        username = "session_test_user"
        password = "foobar"
        last_name = "SessionId"
        test_user = dbhelpers.UserEntry(username, password,
                                        firstname='User',
                                        lastname=last_name)
        test_user.create(gatewaywrapper.gateway, dbhelpers.ROOT.passwd)
        gatewaywrapper.doDisconnect()

        client = omero.client()
        client.createSession(username, password)
        sid = client.getSessionId()
        with BlitzGateway(client_obj=client) as conn:
            assert sid == conn.getSession().getUuid().val

    def testConnectWithSessionId(self, gatewaywrapper):
        gatewaywrapper.loginAsAdmin()
        username = "connect_withsession_test_user"
        password = "foobar"
        last_name = "connect_withsessionId"
        test_user = dbhelpers.UserEntry(username, password,
                                        firstname='User',
                                        lastname=last_name)
        test_user.create(gatewaywrapper.gateway, dbhelpers.ROOT.passwd)
        gatewaywrapper.doDisconnect()

        client = omero.client()
        client.createSession(username, password)
        sid = client.getSessionId()
        with BlitzGateway(client_obj=client) as conn:
            assert conn.connect(sUuid=sid), "Should be connected"

    def testSecureWithSecureClient(self, gatewaywrapper):
        client = omero.client()
        client.createSession("root", dbhelpers.ROOT.passwd)
        assert client.isSecure()
        with BlitzGateway(client_obj=client) as conn:
            assert conn.isSecure()
            assert conn.c.isSecure()
            assert conn.secure
            conn.setSecure(False)
            assert not conn.isSecure()
            assert not conn.c.isSecure()
            assert not conn.secure

    def testSecureWithUnsecureClient(self, gatewaywrapper):
        client = omero.client()
        client.createSession("root", dbhelpers.ROOT.passwd)
        assert client.isSecure()
        unsecure_client = client.createClient(secure=False)
        client.__del__()

        with BlitzGateway(client_obj=unsecure_client) as conn:
            assert not conn.isSecure()
            assert not conn.c.isSecure()
            assert not conn.secure
            conn.setSecure(True)
            assert conn.isSecure()
            assert conn.c.isSecure()
            assert conn.secure

    @pytest.mark.parametrize("secure", [None, "False", "True"])
    def testSecureWithUsername(self, gatewaywrapper, secure):
        try:
            conn = BlitzGateway(username="root",
                                passwd=dbhelpers.ROOT.passwd,
                                host="localhost",
                                secure=secure)
            conn.connect()
            if secure:
                assert conn.isSecure()
                assert conn.c.isSecure()
                assert conn.secure
                conn.setSecure(False)
                assert not conn.isSecure()
                assert not conn.c.isSecure()
                assert not conn.secure
            else:
                assert not conn.isSecure()
                assert not conn.c.isSecure()
                assert not conn.secure
                conn.setSecure(True)
                assert conn.isSecure()
                assert conn.c.isSecure()
                assert conn.secure
        finally:
            conn.close()

    def testSecureMisMatch(self, gatewaywrapper):
        client = omero.client()
        client.createSession("root", dbhelpers.ROOT.passwd)
        assert client.isSecure()
        with pytest.raises(Exception) as ex:
            BlitzGateway(client_obj=client, secure=False)
        assert "do not match" in str(ex.value)

    def testHost(self, gatewaywrapper):
        gatewaywrapper.loginAsUser()
        client = gatewaywrapper.gateway.c
        with pytest.raises(Exception) as ex:
            BlitzGateway(client_obj=client, host="myserver.com")
        assert "do not match" in str(ex.value)
