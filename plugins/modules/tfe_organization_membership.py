#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_organization_membership
short_description: Manage Organization membership
description:
- Manages Organization membership, adds users to organizations and removes users from organizations.
- Users are added to organizations by inviting them to join. Once accepted, they become members of the organization. The Organization Membership resource represents this membership.
- All users must be added to at least one team.
- You can invite users who already have an account, as well as new users. 
- If the user has an existing account with the same email address used to invite them, they can reuse the same login.
author:
  - Krzysztof Lewandowski (@klewan)
version_added: 0.1.0
options:
  url:
    description:
    - Terraform Enterprise URL.
    type: str
    required: false
  token:
    description:
    - All requests to Terraform Enterprise must be authenticated with a bearer token.
    - There are three kinds of token available, i.e. user tokens, team tokens and organization tokens.
    - See L(Authentication,https://www.terraform.io/docs/cloud/api/index.html#authentication).
    type: str
    required: true
  organization:
    description:
    - Organization name.
    type: str
    required: true                       
  user:
    description:
    - The user to be invited or deleted.
    - If C(state=present) you must refer to the user by user email.
    - If C(state=absent) you may refer to the user either by user login, ID, email or existing organization membership_id as well.
    type: str
    required: true
  teams:
    description:
    - List of teams the invited user will be a member of.
    - All users must be added to at least one team.
    - You may refer to the team either by team name or its ID.
    - Required when C(state=present).
    type: list
    required: false  
  state:
    description:
    - Whether the user should be a member of the organization or not.
    type: str
    default: present
    choices: [ absent, present ]
    required: true
  validate_certs:
    description:
      - If C(no), SSL certificates will not be validated.
      - This should only set to C(no) used on personally controlled sites using self-signed certificates.
    type: bool
    default: yes
  use_proxy:
    description:
      - If C(no), it will not use a proxy, even if one is defined in an environment variable on the target hosts.
    type: bool
    default: yes 
  sleep:
    description:
      - Number of seconds to sleep between API retries.
    type: int
    default: 5
  retries:
    description:
      - Number of retries to call Terraform API URL before failure.
    type: int
    default: 3
notes:
- Authentication must be done with U(token).
- Supports C(check_mode).
'''

EXAMPLES = r'''
- name: Invite a user to an Organization
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    user: jsmith@example.com
    teams:
      - owners 
    state: present
    validate_certs: no

- name: Invite a user to an Organization
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    user: jsmith@example.com
    teams:
      - team-VQ1FncissQs9Bom8
      - developers
    state: present
    validate_certs: no

- name: Remove user from Organization, refer to the user by user email
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo     
    user: jsmith@example.com    
    state: absent
    validate_certs: no

- name: Remove user from Organization, refer to the user by user ID
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo     
    user: user-K1LWGyjmnDL59y4H    
    state: absent
    validate_certs: no

- name: Remove user from Organization, refer to the user by user login
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo     
    user: john_smith    
    state: absent
    validate_certs: no

- name: Remove user from Organization, refer to the user by organization membership_id
  esp.terraform.tfe_organization_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo     
    user: ou-SKVvnWhoTxWrofkE   
    state: absent
    validate_certs: no    
'''

RETURN = r'''
state:
    description: Organization membership state
    returned: always
    type: str
    sample: present
json:
    description: Details on organization membership.
    returned: success
    type: dict
    contains:
        data:
            description: Details on organization membership.
            returned: success
            type: dict                  
            sample:
                attributes:
                    created-at: 2021-04-25T19:17:31.368Z
                    email: jsmith@example.com
                    status: invited
                id: ou-hPb9GEGDdpVKM8Z5
                relationships:
                    organization:
                        data:
                            id: foo
                            type: organizations
                    teams:
                        data:
                            - id: team-VQ1FncissQs9Bom8
                              type: teams
                    user:
                        data:
                            id: user-ctVahEhZNb22D5Se
                            type: users
                type: organization-memberships             
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def get_user_details(module, tfe, organization=None, user=None):
    """
    Returns a dictionary with user details including user email, login, ID and the supplied organization membership ID.

    """
    user_details = {}

    # Search for all organization memberships
    try:        
        all_memberships = tfe.call_endpoint(tfe.api.org_memberships.list_all_for_org, query=None, filters=None, include=["user"])
    except Exception as e:
        module.fail_json(msg='Unable to list memberships in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Try to find organization membership based on the supplied user value
    if any(m['id'] == user or m['attributes']['email'] == user or m['relationships']['user']['data']['id'] == user for m in all_memberships['data']):
        user_organization_membership = [m for m in all_memberships['data'] if m['id'] == user or m['attributes']['email'] == user or m['relationships']['user']['data']['id'] == user][0]
        user_details = dict(
            email=user_organization_membership['attributes']['email'],
            id=user_organization_membership['relationships']['user']['data']['id'],
            username=None,
            organization_membership_id=user_organization_membership['id']             
        )

    if any(i['attributes']['username'] == user for i in all_memberships['included']):
        included_info = [i for i in all_memberships['included'] if i['attributes']['username'] == user][0]
        user_details = dict(
            email=included_info['attributes']['email'],
            id=included_info['id'],
            username=user,
            organization_membership_id=None             
        )
        user_organization_membership = [m for m in all_memberships['data'] if m['attributes']['email'] == user_details['email']][0]
        user_details['organization_membership_id'] = user_organization_membership['id'] 

    return user_details


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        user=dict(type='str', required=True, no_log=False),
        teams=dict(type='list', elements='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'present', ('teams',), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    state = module.params['state']
    user = module.params['user']
    
    if module.params['teams'] is not None:
        teams = []
        teams = [p.strip() for p in module.params['teams']]
        teams = tfe.listify_comma_sep_strings_in_list(teams)
    else:
        teams = None

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        user=user,
        state=state,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get user details, such as username, email, ID and membership ID.
    user_details = get_user_details(module, tfe, organization=organization, user=user)
    
    # Remove a User from Organization if membership exists and state == 'absent'
    if (state == 'absent') and (user_details.get('organization_membership_id', None) is not None):

        if not module.check_mode:            
            result['json'] = tfe.call_endpoint(tfe.api.org_memberships.remove, org_membership_id=user_details['organization_membership_id'])
        result['changed'] = True
 
    # Invite a User to an Organization if membership does not exist and state == 'present'
    if (state == 'present') and (user_details.get('organization_membership_id', None) is None):

        # When the user accout does not exist, assume it is a valid email
        if not bool(user_details):
            user_details['email'] = user

        org_membership_payload = {
          "data": {
            "attributes": {
              "email": user_details['email']
            },
            "relationships": {
              "teams": {
                "data": []
              },
            },
            "type": "organization-memberships"
          }
        }

        # Get all teams
        try:        
            all_teams = tfe.call_endpoint(tfe.api.teams.list_all, include=None)
        except Exception as e:
            module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        for team in teams:
            # Refer to a team by its name
            if any(t['attributes']['name'] == team for t in all_teams['data']):
                team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
            elif any(t['id'] == team for t in all_teams['data']):
                team_id = team
            else:
                module.fail_json(msg='Unable to find "%s" team in "%s" organization.' % (team, organization) )

            org_membership_payload['data']['relationships']['teams']['data'].append({'type': 'teams', 'id': team_id})

        if not module.check_mode:            
            result['json'] = tfe.call_endpoint(tfe.api.org_memberships.invite, payload=org_membership_payload)
        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()