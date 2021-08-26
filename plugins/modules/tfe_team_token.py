#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_token
short_description: Generate and delete the team token
description:
- Generates a new team token and deletes the existing token.
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
    - Terraform Team.
    - The team may be referred either by its id or its name.
    type: str
    required: true       
  state:
    description:
    - Whether the team token should exist or not.
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
- name: Generate a new team token
  esp.terraform.tfe_team_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo     
    team: developers
    state: present
    validate_certs: no
  register: _result

- debug:
    msg: "{{ _result.json.data.attributes.token }}"

- name: Destroy the team token
  esp.terraform.tfe_team_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers     
    state: absent
    validate_certs: no
'''

RETURN = r'''
json:
    description: Details on team token.
    returned: success
    type: dict
    contains:
        data:
            description: Details on team token.
            returned: success
            type: dict                  
            sample:
                attributes:
                    created-at: 2021-04-27T06:30:13.827Z
                    description: null
                    last-used-at: null
                    token: 9cYRjBE....WuvlXJ0dI
                id: at-6Ljdprm87HYE5oVB
                relationships:
                    created-by:
                        data:
                            id: user-K1LWGyjmnDL59y4H
                            type: users
                type: authentication-tokens               
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        team=dict(type='str', required=True, no_log=False),      
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

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        team=team,
        state=state,
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

    # Delete the team token if state == 'absent'
    if state == 'absent':

        if not module.check_mode:            
            result['json'] = tfe.call_endpoint(tfe.api.team_tokens.destroy, team_id=team_id)
        result['changed'] = True
 
    # Generate a new team token if state == 'present'
    else:

        if not module.check_mode:            
            result['json'] = tfe.call_endpoint(tfe.api.team_tokens.create, team_id=team_id, payload=None)
        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()