"""Offline classification of supplied evidence; never live identity verification."""

def classify_route(home_lan, vpn_up):
    """
    Classify network route based on home LAN and VPN status.

    Args:
        home_lan (bool or None): True if known to be home LAN, False if away, None if unknown
        vpn_up (bool or None): True if VPN is up, False if down, None if unknown

    Returns:
        str: 'lan' for known home LAN, 'vpn' for known away + VPN, 'unavailable' for known away without VPN,
             'unknown' for unresolved inputs
    """
    # If home_lan is unknown, route is unknown even if VPN is known
    if home_lan is None:
        return 'unknown'

    # If home_lan is True, we're on LAN regardless of VPN status
    if home_lan:
        return 'lan'

    # At this point, home_lan is False (away)
    # If VPN is up, we're using VPN
    if vpn_up:
        return 'vpn'

    # If VPN is down, we're unavailable
    if vpn_up is False:
        return 'unavailable'

    # If VPN status is unknown, route is unknown
    return 'unknown'


def assess_owner(observed_owner, expected_owner):
    """
    Assess owner claim against expected owner.

    Args:
        observed_owner (str or None): Observed owner name or None if unknown
        expected_owner (str or None): Expected owner name or None if unknown

    Returns:
        str: 'matches' if owners match, 'mismatch' if they don't, 'unknown' if either is None
    """
    # If either owner is unknown, return 'unknown'
    if observed_owner is None or expected_owner is None:
        return 'unknown'

    # If both owners are present and equal, return 'matches'
    if observed_owner == expected_owner:
        return 'matches'

    # If both owners are present but different, return 'mismatch'
    return 'mismatch'


def _availability(value):
    if value is True:
        return 'available'
    if value is False:
        return 'unavailable'
    return 'unknown'


def report_bootstrap(evidence):
    """Return only allowlisted status labels from a supplied evidence mapping.

    Missing fields are unknown. Availability accepts bool/None; other values
    stay unknown. Owner comparison is a claim comparison, not authentication.
    This function performs no probes, logging, persistence or control actions.
    """
    return {
        'owner_status': assess_owner(evidence.get('observed_owner'),
                                     evidence.get('expected_owner')),
        'route': classify_route(evidence.get('home_lan'), evidence.get('vpn_up')),
        'service_status': _availability(evidence.get('service_available')),
        'source_status': _availability(evidence.get('source_available')),
        'live_acceptance': 'not_run',
    }
