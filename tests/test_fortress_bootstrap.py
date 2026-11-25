"""Synthetic NI-01 regression tests bound to the production module."""
import importlib.util
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'fortress_bootstrap',
    Path(__file__).resolve().parents[1] / 'scripts' / 'fortress_bootstrap.py',
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)
classify_route = bootstrap.classify_route
assess_owner = bootstrap.assess_owner


class TestFortressBootstrap(unittest.TestCase):

    def test_classify_route_home_lan_true_vpn_up_true(self):
        """Test classify_route with home_lan=True and vpn_up=True -> 'lan'"""
        self.assertEqual(classify_route(True, True), 'lan')

    def test_classify_route_home_lan_true_vpn_up_false(self):
        """Test classify_route with home_lan=True and vpn_up=False -> 'lan'"""
        self.assertEqual(classify_route(True, False), 'lan')

    def test_classify_route_home_lan_false_vpn_up_true(self):
        """Test classify_route with home_lan=False and vpn_up=True -> 'vpn'"""
        self.assertEqual(classify_route(False, True), 'vpn')

    def test_classify_route_home_lan_false_vpn_up_false(self):
        """Test classify_route with home_lan=False and vpn_up=False -> 'unavailable'"""
        self.assertEqual(classify_route(False, False), 'unavailable')

    def test_classify_route_home_lan_none_vpn_up_none(self):
        """Test classify_route with home_lan=None and vpn_up=None -> 'unknown'"""
        self.assertEqual(classify_route(None, None), 'unknown')

    def test_classify_route_home_lan_false_vpn_up_none(self):
        """Test classify_route with home_lan=False and vpn_up=None -> 'unknown'"""
        self.assertEqual(classify_route(False, None), 'unknown')

    def test_classify_route_home_lan_none_vpn_up_true(self):
        """Test classify_route with home_lan=None and vpn_up=True -> 'unknown'"""
        self.assertEqual(classify_route(None, True), 'unknown')

    def test_classify_route_home_lan_none_vpn_up_false(self):
        """Test classify_route with home_lan=None and vpn_up=False -> 'unknown'"""
        self.assertEqual(classify_route(None, False), 'unknown')

    def test_assess_owner_matches(self):
        """Test assess_owner with matching owners -> 'matches'"""
        self.assertEqual(assess_owner('owner-a', 'owner-a'), 'matches')

    def test_assess_owner_mismatch(self):
        """Test assess_owner with mismatching owners -> 'mismatch'"""
        self.assertEqual(assess_owner('owner-b', 'owner-a'), 'mismatch')

    def test_assess_owner_observed_none(self):
        """Test assess_owner with observed_owner=None -> 'unknown'"""
        self.assertEqual(assess_owner(None, 'owner-a'), 'unknown')

    def test_assess_owner_expected_none(self):
        """Test assess_owner with expected_owner=None -> 'unknown'"""
        self.assertEqual(assess_owner('owner-a', None), 'unknown')


    def test_route_rejects_non_boolean_observations(self):
        for invalid in ('false', 'true', '', 0, 1, 0.0, 1.0, [], [True], {}, {'up': True}):
            for valid in (True, False, None):
                with self.subTest(invalid=invalid, valid=valid):
                    self.assertEqual(classify_route(invalid, valid), 'unknown')
                    self.assertEqual(classify_route(valid, invalid), 'unknown')

    def test_owner_requires_nonempty_strings_on_both_sides(self):
        for invalid in ('', ' ', '\t\n', False, True, 0, 1, 0.0, [], {}, None):
            with self.subTest(invalid=invalid):
                self.assertEqual(assess_owner(invalid, invalid), 'unknown')
                self.assertEqual(assess_owner(invalid, 'owner-a'), 'unknown')
                self.assertEqual(assess_owner('owner-a', invalid), 'unknown')
        self.assertEqual(assess_owner(False, 0), 'unknown')

    def test_valid_owner_claims_compare_exactly_without_normalization(self):
        self.assertEqual(assess_owner(' owner-a ', 'owner-a'), 'mismatch')
        self.assertEqual(assess_owner('Owner-a', 'owner-a'), 'mismatch')




