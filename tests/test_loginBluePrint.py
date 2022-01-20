import uuid
from tempfile import TemporaryDirectory

from lodstorage.storageconfig import StorageConfig, StoreMode

from onlinespreadsheet.loginBlueprint import UserManager, User, Roles
from tests.basetest import BaseTest
from tests.test_WebServer import TestWebServer


class TestLoginBlueprint(TestWebServer):
    """
    tests the LoginBluePrint
    """

    def setUp(self) -> None:
        super(TestLoginBlueprint, self).setUp()
        self.testPassword="password"
        self.testAdmin=User.getFromArgs(id="admin@example.org",roles=[Roles.ADMIN], username="Admin", wikidataid="Q1", password=self.testPassword)
        self.testUser = User.getFromArgs(id="user@example.org", roles=[Roles.USER], username="User",wikidataid="Q2", password=self.testPassword)

    def test_pageRestrictions(self):
        """
        tests if certain pages are login protected
        """
        restrictedRoutes=["/users", "/users/new", "/users/test@me.com"]
        for restrictedRoute in restrictedRoutes:
            response=self.client.get(restrictedRoute)
            self.assertEqual(401, response.status_code)

    def test_roleRestrictions(self):
        """
        tests if certain pages are only accessible by users with corresponding roles
        """
        restrictedRoutes=["/users", "/users/new", "/users/test@me.com"]
        for restrictedRoute in restrictedRoutes:
            self.createUserAndLogin(self.testAdmin)
            self.assertEqual(200, self.client.get(restrictedRoute).status_code)
            self.createUserAndLogin(self.testUser) # unauthorized user for the path
            self.assertEqual(401, self.client.get(restrictedRoute).status_code)

    def createUserAndLogin(self, user:User)->User:
        """
        create the user id necessary and login
        """
        self.client.get("/logout")
        # ensure the the user exists
        try:
            self.ws.loginBluePrint.userManager.addUser(user)
        except Exception as e:
            print(e)
        response = self.client.post('login', data={"username": user.id, "password": self.testPassword})
        self.assertEqual(302, response.status_code)


class TestUserManager(BaseTest):
    """
    tests UserManager
    """

    def setUp(self,debug=False,profile=True):
        super(TestUserManager, self).setUp(debug=debug, profile=profile)
        self.tmpDir = TemporaryDirectory(suffix="ose_test")
        self.config = StorageConfig(mode=StoreMode.SQL, cacheRootDir=self.tmpDir.name, cacheDirName="ose")
        self.manager = UserManager(storageConfig=self.config)

    def tearDown(self):
        super(TestUserManager, self).tearDown()
        self.tmpDir.cleanup()

    def test_userCreation(self):
        """
        tests creating a new user
        """
        password="paswordTest"
        testUser = User.getFromArgs(id="alice@example.org", username="Alice", wikidataid="Q1", password=password)
        self.manager.addUser(testUser)
        user = self.manager.getUser(testUser.id)
        self.assertTrue(user.checkPassword(password))

    def test_uniqueUser(self):
        """
        test if a user can not be over written
        """
        password = "paswordTest"
        testUser = User.getFromArgs(id="unique@example.org", username="unique", wikidataid="Q2", password=password)
        self.manager.addUser(testUser)
        self.assertRaises(Exception, self.manager.addUser, testUser)

    def test_dbPersistence(self):
        """
        tests if data is preserved if a new UserManager is initialized with the same config
        """
        password = "paswordTest"
        testUser = User.getFromArgs(id="alice@example.org", username="Alice", wikidataid="Q1", password=password)
        self.manager.addUser(testUser)
        newManager = UserManager(storageConfig=self.config)
        user = newManager.getUser(testUser.id)
        self.assertTrue(user.checkPassword(password))


    def test_userRoles(self):
        """
        tests assigning and checking user roles
        """
        roles = [Roles.USER, Roles.ADMIN]
        testUser = User.getFromArgs(id="roleTest@example.org", username="roleTest", wikidataid="Q1", password="password", roles=roles)
        self.manager.addUser(testUser)
        user = self.manager.getUser(testUser.id)
        self.assertListEqual(roles, user.roles)