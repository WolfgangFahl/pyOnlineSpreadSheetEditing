import datetime

from onlinespreadsheet.profile import Profile
from tests.basetest import BaseTest
from tests.test_WebServer import TestWebServer


class TestProfile(BaseTest):
    """
    tests Profile class
    """

    def test_wikidataQueries(self):
        """
        tests querying user information
        """
        mj = Profile(wikidataid="Q1910001")
        self.assertEqual("Matthias", mj.firstname)
        self.assertEqual("0000-0001-6169-2942", mj.ids["ORCID iD"]["id"])
        self.assertEqual("https://orcid.org/0000-0001-6169-2942", mj.ids["ORCID iD"]["url"])
        self.assertEqual(datetime.datetime(year=1952, month=5, day=28), mj.dateOfBirth)


class TestProfileBluePrint(TestWebServer):
    """
    tests the ProfileBluePrint
    """

    def test_profilePage(self):
        """
        tests if the profile page can be rendered
        """
        htmlProfilePage = self.getResponseHtml("/profile/Q1910001")
        self.assertTrue("Matthias Jarke" in htmlProfilePage)
        self.assertTrue("0000-0001-6169-2942" in htmlProfilePage)