class TestBootstrapReport(unittest.TestCase):
    def test_remaining_route_combination(self):
        self.assertEqual(classify_route(True, None), 'lan')

    def test_report_route_owner_and_availability_matrix(self):
        routes = [(True, True, 'lan'), (True, False, 'lan'),
                  (True, None, 'lan'), (False, True, 'vpn'),
                  (False, False, 'unavailable'), (False, None, 'unknown'),
                  (None, True, 'unknown'), (None, False, 'unknown'),
                  (None, None, 'unknown')]
        owners = [('owner-a', 'owner-a', 'matches'),
                  ('owner-b', 'owner-a', 'mismatch'),
                  (None, 'owner-a', 'unknown'),
                  ('owner-a', None, 'unknown'), (None, None, 'unknown')]
        states = [(True, 'available'), (False, 'unavailable'), (None, 'unknown')]
        for home, vpn, route in routes:
            for observed, expected, owner in owners:
                for service_value, service in states:
                    for source_value, source in states:
                        with self.subTest(home=home, vpn=vpn, owner=owner,
                                          service=service, source=source):
                            report = bootstrap.report_bootstrap(dict(
                                home_lan=home, vpn_up=vpn,
                                observed_owner=observed, expected_owner=expected,
                                service_available=service_value,
                                source_available=source_value))
                            self.assertEqual(report, dict(
                                route=route, owner_status=owner,
                                service_status=service, source_status=source,
                                live_acceptance='not_run'))

    def test_vpn_up_service_down(self):
        report = bootstrap.report_bootstrap(dict(home_lan=False, vpn_up=True,
            service_available=False, source_available=None))
        self.assertEqual(report['route'], 'vpn')
        self.assertEqual(report['service_status'], 'unavailable')
        self.assertEqual(report['source_status'], 'unknown')

    def test_vpn_up_source_down_service_up(self):
        report = bootstrap.report_bootstrap(dict(home_lan=False, vpn_up=True,
            service_available=True, source_available=False))
        self.assertEqual(report['route'], 'vpn')
        self.assertEqual(report['service_status'], 'available')
        self.assertEqual(report['source_status'], 'unavailable')

    def test_missing_fields_remain_unknown(self):
        self.assertEqual(bootstrap.report_bootstrap({}), dict(
            owner_status='unknown', route='unknown', service_status='unknown',
            source_status='unknown', live_acceptance='not_run'))

    def test_privacy_canaries_and_input_preservation(self):
        evidence = dict(home_lan=False, vpn_up=True,
            observed_owner='SYNTHETIC_IDENTITY_CANARY', expected_owner='owner-a',
            credentials='SYNTHETIC_CREDENTIAL_CANARY',
            ha_state='SYNTHETIC_HA_CANARY',
            command='SYNTHETIC_COMMAND_CANARY --private-argument',
            resource_contents={'nested': 'SYNTHETIC_RESOURCE_CANARY'},
            description='<script>SYNTHETIC_DESCRIPTION_CANARY</script>',
            uri='https://example.invalid/SYNTHETIC_URI_CANARY',
            icon='https://example.invalid/SYNTHETIC_ICON_CANARY',
            unknown='SYNTHETIC_UNKNOWN_CANARY', live_acceptance='passed')
        before = json.dumps(evidence, sort_keys=True)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            report = bootstrap.report_bootstrap(evidence)
        self.assertEqual(set(report), {'owner_status', 'route', 'service_status',
                                      'source_status', 'live_acceptance'})
        self.assertEqual(report['owner_status'], 'mismatch')
        self.assertEqual(report['live_acceptance'], 'not_run')
        self.assertNotIn('CANARY', json.dumps(report))
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), '')
        self.assertEqual(json.dumps(evidence, sort_keys=True), before)

    def test_non_boolean_availability_is_unknown(self):
        for value in ['SYNTHETIC_CANARY', 'true', 1, 0, [], {}]:
            with self.subTest(value=value):
                report = bootstrap.report_bootstrap(dict(
                    service_available=value, source_available=value))
                self.assertEqual(report['service_status'], 'unknown')
                self.assertEqual(report['source_status'], 'unknown')

    def test_report_keeps_invalid_route_and_owner_observations_unknown(self):
        report = bootstrap.report_bootstrap(dict(home_lan='false', vpn_up='true',
            observed_owner=False, expected_owner=0, service_available=True,
            source_available=False, live_acceptance='passed'))
        self.assertEqual(report, dict(route='unknown', owner_status='unknown',
            service_status='available', source_status='unavailable', live_acceptance='not_run'))

    def test_report_uses_production_helpers(self):
        with patch.object(bootstrap, 'classify_route', return_value='unknown') as route:
            with patch.object(bootstrap, 'assess_owner', return_value='mismatch') as owner:
                report = bootstrap.report_bootstrap(dict(home_lan=True, vpn_up=False,
                    observed_owner='owner-a', expected_owner='owner-a'))
        route.assert_called_once_with(True, False)
        owner.assert_called_once_with('owner-a', 'owner-a')
        self.assertEqual(report['route'], 'unknown')
        self.assertEqual(report['owner_status'], 'mismatch')


if __name__ == '__main__':
    unittest.main()
