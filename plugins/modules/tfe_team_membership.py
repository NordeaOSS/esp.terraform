#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_membership
short_description: Manage team membership
description:
- Adds or removes users from teams.
- Both users and the team must already exist.
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
  team:
    description:
    - Terraform team to add users to or remove users from.
    - The team may be referred either by its id or its name.
    type: str
    required: true   
  user:
    description:
    - List of users to add or remove from the team.
    - You must refer to a user by its name when C(state=present).
    - You may refer to a user either by its id or its user name when C(state=absent).
    type: list
    required: true
  state:
    description:
    - Whether the users should be members of the team or not.
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
- name: Add users to a team
  esp.terraform.tfe_team_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: owners
    user:
      - john_smith  
    state: present 
    validate_certs: no
  register: _result

- name: Remove users from a team
  esp.terraform.tfe_team_membership:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: owners
    user:
      - john_smith
      - user-ctVahEhZNb22D5Se   
    state: absent 
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
team:
    description: Team name or ID
    returned: always
    type: str
    sample: owners    
state:
    description: Membership state
    returned: always
    type: str
    sample: present    
users:
    description: List of users added or removed.
    returned: success
    type: list
    elements: str
    sample:
        - user-K1LWGyjmnDL59y4H
        - john_smith
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        team=dict(type='str', required=True, no_log=False),  
        user=dict(type='list', elements='str', required=True, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),   
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    team = module.params['team']
    state = module.params['state']
    users = module.params['user']
    if isinstance(module.params['user'], collections.Iterable):
        users = [p.strip() for p in module.params['user']]
        users = tfe.listify_comma_sep_strings_in_list(users)

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        team=team,
        state=state,
        users=users,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all teams
    try:        
        all_teams = tfe.call_endpoint(tfe.api.teams.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get team ID. 
    team_id = None
    # Refer to a team by its name
    if any(t['attributes']['name'] == team for t in all_teams['data']):
        team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
    elif any(t['id'] == team for t in all_teams['data']):
        team_id = team
    else:
        module.fail_json(msg='The supplied "%s" team does not exist in "%s" organization.' % (team, organization) )

    # Retrieve information for all memberships in the team
    try:        
        team_details = tfe.call_endpoint(tfe.api.teams.show, team_id=team_id, include=['users'])
    except Exception as e:
        module.fail_json(msg='Unable to retrieve details on a team in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    if 'included' in team_details:
        current_members = team_details['included']
    else:
        current_members = []

    u_payload = {
        "data": []
    }

    # Add users to a teams when state == 'present'
    if state == 'present':

        for user in users:
            # Search for the user among existing team members
            matching_members = [m for m in current_members if m['attributes']['username'] == user or m['id'] == user]
            if len(matching_members) == 0:
                u_payload['data'].append({'type': 'users', 'id': user})

        if len(u_payload['data']) > 0:
            if not module.check_mode:
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.team_memberships.add_user_to_team, team_id=team_id, payload=u_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to add users to "%s" team in "%s" organization. Error: %s.' % (team, organization, to_native(e)) )    

            result['changed'] = True

    # Remove users from a teams when state == 'absent'
    if state == 'absent':

        for user in users:
            # Search for the user among existing team members
            matching_members = [m for m in current_members if m['attributes']['username'] == user or m['id'] == user]
            if len(matching_members) == 1:
                u_payload['data'].append({'type': 'users', 'id': matching_members[0]['attributes']['username']})

        if len(u_payload['data']) > 0:
            if not module.check_mode:
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.team_memberships.remove_user_from_team, team_id=team_id, payload=u_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to remove users from "%s" team in "%s" organization. Error: %s.' % (team, organization, to_native(e)) )    

            result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()