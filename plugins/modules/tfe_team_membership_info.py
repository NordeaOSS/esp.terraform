#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_membership_info
short_description: List team memberships
description:
- Lists team memberships.
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
    - Terraform team to list the memberships of.
    - The team may be referred either by its id or its name.
    type: str
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
- name: Retrieve details on all team members
  esp.terraform.tfe_team_membership_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
json:
    description: Details on memberships.
    returned: success
    type: dict
    contains:
        data:
            description: Details on team.
            returned: success
            type: dict
            sample:
                attributes:
                    name: owners
                    organization-access:
                        manage-policies: true
                        manage-vcs-settings: true
                        manage-workspaces: true
                    permissions:
                        can-destroy: false
                        can-update-api-token: true
                        can-update-membership: true
                        can-update-organization-access: false
                        can-update-visibility: false
                    users-count: 1
                    visibility: secret
                id: team-VQ1FncissQs9Bom8
                links:
                    self: /api/v2/teams/team-VQ1FncissQs9Bom8
                relationships:
                    authentication-token:
                        meta: {}
                    organization:
                        data:
                            id: foo
                            type: organizations
                    organization-memberships:
                        data:
                            - id: ou-SKVvnWhoTxWrofkE
                              type: organization-memberships
                    users:
                        data:
                            - id: user-K1LWGyjmnDL59y4H
                              type: users
                type: teams
        members:
            description: Details on memberships.
            returned: success
            type: list
            elements: dict            
            sample:                
                  - attributes:
                        avatar-url: https://www.gravatar.com/avatar/73e8b34b8de0f050f5fdd7960ef0c756?s=100&d=mm
                        is-service-account: false
                        permissions:
                            can-change-email: false
                            can-change-username: false
                            can-create-organizations: true
                            can-manage-user-tokens: true
                        two-factor:
                            verified: false
                        username: john_smith
                    id: user-K1LWGyjmnDL59y4H
                    links:
                        self: /api/v2/users/user-K1LWGyjmnDL59y4H
                    relationships:
                        authentication-tokens:
                            links:
                                related: /api/v2/users/user-K1LWGyjmnDL59y4H/authentication-tokens
                    type: users
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
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    team = module.params['team']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        team=team,
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

    # Get existing team ID. 
    team_id = None
    # Refer to a team by its name
    if any(t['attributes']['name'] == team for t in all_teams['data']):
        team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
    elif any(t['id'] == team for t in all_teams['data']):
        team_id = team
    else:
        module.fail_json(msg='The supplied "%s" team does not exist in "%s" organization.' % (team, organization) )

    # Retrieve information for all memberships
    try:        
        ret = tfe.call_endpoint(tfe.api.teams.show, team_id=team_id, include=['users'])
    except Exception as e:
        module.fail_json(msg='Unable to retrieve details on a team in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    result['json']['data'] = ret['data']
    if 'included' in ret:
        result['json']['members'] = ret['included']
    else:
        result['json']['members'] = []

    module.exit_json(**result)


if __name__ == '__main__':
    main()