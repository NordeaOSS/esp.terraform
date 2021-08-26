#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_info
short_description: List teams in the organization
description:
- Lists teams in the organization.
- Details on a team can be retrieved either by its ID or by its name.
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
    - List of teams to retrieve details for.
    - This can be '*' which means all teams.
    - One may refer to a team either by its ID or its name.
    type: list
    required: false
    default: [ '*' ]
  include:
    description:
    - Return additional information about nested resources.
    - This can be only C(users) as of now.
    type: list
    elements: str
    required: false    
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
- name: Retrieve details on all teams in the organization, include additional information about users
  esp.terraform.tfe_team_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team:
      - '*'
    include:
      - users
    validate_certs: no
  register: _result

- name: Retrieve details on the given teams (supplied by names or IDs), in the organization
  esp.terraform.tfe_team_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team:
      - owners
      - team-VQ1FncissQs9Bom8
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on teams.
    returned: success
    type: dict
    contains:
        data:
            description: Details on teams.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
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
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        team=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
        include=dict(type='list', elements='str', no_log=False, required=False, choices=['users']),          
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    include = module.params['include']

    # Parse `team` parameter and create list of teams.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all teams.
    teams = module.params['team']
    if isinstance(module.params['team'], collections.Iterable):
        teams = [p.strip() for p in module.params['team']]
        teams = tfe.listify_comma_sep_strings_in_list(teams)
    if not teams:
        teams = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        teams=teams,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    if '*' in teams:
        # Retrieve information for all teams
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.teams.list_all, include=include)
        except Exception as e:
            module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    else:
        result['json']['data'] = []
        # First, get the list of all teams
        try:        
            all_teams = tfe.call_endpoint(tfe.api.teams.list_all, include=None)
        except Exception as e:
            module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        # Next, iterate over the supplied teams to retrieve their details
        for team in teams:

            # Refer to a team by its name
            if any(t['attributes']['name'] == team for t in all_teams['data']):
                try:
                    team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
                    ret = tfe.call_endpoint(tfe.api.teams.show, team_id=team_id, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a team in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            # Refer to a team by its ID
            else:
                try:        
                    ret = tfe.call_endpoint(tfe.api.teams.show, team_id=team, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a team in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            result['json']['data'].append(ret['data'])           

    module.exit_json(**result)


if __name__ == '__main__':
    main()