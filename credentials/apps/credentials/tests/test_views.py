"""
Tests for credentials rendering views.
"""
from __future__ import unicode_literals
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import patch

from credentials.apps.api.tests import factories
from credentials.apps.credentials.models import Signatory, UserCredential
from credentials.apps.credentials.tests.mixins import OrganizationsDataMixin, ProgramsDataMixin, UserDataMixin
from credentials.apps.credentials.views import RenderCredential


class RenderCredentialPageTests(TestCase):
    """ Tests for credential rendering view. """

    def setUp(self):
        super(RenderCredentialPageTests, self).setUp()
        self.program_certificate = factories.ProgramCertificateFactory.create(template=None)
        self.signatory_1 = Signatory.objects.create(name='Signatory 1', title='Manager', image='images/signatory_1.png')
        self.signatory_2 = Signatory.objects.create(name='Signatory 1', title='Manager', image='images/signatory_1.png')
        self.program_certificate.signatories.add(self.signatory_1, self.signatory_2)
        self.user_credential = factories.UserCredentialFactory.create(
            credential=self.program_certificate
        )

    def _credential_url(self, uuid_string):
        """ Helper method to generate the url for a credential."""
        return reverse('credentials:render', kwargs={'uuid': uuid_string})

    def test_get_cert_with_awarded_status(self):
        """ Verify that the view renders a certificate and returns 200 when the
        uuid is valid and certificate status is 'awarded'.
        """
        path = self._credential_url(self.user_credential.uuid.hex)
        with patch('credentials.apps.credentials.views.get_program') as mock_program_data:
            mock_program_data.return_value = ProgramsDataMixin.PROGRAMS_API_RESPONSE
            with patch('credentials.apps.credentials.views.get_organization') as mock_org_data:
                mock_org_data.return_value = OrganizationsDataMixin.ORGANIZATIONS_API_RESPONSE
                with patch('credentials.apps.credentials.views.get_user') as user_data:
                    user_data.return_value = UserDataMixin.USER_API_RESPONSE
                    response = self.client.get(path)

        self.assertEqual(response.status_code, 200)
        self._assert_user_credential_template_data(response, self.user_credential)
        self._assert_signatory_data(response, self.signatory_1)
        self._assert_signatory_data(response, self.signatory_2)

    def test_get_cert_with_revoked_status(self):
        """ Verify that the view returns 404 when the uuid is valid but certificate status
        is 'revoked'.
        """
        self.user_credential.status = UserCredential.REVOKED
        self.user_credential.save()
        path = self._credential_url(self.user_credential.uuid.hex)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 404)

    def test_get_cert_with_invalid_uuid(self):
        """ Verify that view returns 404 with invalid uuid."""
        path = self._credential_url(uuid.uuid4().hex)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 404)

    def test_get_cert_with_wrong_certificate_type(self):
        """ Verify that the view returns 404 when the uuid refers to a certificate
        type other than a ProgramCertificate.
        """
        course_certificate = factories.CourseCertificateFactory.create(template=None)
        user_credential = factories.UserCredentialFactory.create(
            credential=course_certificate
        )

        path = self._credential_url(user_credential.uuid.hex)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 404)

    def _assert_user_credential_template_data(self, response, user_credential):
        """ Verify the default template has the data. """
        self.assertContains(response, 'Congratulations, Test User')
        self.assertContains(response, user_credential.uuid.hex)
        issued_date = '{month} {year}'.format(
            month=user_credential.modified.strftime("%B"),
            year=user_credential.modified.year
        )
        self.assertContains(response, issued_date)

        # test organization related data.
        self.assertContains(response, 'Test Organization')
        self.assertContains(response, 'http://testserver/media/organization_logos/test_org_logo.png')

        # test programs data
        self.assertContains(
            response,
            'a series of 2 courses offered by Test Organization through {platform_name}'.format(
                platform_name=settings.PLATFORM_NAME)
        )
        self.assertContains(response, 'Test Program A')

        # test html strings are appearing on page.
        self.assertContains(
            response,
            'XSeries Certificate | {platform_name}'.format(platform_name=settings.PLATFORM_NAME)
        )
        self._assert_html_data(response)

    def _assert_html_data(self, response):
        """ Helper method to check html data."""
        self.assertContains(response, 'Print this certificate')
        self.assertContains(response, 'images/logo-edX.png')
        self.assertContains(response, 'images/edx-openedx-logo-tag.png')
        self.assertContains(response, 'http://testserver/media/organization_logos/test_org_logo.png')
        self.assertContains(response, 'offers interactive online classes and MOOCs from the')
        self.assertContains(
            response,
            'An {platform_name} XSeries certificate signifies that the learner has'.format(
                platform_name=settings.PLATFORM_NAME
            )
        )
        self.assertContains(response, 'All rights reserved except where noted. edX')

    def _assert_signatory_data(self, response, signatory):
        """ DRY method to check signatory data."""
        self.assertContains(response, signatory.name)
        self.assertContains(response, signatory.title)
        self.assertContains(response, signatory.image)

    def test_get_programs_data(self):
        """ Verify the method parses the programs data correctly. """
        expected_data = {
            'category': 'xseries',
            'course_count': 2,
            'name': 'Test Program A',
            'organization_key': 'organization-a'
        }

        with patch('credentials.apps.credentials.views.get_program') as mock_program_data:
            mock_program_data.return_value = ProgramsDataMixin.PROGRAMS_API_RESPONSE
            self.assertEqual(
                expected_data,
                RenderCredential()._get_program_data(100)  # pylint: disable=protected-access
            )

    def test_get_cert_with_awarded_status_without_signatory(self):
        """ Verify that the view renders a certificate if program credential has no
        signatory data with it.
        """
        self.program_certificate.signatories.clear()
        path = self._credential_url(self.user_credential.uuid.hex)
        with patch('credentials.apps.credentials.views.get_program') as mock_program_data:
            mock_program_data.return_value = ProgramsDataMixin.PROGRAMS_API_RESPONSE
            with patch('credentials.apps.credentials.views.get_organization') as mock_org_data:
                mock_org_data.return_value = OrganizationsDataMixin.ORGANIZATIONS_API_RESPONSE
                with patch('credentials.apps.credentials.views.get_user') as user_data:
                    user_data.return_value = UserDataMixin.USER_API_RESPONSE
                    response = self.client.get(path)

        self.assertEqual(response.status_code, 200)
        self._assert_user_credential_template_data(response, self.user_credential)
        self.assertNotContains(response, self.signatory_1.name)
        self.assertNotContains(response, self.signatory_2.name)