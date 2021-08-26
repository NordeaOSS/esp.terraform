#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team
short_description: Create, update, and destroy teams
description:
- Creates, edits or destroys Terraform teams, as well as manages a team's organization-level permissions.
- A team may be referred either by its id or its name.
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
    - Team to edit or remove.
    - The team may be referred either by its id or its name.
    type: str
    required: false    
  attributes:
    description:
    - Definition of the attributes for the team.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      name:
        description:
        - Name of the team.
        - This will be used as an identifier and must be unique in the organization.
        type: str
        required: true    
      visibility:
        description:
        - The team's visibility. 
        - Must be "secret" or "organization" (visible).
        type: str
        choices: [ secret, organization ]
        default: secret
      organization-access:
        description:
        - Settings for the team's organization access.
        type: dict
        required: false
        suboptions:
          manage-policies:
            description:
            - manage-policies. 
            type: bool
            required: false
            default: false
          manage-policy-overrides:
            description:
            - manage-policy-overrides. 
            type: bool
            required: false
            default: false
          manage-workspaces:
            description:
            - manage-workspaces. 
            type: bool
            required: false
            default: false
          manage-vcs-settings:
            description:
            - manage-vcs-settings. 
            type: bool
            required: false
            default: false                                             
  state:
    description:
    - Whether the team should exist or not.
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
- name: Create a Team
  esp.terraform.tfe_team:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    attributes:
      "name": developers
      "organization-access":
        "manage-workspaces": true
        "manage-vcs-settings": true
    state: present
    validate_certs: no

- name: Edit a Team
  esp.terraform.tfe_team:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers  
    attributes:
      "name": new-name
      "organization-access":
        "manage-workspaces": true
        "manage-vcs-settings": true
    state: present
    validate_certs: no

- name: Remove a Team
  esp.terraform.tfe_team:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers
    state: absent
    validate_certs: no
'''

RETURN = r'''
json:
    description: Details on the team.
    returned: success
    type: dict
    contains:
        data:
            description: Details on the team.
            returned: success
            type: dict                  
            sample:
                attributes:
                    name: developers
                    organization-access:
                        manage-policies: false
                        manage-vcs-settings: true
                        manage-workspaces: true
                    permissions:
                        can-destroy: true
                        can-update-api-token: true
                        can-update-membership: true
                        can-update-organization-access: true
                        can-update-visibility: true
                    users-count: 0
                    visibility: secret
                id: team-EMyKbSwR3FbgpDop
                links:
                    self: /api/v2/teams/team-EMyKbSwR3FbgpDop
                relationships:
                    authentication-token:
                        meta: {}
                    organization:
                        data:
                            id: esp-api-test
                            type: organizations
                    organization-memberships:
                        data: []
                    users:
                        data: []
                type: teams            
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        team=dict(type='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'absent', ('team',), True), ('state', 'present', ('attributes',), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    team = module.params['team']
    state = module.params['state']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        organization=organization,
        json={},
    )
    if team is not None:
        result['team'] = team
    if attributes is not None:
        result['attributes'] = attributes

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
    if team is not None:
    # Refer to a team by its name
        if any(t['attributes']['name'] == team for t in all_teams['data']):
            team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
        elif any(t['id'] == team for t in all_teams['data']):
            team_id = team
        else:
            if state == 'present':
                module.fail_json(msg='The supplied "%s" team does not exist in "%s" organization.' % (team, organization) )
    else:
        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new team.')
        # Find team_id when 'New' team already exists
        if any(t['attributes']['name'] == attributes['name'] for t in all_teams['data']):
            team_id = [t for t in all_teams['data'] if t['attributes']['name'] == attributes['name']][0]['id']

    # Destroy the team if it exists and state == 'absent'
    if (state == 'absent') and (team_id is not None):

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.teams.destroy, team_id=team_id)
            except Exception as e:
                module.fail_json(msg='Unable to destroy "%s" team in "%s" organization. Error: %s.' % (team, organization, to_native(e)) )          

        result['changed'] = True
 
    # Update the team if it exists and state == 'present'
    if (state == 'present') and (team_id is not None):

        if attributes is not None:
            t_payload = {
              "data": {
                "type": "teams",
                "attributes": attributes
              }
            }

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [t for t in all_teams['data'] if t['id'] == team_id][0]['attributes']            
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.teams.update, team_id=team_id, payload=t_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" team in "%s" organization. Error: %s.' % (team, organization, to_native(e)) )    

                result['changed'] = True

    # Create the team if it does not exist and state == 'present'
    if (state == 'present') and (team_id is None):

        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new team')

        t_payload = {
          "data": {
            "type": "teams",
            "attributes": attributes
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.teams.create, payload=t_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create "%s" team in "%s" organization. Error: %s.' % (team, organization, to_native(e)) )    

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()